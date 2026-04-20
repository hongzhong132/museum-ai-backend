import json
import logging
import os
import re
import time
from copy import deepcopy
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app import crud, models
from app.services.llm_service import chat_with_llm, is_llm_configured

logger = logging.getLogger(__name__)

ROUTE_USE_LLM = os.getenv("ROUTE_USE_LLM", "1").strip().lower() in {"1", "true", "yes", "on"}

ROUTE_LLM_TIMEOUT = float(os.getenv("ROUTE_LLM_TIMEOUT", "18"))
ROUTE_LLM_MAX_RETRIES = int(os.getenv("ROUTE_LLM_MAX_RETRIES", "0"))
ROUTE_LLM_MAX_TOKENS_BASIC = int(os.getenv("ROUTE_LLM_MAX_TOKENS_BASIC", "420"))
ROUTE_LLM_MAX_TOKENS_REPLAN = int(os.getenv("ROUTE_LLM_MAX_TOKENS_REPLAN", "480"))
ROUTE_CACHE_TTL_SECONDS = int(os.getenv("ROUTE_CACHE_TTL_SECONDS", "600"))

_route_cache: dict[str, tuple[float, dict]] = {}
_replan_cache: dict[str, tuple[float, dict]] = {}


def _make_route_cache_key(
    available_minutes: int,
    interest: str,
    first_visit: bool,
    visit_goal: str,
) -> str:
    return json.dumps(
        {
            "available_minutes": available_minutes,
            "interest": interest,
            "first_visit": first_visit,
            "visit_goal": visit_goal,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _make_replan_cache_key(
    current_hall_id: int,
    visited_hall_ids: list[int],
    remaining_minutes: int,
    updated_goal: str,
) -> str:
    return json.dumps(
        {
            "current_hall_id": current_hall_id,
            "visited_hall_ids": sorted(visited_hall_ids),
            "remaining_minutes": remaining_minutes,
            "updated_goal": updated_goal,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _get_cache(cache_obj: dict[str, tuple[float, dict]], key: str) -> dict | None:
    item = cache_obj.get(key)
    if not item:
        return None

    expires_at, value = item
    if time.time() > expires_at:
        cache_obj.pop(key, None)
        return None

    return deepcopy(value)


def _set_cache(cache_obj: dict[str, tuple[float, dict]], key: str, value: dict) -> None:
    cache_obj[key] = (time.time() + ROUTE_CACHE_TTL_SECONDS, deepcopy(value))


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _ensure_sentence(text: str) -> str:
    text = _safe_text(text)
    if not text:
        return ""
    if text[-1] not in "。！？":
        text += "。"
    return text


def _truncate(text: str, limit: int = 80) -> str:
    text = _safe_text(text)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip("，。；;,. ") + "…"


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    result: list[str] = []
    for item in items:
        text = _safe_text(item)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _coerce_string_list(value: Any, limit: int = 3) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return _dedupe_keep_order([_safe_text(item) for item in value if _safe_text(item)])[:limit]

    text = _safe_text(value)
    if not text:
        return []

    parts = re.split(r"[\n；;、|]+", text)
    if len(parts) <= 1:
        parts = re.split(r"[，,]+", text)

    return _dedupe_keep_order([part for part in parts if _safe_text(part)])[:limit]


def _float_value(value: Any) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _clean_user_text(text: str) -> str:
    if not text:
        return ""

    cleaned = str(text).strip()
    cleaned = re.sub(r"\b(normal|deep|child)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" \n\r\t\"'，,。；;")
    return cleaned


def _clean_json_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    cleaned = cleaned.replace("“", '"').replace("”", '"')
    cleaned = cleaned.replace("‘", "'").replace("’", "'")

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(0)

    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)

    return cleaned.strip()


def _extract_keywords(*texts: str) -> list[str]:
    keywords: list[str] = []
    seen = set()

    separators = [
        "，", "。", "、", "；", ";", "/", "|", "：", ":",
        "（", "）", "(", ")", "《", "》", "-", "_", "\n", "\t",
        "与", "和", "及", "以及",
    ]

    for text in texts:
        if not text:
            continue

        cleaned = text
        for sep in separators:
            cleaned = cleaned.replace(sep, " ")

        parts = [part.strip() for part in cleaned.split() if part.strip()]
        if not parts and text.strip():
            parts = [text.strip()]

        for part in parts:
            if len(part) < 2:
                continue
            if part not in seen:
                seen.add(part)
                keywords.append(part)

    return keywords


def _dedupe_featured_exhibits(exhibits: list) -> list:
    seen_ids = set()
    result = []

    for exhibit in exhibits:
        exhibit_id = getattr(exhibit, "id", None)
        if exhibit_id in seen_ids:
            continue
        seen_ids.add(exhibit_id)
        result.append(exhibit)

    return result


def _get_edge_map(db: Session) -> dict[tuple[int, int], models.HallEdge]:
    edges = db.query(models.HallEdge).all()
    return {(edge.from_hall_id, edge.to_hall_id): edge for edge in edges}


def _get_hall_relation_map(db: Session) -> dict[tuple[int, int], models.NarrativeRelation]:
    relations = (
        db.query(models.NarrativeRelation)
        .filter(
            models.NarrativeRelation.source_type == "hall",
            models.NarrativeRelation.target_type == "hall",
        )
        .all()
    )
    return {(rel.source_id, rel.target_id): rel for rel in relations}


def _get_hall_exhibit_map(
    db: Session,
    hall_ids: list[int],
    per_hall: int = 3,
) -> dict[int, list[models.Exhibit]]:
    if not hall_ids:
        return {}

    exhibits = db.query(models.Exhibit).filter(models.Exhibit.hall_id.in_(hall_ids)).all()
    exhibits.sort(
        key=lambda item: (
            getattr(item, "hall_id", 0),
            -(getattr(item, "is_featured", 0) or 0),
            -(getattr(item, "recommended_priority", 0) or 0),
            getattr(item, "id", 0),
        )
    )

    result: dict[int, list[models.Exhibit]] = {}
    for exhibit in exhibits:
        hall_id = getattr(exhibit, "hall_id", None)
        if hall_id is None:
            continue
        result.setdefault(hall_id, [])
        if len(result[hall_id]) >= per_hall:
            continue
        result[hall_id].append(exhibit)

    return result


def _fallback_featured_exhibits(
    hall_exhibit_map: dict[int, list[models.Exhibit]],
    selected_halls: list[models.MuseumHall],
    limit_per_hall: int = 2,
    total_limit: int = 10,
) -> list[models.Exhibit]:
    result: list[models.Exhibit] = []
    seen_ids = set()

    for hall in selected_halls:
        for exhibit in hall_exhibit_map.get(hall.id, [])[:limit_per_hall]:
            if exhibit.id in seen_ids:
                continue
            seen_ids.add(exhibit.id)
            result.append(exhibit)
            if len(result) >= total_limit:
                return result

    return result


def _has_chronology_preference(interest: str, goal: str) -> bool:
    text = f"{interest} {goal}"
    keywords = ["时间线", "编年", "历史脉络", "按顺序", "先后", "不想绕路", "有条理", "历史"]
    return any(word in text for word in keywords)


def _hall_interest_score(
    hall: models.MuseumHall,
    interest: str,
    goal: str,
    first_visit: bool,
) -> float:
    score = 0.0
    user_text = f"{interest} {goal}"
    hall_text = " ".join([
        hall.name or "",
        hall.theme or "",
        hall.summary or "",
        hall.code or "",
        hall.zone or "",
        hall.floor or "",
    ])

    if hall.name and hall.name in user_text:
        score += 6.0
    if hall.theme and hall.theme in user_text:
        score += 4.5
    if hall.zone and hall.zone in user_text:
        score += 2.0

    for kw in _extract_keywords(interest, goal):
        if kw in hall_text:
            score += 2.0

    sort_order = hall.sort_order or 99
    if _has_chronology_preference(interest, goal):
        score += max(0, 10 - sort_order * 1.5)
    elif first_visit:
        score += max(0, 5 - sort_order * 0.6)
    else:
        score += max(0, 2 - sort_order * 0.2)

    score += min((hall.recommended_duration_min or 0) / 20, 1.5)
    return score


def _transition_score(
    from_hall_id: int,
    to_hall_id: int,
    edge_map: dict[tuple[int, int], models.HallEdge],
    relation_map: dict[tuple[int, int], models.NarrativeRelation],
) -> float:
    score = 0.0

    edge = edge_map.get((from_hall_id, to_hall_id))
    if edge:
        if edge.is_recommended:
            score += 4.0
        if edge.is_direct:
            score += 2.0
        if edge.is_backtrack_heavy:
            score -= 3.0
        score -= min(edge.walk_minutes or 0, 10) * 0.15
    else:
        score -= 1.0

    relation = relation_map.get((from_hall_id, to_hall_id))
    if relation:
        relation_type = (relation.relation_type or "").strip().lower()
        if relation_type in {"route_next", "chronological", "timeline"}:
            score += 3.5
        else:
            score += 1.0
        score += _float_value(relation.strength_score) * 2

    return score


def _pick_best_hall(
    candidates: Iterable[models.MuseumHall],
    current_hall: models.MuseumHall | None,
    total_time: int,
    limit_minutes: int,
    interest: str,
    goal: str,
    first_visit: bool,
    edge_map: dict[tuple[int, int], models.HallEdge],
    relation_map: dict[tuple[int, int], models.NarrativeRelation],
    allow_over_time_when_empty: bool = False,
) -> models.MuseumHall | None:
    best_hall = None
    best_score = float("-inf")

    for hall in candidates:
        hall_time = hall.recommended_duration_min or 0

        if not allow_over_time_when_empty and total_time + hall_time > limit_minutes:
            continue

        score = _hall_interest_score(hall, interest, goal, first_visit)

        if current_hall:
            score += _transition_score(
                current_hall.id,
                hall.id,
                edge_map=edge_map,
                relation_map=relation_map,
            )

        score -= hall_time * 0.03

        if score > best_score:
            best_score = score
            best_hall = hall

    return best_hall


def _sort_remaining_halls_for_replan(
    remaining_halls: list[models.MuseumHall],
    current_hall: models.MuseumHall | None,
    updated_goal: str,
    edge_map: dict[tuple[int, int], models.HallEdge],
    relation_map: dict[tuple[int, int], models.NarrativeRelation],
) -> list[models.MuseumHall]:
    def score(hall: models.MuseumHall) -> float:
        value = _hall_interest_score(
            hall=hall,
            interest=updated_goal,
            goal=updated_goal,
            first_visit=False,
        )
        if current_hall:
            value += _transition_score(
                current_hall.id,
                hall.id,
                edge_map=edge_map,
                relation_map=relation_map,
            )
        value -= (hall.sort_order or 999) * 0.05
        return value

    return sorted(remaining_halls, key=score, reverse=True)


def _build_route_exhibit_item(exhibit: models.Exhibit) -> dict:
    return {
        "id": exhibit.id,
        "name": exhibit.name,
        "hall_id": exhibit.hall_id,
        "era": exhibit.era,
        "category": exhibit.category,
        "material": exhibit.material,
        "craft": exhibit.craft,
        "usage_desc": getattr(exhibit, "usage_desc", None),
        "short_intro": exhibit.short_intro,
        "image_url": exhibit.image_url,
    }


def _build_transition_reason(
    from_hall: models.MuseumHall,
    to_hall: models.MuseumHall,
    edge_map: dict[tuple[int, int], models.HallEdge],
    relation_map: dict[tuple[int, int], models.NarrativeRelation],
) -> str:
    edge = edge_map.get((from_hall.id, to_hall.id))
    relation = relation_map.get((from_hall.id, to_hall.id))

    reasons: list[str] = []
    relation_summary = _safe_text(getattr(relation, "relation_summary", "")) if relation else ""
    relation_type = _safe_text(getattr(relation, "relation_type", "")).lower() if relation else ""

    if relation_summary:
        reasons.append(relation_summary)
    else:
        if relation_type in {"chronological", "timeline", "route_next"}:
            reasons.append("这一段更适合按时间线继续往后推")
        elif relation_type in {"thematic", "theme"}:
            reasons.append("这一段的主题承接更自然")
        elif relation_type in {"contrast", "compare"}:
            reasons.append("这样安排更方便做前后对照")

    if edge and _safe_text(edge.remark):
        reasons.append(_safe_text(edge.remark))
    elif edge:
        if edge.is_recommended:
            reasons.append("两区之间动线较顺")
        elif edge.is_direct:
            reasons.append("不用绕太多路")
        elif edge.walk_minutes:
            reasons.append(f"两站之间步行大约{edge.walk_minutes}分钟")

    if not reasons:
        reasons.append("这样衔接能让参观主线更连贯")

    return "；".join(_dedupe_keep_order(reasons)[:2])


def _build_hall_focus_text(hall: models.MuseumHall, exhibits: list[models.Exhibit]) -> str:
    exhibit_names = [exhibit.name for exhibit in exhibits[:3]]
    theme = _safe_text(hall.theme)
    summary = _safe_text(hall.summary)

    if theme and exhibit_names:
        return f"这一站先用{'、'.join(exhibit_names[:2])}把“{theme}”这条线立起来，再往展区内部细看。"
    if theme:
        return f"这一站先把“{theme}”这条主线抓住，别急着只盯着单件文物。"
    if exhibit_names:
        return f"这一站可以先用{'、'.join(exhibit_names[:2])}建立整体印象。"
    if summary:
        return _ensure_sentence(_truncate(summary, 56))
    return f"这一站适合先建立对“{hall.name}”的整体感觉。"


def _build_why_here_text(
    hall: models.MuseumHall,
    idx: int,
    selected_halls: list[models.MuseumHall],
    edge_map: dict[tuple[int, int], models.HallEdge],
    relation_map: dict[tuple[int, int], models.NarrativeRelation],
    interest: str,
    goal: str,
) -> str:
    is_chrono = _has_chronology_preference(interest, goal)

    if idx == 0:
        if is_chrono and _safe_text(hall.theme):
            return f"先从“{hall.name}”开始，更容易先把“{hall.theme}”这条主线立住，后面再往其他展区展开。"
        return f"先从“{hall.name}”开始，是为了先把整条路线的观察重点立起来。"

    if idx == len(selected_halls) - 1:
        if _safe_text(hall.theme):
            return f"把“{hall.name}”放在后段，是为了让这条路线最后落到“{hall.theme}”这个主题上完成收束。"
        return f"把“{hall.name}”放在后段，是为了让这条路线不是零散结束。"

    prev_hall = selected_halls[idx - 1]
    next_hall = selected_halls[idx + 1]
    prev_reason = _build_transition_reason(prev_hall, hall, edge_map, relation_map)
    next_reason = _build_transition_reason(hall, next_hall, edge_map, relation_map)
    return f"这一站放在中段更合适，因为它既能承接前一站，也方便自然过渡到下一站。{prev_reason}；{next_reason}。"


def _build_stop_guides_template(
    selected_halls: list[models.MuseumHall],
    hall_exhibit_map: dict[int, list[models.Exhibit]],
    edge_map: dict[tuple[int, int], models.HallEdge],
    relation_map: dict[tuple[int, int], models.NarrativeRelation],
    interest: str,
    goal: str,
) -> list[dict]:
    guides: list[dict] = []

    for idx, hall in enumerate(selected_halls):
        exhibits = hall_exhibit_map.get(hall.id, [])
        next_hall = selected_halls[idx + 1] if idx + 1 < len(selected_halls) else None
        key_exhibits = _dedupe_keep_order([exhibit.name for exhibit in exhibits[:3]])

        why_here = _build_why_here_text(
            hall=hall,
            idx=idx,
            selected_halls=selected_halls,
            edge_map=edge_map,
            relation_map=relation_map,
            interest=interest,
            goal=goal,
        )

        transition_to_next = (
            _build_transition_reason(hall, next_hall, edge_map, relation_map)
            if next_hall
            else "看到这里，这条路线已经比较完整地收住了。"
        )

        guides.append(
            {
                "hall_id": hall.id,
                "hall_name": hall.name,
                "hall_theme": hall.theme or "",
                "focus": _ensure_sentence(_build_hall_focus_text(hall, exhibits)),
                "why_here": _ensure_sentence(why_here),
                "key_exhibits": key_exhibits,
                "transition_to_next": _ensure_sentence(transition_to_next),
                "time_budget_min": hall.recommended_duration_min or 0,
            }
        )

    return guides


def _build_route_theme(selected_halls: list[models.MuseumHall], interest: str, goal: str) -> str:
    if goal:
        return f"围绕“{_truncate(goal, 18)}”展开的馆区主线"
    if interest:
        return f"围绕“{_truncate(interest, 18)}”展开的馆区主线"

    themes = [hall.theme for hall in selected_halls if _safe_text(hall.theme)]
    if len(themes) >= 2:
        return f"从“{themes[0]}”切入，再往“{themes[-1]}”展开"
    if len(themes) == 1:
        return f"围绕“{themes[0]}”展开"
    if selected_halls:
        return f"从“{selected_halls[0].name}”开始的馆区主线"
    return "馆内导览主线"


def _build_target_fit_reason(
    available_minutes: int,
    interest: str,
    first_visit: bool,
    visit_goal: str,
    selected_halls: list[models.MuseumHall],
) -> str:
    if not selected_halls:
        return "当前没有足够数据生成合适路线。"

    audience_text = "第一次来馆的参观" if first_visit else "目标更明确的参观"
    hall_count = len(selected_halls)
    goal_text = visit_goal or interest or "重点了解馆内代表内容"

    return (
        f"这条路线更适合{audience_text}的{available_minutes}分钟安排，"
        f"尽量用{hall_count}个展区把“{goal_text}”这条线讲清楚。"
    )


def _build_order_logic(
    selected_halls: list[models.MuseumHall],
    edge_map: dict[tuple[int, int], models.HallEdge],
    relation_map: dict[tuple[int, int], models.NarrativeRelation],
) -> str:
    if not selected_halls:
        return "当前没有可解释的顺序逻辑。"

    if len(selected_halls) == 1:
        return f"这次只保留“{selected_halls[0].name}”这一站，避免路线过散。"

    first_hall = selected_halls[0]
    second_hall = selected_halls[1]
    last_hall = selected_halls[-1]
    first_transition = _build_transition_reason(first_hall, second_hall, edge_map, relation_map)

    return (
        f"顺序上先从“{first_hall.name}”切入，再往“{second_hall.name}”推进，"
        f"最后用“{last_hall.name}”收束。{_ensure_sentence(first_transition)}"
    )


def _build_skip_strategy(
    selected_halls: list[models.MuseumHall],
    hall_exhibit_map: dict[int, list[models.Exhibit]],
) -> str:
    if not selected_halls:
        return "当前没有可缩减的路线。"

    if len(selected_halls) == 1:
        hall = selected_halls[0]
        exhibits = hall_exhibit_map.get(hall.id, [])
        if exhibits:
            return f"时间再紧一点时，你可以只抓住“{hall.name}”里的{'、'.join([e.name for e in exhibits[:2]])}。"
        return f"时间再紧一点时，你可以只保留“{hall.name}”这一站。"

    must_keep = selected_halls[:2]
    must_keep_names = "、".join([hall.name for hall in must_keep])
    optional_hall = selected_halls[-1]
    optional_exhibits = hall_exhibit_map.get(optional_hall.id, [])
    optional_text = optional_hall.name
    if optional_exhibits:
        optional_text += f"（尤其是{'、'.join([e.name for e in optional_exhibits[:1]])}）"

    return f"如果时间临时缩水，建议优先保留{must_keep_names}这两站，最后一站的{optional_text}可以酌情缩减。"


def _build_route_closing(selected_halls: list[models.MuseumHall]) -> str:
    if not selected_halls:
        return "当前没有形成完整路线。"

    last_hall = selected_halls[-1]
    if _safe_text(last_hall.theme):
        return f"最后落在“{last_hall.name}”，是为了让这条路线在“{last_hall.theme}”这个主题上完成收束。"
    return f"最后落在“{last_hall.name}”，是为了让这条路线带着一个完整印象收束。"


def _build_route_summary_from_structure(structure: dict) -> str:
    stop_guides = structure.get("stop_guides", []) or []
    hall_names = [item.get("hall_name") for item in stop_guides if _safe_text(item.get("hall_name"))]
    if not hall_names:
        return ""

    first_hall = hall_names[0]
    last_hall = hall_names[-1]
    middle_names = hall_names[1:-1]

    if len(middle_names) >= 2:
        middle_text = f"，中间会经过“{middle_names[0]}”“{middle_names[1]}”等展区"
    elif len(middle_names) == 1:
        middle_text = f"，中间会经过“{middle_names[0]}”"
    else:
        middle_text = ""

    return _ensure_sentence(
        f"这条路线会先从“{first_hall}”切入{middle_text}，最后在“{last_hall}”收住。"
        f"{_safe_text(structure.get('target_fit_reason'))}"
    )


def _build_route_structure_template(
    available_minutes: int,
    interest: str,
    first_visit: bool,
    visit_goal: str,
    selected_halls: list[models.MuseumHall],
    hall_exhibit_map: dict[int, list[models.Exhibit]],
    edge_map: dict[tuple[int, int], models.HallEdge],
    relation_map: dict[tuple[int, int], models.NarrativeRelation],
) -> dict:
    stop_guides = _build_stop_guides_template(
        selected_halls=selected_halls,
        hall_exhibit_map=hall_exhibit_map,
        edge_map=edge_map,
        relation_map=relation_map,
        interest=interest,
        goal=visit_goal,
    )

    structure = {
        "route_theme": _build_route_theme(selected_halls, interest, visit_goal),
        "target_fit_reason": _build_target_fit_reason(
            available_minutes=available_minutes,
            interest=interest,
            first_visit=first_visit,
            visit_goal=visit_goal,
            selected_halls=selected_halls,
        ),
        "order_logic": _build_order_logic(
            selected_halls=selected_halls,
            edge_map=edge_map,
            relation_map=relation_map,
        ),
        "route_summary": "",
        "stop_guides": stop_guides,
        "skip_strategy": _build_skip_strategy(selected_halls, hall_exhibit_map),
        "route_closing": _build_route_closing(selected_halls),
    }
    structure["route_summary"] = _build_route_summary_from_structure(structure)
    return structure


def _build_replan_reason_template(
    current_hall_name: str,
    remaining_minutes: int,
    updated_goal: str,
    selected_halls: list[models.MuseumHall],
) -> str:
    if not selected_halls:
        return "当前没有新的候选路线。"

    hall_names = "、".join([hall.name for hall in selected_halls[:3]])
    goal_text = updated_goal or "当前新目标"

    return (
        f"这次重规划优先保留了还没访问、又和“{goal_text}”更贴近的展区，"
        f"并尽量从“{current_hall_name}”顺着推进到{hall_names}。"
    )


def _build_replan_structure_template(
    current_hall_name: str,
    visited_hall_ids: list[int],
    remaining_minutes: int,
    updated_goal: str,
    selected_halls: list[models.MuseumHall],
    hall_exhibit_map: dict[int, list[models.Exhibit]],
    edge_map: dict[tuple[int, int], models.HallEdge],
    relation_map: dict[tuple[int, int], models.NarrativeRelation],
) -> dict:
    base_structure = _build_route_structure_template(
        available_minutes=remaining_minutes,
        interest=updated_goal,
        first_visit=False,
        visit_goal=updated_goal,
        selected_halls=selected_halls,
        hall_exhibit_map=hall_exhibit_map,
        edge_map=edge_map,
        relation_map=relation_map,
    )

    base_structure["route_summary"] = (
        f"接下来建议你从当前所在的“{current_hall_name}”继续往“{selected_halls[0].name if selected_halls else '下一站'}”推进，"
        f"尽量把剩余{remaining_minutes}分钟放在与当前目标更贴近的内容上。"
    )
    base_structure["replan_reason"] = _build_replan_reason_template(
        current_hall_name=current_hall_name,
        remaining_minutes=remaining_minutes,
        updated_goal=updated_goal,
        selected_halls=selected_halls,
    )
    base_structure["visited_hall_ids"] = visited_hall_ids
    return base_structure


def _merge_stop_guides(template_guides: list[dict], llm_guides: Any) -> list[dict]:
    llm_guides = llm_guides if isinstance(llm_guides, list) else []
    result: list[dict] = []

    for idx, template_item in enumerate(template_guides):
        item = llm_guides[idx] if idx < len(llm_guides) and isinstance(llm_guides[idx], dict) else {}
        merged = {
            "hall_id": template_item.get("hall_id"),
            "hall_name": template_item.get("hall_name"),
            "hall_theme": template_item.get("hall_theme"),
            "focus": _ensure_sentence(_safe_text(item.get("focus")) or template_item.get("focus", "")),
            "why_here": _ensure_sentence(_safe_text(item.get("why_here")) or template_item.get("why_here", "")),
            "key_exhibits": _coerce_string_list(item.get("key_exhibits"), limit=3) or template_item.get("key_exhibits", []),
            "transition_to_next": _ensure_sentence(
                _safe_text(item.get("transition_to_next")) or template_item.get("transition_to_next", "")
            ),
            "time_budget_min": item.get("time_budget_min") or template_item.get("time_budget_min"),
        }
        result.append(merged)

    return result


def _build_light_route_rewrite_prompt(
    available_minutes: int,
    interest: str,
    first_visit: bool,
    visit_goal: str,
    template_structure: dict,
) -> tuple[str, str]:
    compact_template = {
        "route_theme": template_structure["route_theme"],
        "target_fit_reason": template_structure["target_fit_reason"],
        "order_logic": template_structure["order_logic"],
        "route_summary": template_structure["route_summary"],
        "skip_strategy": template_structure["skip_strategy"],
        "route_closing": template_structure["route_closing"],
        "stop_guides": [
            {
                "hall_id": item["hall_id"],
                "hall_name": item["hall_name"],
                "hall_theme": item.get("hall_theme", ""),
                "focus": item["focus"],
                "why_here": item["why_here"],
                "key_exhibits": item["key_exhibits"],
                "transition_to_next": item["transition_to_next"],
                "time_budget_min": item["time_budget_min"],
            }
            for item in template_structure["stop_guides"]
        ],
    }

    system_prompt = (
        "你是湖北博物院里的个人导览助手。"
        "你只负责把已经选好的路线结果改写得更自然、更像真人陪逛。"
        "你不能改馆区顺序，不能改 hall_id，不能删除 key_exhibits，不能编造新事实。"
        "你的任务是让它摆脱生硬模板感，但仍保持原有内容和结构。"
    )

    user_prompt = f"""
请把这份已经生成好的路线结果改写成更自然、更像真人导览的话，但不要改变路线结构本身。

硬性要求：
1. 只输出 JSON，不要输出额外解释。
2. 必须保留原有字段：
{{
  "route_theme": "",
  "target_fit_reason": "",
  "order_logic": "",
  "route_summary": "",
  "stop_guides": [
    {{
      "hall_id": 1,
      "hall_name": "",
      "focus": "",
      "why_here": "",
      "key_exhibits": [],
      "transition_to_next": "",
      "time_budget_min": 0
    }}
  ],
  "skip_strategy": "",
  "route_closing": ""
}}
3. hall_id、hall_name、key_exhibits、time_budget_min 不要改。
4. 只润色文字，不重排路线，不补新事实。
5. 语气要像面对一个人，不要像系统摘要，也不要像一成不变的模板。
6. route_summary 控制在 130 到 200 字。
7. order_logic、skip_strategy、route_closing 各尽量 1 到 2 句。
8. 每个 stop_guide 的 focus / why_here / transition_to_next 要写得更自然，但不要空话。
9. 不要出现“系统根据”“智能推荐”“各位观众”“让我们来看”等表达。

用户输入：
- 可用时间：{available_minutes}分钟
- 兴趣方向：{interest or '未特别指定'}
- 是否首次参观：{"是" if first_visit else "否"}
- 参观目标：{visit_goal or '未特别指定'}

当前路线结果：
{json.dumps(compact_template, ensure_ascii=False)}
""".strip()

    return system_prompt, user_prompt


def _parse_route_structure_result(text: str, template_structure: dict, is_replan: bool = False) -> dict:
    cleaned = _clean_json_text(text)
    data = json.loads(cleaned)

    structure = {
        "route_theme": _safe_text(data.get("route_theme")) or template_structure["route_theme"],
        "target_fit_reason": _ensure_sentence(_safe_text(data.get("target_fit_reason")) or template_structure["target_fit_reason"]),
        "order_logic": _ensure_sentence(_safe_text(data.get("order_logic")) or template_structure["order_logic"]),
        "route_summary": _ensure_sentence(_safe_text(data.get("route_summary")) or template_structure["route_summary"]),
        "stop_guides": _merge_stop_guides(template_structure["stop_guides"], data.get("stop_guides")),
        "skip_strategy": _ensure_sentence(_safe_text(data.get("skip_strategy")) or template_structure["skip_strategy"]),
        "route_closing": _ensure_sentence(_safe_text(data.get("route_closing")) or template_structure["route_closing"]),
    }

    if is_replan:
        structure["replan_reason"] = _ensure_sentence(
            _safe_text(data.get("replan_reason")) or template_structure.get("replan_reason", "")
        )

    return structure


def generate_basic_route(
    db: Session,
    available_minutes: int,
    interest: str,
    first_visit: bool,
    visit_goal: str,
):
    interest = _clean_user_text(interest)
    visit_goal = _clean_user_text(visit_goal)

    cache_key = _make_route_cache_key(
        available_minutes=available_minutes,
        interest=interest,
        first_visit=first_visit,
        visit_goal=visit_goal,
    )
    cached = _get_cache(_route_cache, cache_key)
    if cached is not None:
        return cached

    halls = crud.get_all_halls(db)
    if not halls:
        result = {
            "route_title": f"{available_minutes}分钟智能导览路线",
            "route_theme": "",
            "target_fit_reason": "",
            "order_logic": "",
            "route_summary": "当前没有可用展区数据。",
            "selected_halls": [],
            "featured_exhibits": [],
            "stop_guides": [],
            "skip_strategy": "",
            "route_closing": "",
            "source": "none",
        }
        _set_cache(_route_cache, cache_key, result)
        return result

    edge_map = _get_edge_map(db)
    relation_map = _get_hall_relation_map(db)

    remaining_halls = halls[:]
    selected_halls: list[models.MuseumHall] = []
    total_time = 0
    current_hall: models.MuseumHall | None = None

    while remaining_halls:
        best_hall = _pick_best_hall(
            candidates=remaining_halls,
            current_hall=current_hall,
            total_time=total_time,
            limit_minutes=available_minutes,
            interest=interest,
            goal=visit_goal,
            first_visit=first_visit,
            edge_map=edge_map,
            relation_map=relation_map,
            allow_over_time_when_empty=False,
        )

        if best_hall is None:
            break

        selected_halls.append(best_hall)
        total_time += best_hall.recommended_duration_min or 0
        current_hall = best_hall
        remaining_halls = [hall for hall in remaining_halls if hall.id != best_hall.id]

    if not selected_halls:
        fallback_hall = _pick_best_hall(
            candidates=halls,
            current_hall=None,
            total_time=0,
            limit_minutes=available_minutes,
            interest=interest,
            goal=visit_goal,
            first_visit=first_visit,
            edge_map=edge_map,
            relation_map=relation_map,
            allow_over_time_when_empty=True,
        )
        if fallback_hall:
            selected_halls.append(fallback_hall)

    hall_ids = [hall.id for hall in selected_halls]
    hall_exhibit_map = _get_hall_exhibit_map(db, hall_ids, per_hall=3)

    featured_exhibits = crud.get_featured_exhibits_by_hall_ids(
        db,
        hall_ids,
        interest=interest,
        visit_goal=visit_goal,
        limit=10,
    )
    featured_exhibits = _dedupe_featured_exhibits(featured_exhibits)
    if not featured_exhibits:
        featured_exhibits = _fallback_featured_exhibits(hall_exhibit_map, selected_halls)

    route_title = f"{available_minutes}分钟智能导览路线"
    template_structure = _build_route_structure_template(
        available_minutes=available_minutes,
        interest=interest,
        first_visit=first_visit,
        visit_goal=visit_goal,
        selected_halls=selected_halls,
        hall_exhibit_map=hall_exhibit_map,
        edge_map=edge_map,
        relation_map=relation_map,
    )

    source = "template"
    if ROUTE_USE_LLM and is_llm_configured() and selected_halls:
        try:
            system_prompt, user_prompt = _build_light_route_rewrite_prompt(
                available_minutes=available_minutes,
                interest=interest,
                first_visit=first_visit,
                visit_goal=visit_goal,
                template_structure=template_structure,
            )

            start_time = time.perf_counter()
            llm_text = chat_with_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.36,
                max_tokens=ROUTE_LLM_MAX_TOKENS_BASIC,
                timeout=(4, ROUTE_LLM_TIMEOUT),
                max_retries=ROUTE_LLM_MAX_RETRIES,
            )
            template_structure = _parse_route_structure_result(
                llm_text,
                template_structure=template_structure,
                is_replan=False,
            )
            elapsed = time.perf_counter() - start_time
            source = "llm"

            logger.info(
                "AI basic route rewrite success | minutes=%s | halls=%s | elapsed=%.2fs",
                available_minutes,
                [hall.name for hall in selected_halls],
                elapsed,
            )
        except Exception as exc:
            logger.exception(
                "AI basic route rewrite failed, fallback to template | error=%s",
                exc,
            )

    result = {
        "route_title": route_title,
        "route_theme": template_structure["route_theme"],
        "target_fit_reason": template_structure["target_fit_reason"],
        "order_logic": template_structure["order_logic"],
        "route_summary": template_structure["route_summary"],
        "selected_halls": [
            {
                "id": hall.id,
                "name": hall.name,
                "recommended_duration_min": hall.recommended_duration_min,
            }
            for hall in selected_halls
        ],
        "featured_exhibits": [_build_route_exhibit_item(exhibit) for exhibit in featured_exhibits],
        "stop_guides": template_structure["stop_guides"],
        "skip_strategy": template_structure["skip_strategy"],
        "route_closing": template_structure["route_closing"],
        "source": source,
    }
    _set_cache(_route_cache, cache_key, result)
    return result


def generate_replanned_route(
    db: Session,
    current_hall_id: int,
    visited_hall_ids: list[int],
    remaining_minutes: int,
    updated_goal: str,
):
    updated_goal = _clean_user_text(updated_goal)

    cache_key = _make_replan_cache_key(
        current_hall_id=current_hall_id,
        visited_hall_ids=visited_hall_ids,
        remaining_minutes=remaining_minutes,
        updated_goal=updated_goal,
    )
    cached = _get_cache(_replan_cache, cache_key)
    if cached is not None:
        return cached

    halls = crud.get_all_halls(db)
    if not halls:
        result = {
            "route_title": "重规划结果",
            "route_theme": "",
            "target_fit_reason": "",
            "order_logic": "",
            "route_summary": "当前没有可用展区数据。",
            "selected_halls": [],
            "featured_exhibits": [],
            "stop_guides": [],
            "skip_strategy": "",
            "route_closing": "",
            "replan_reason": "数据库中暂无展区信息。",
            "source": "none",
        }
        _set_cache(_replan_cache, cache_key, result)
        return result

    edge_map = _get_edge_map(db)
    relation_map = _get_hall_relation_map(db)

    hall_map = {hall.id: hall for hall in halls}
    current_hall = hall_map.get(current_hall_id)
    current_hall_name = current_hall.name if current_hall else "当前展区"
    current_sort_order = current_hall.sort_order if current_hall else 0

    remaining_halls = [
        hall
        for hall in halls
        if hall.id not in visited_hall_ids
        and hall.id != current_hall_id
        and (hall.sort_order or 999) >= current_sort_order
    ]

    if not remaining_halls:
        remaining_halls = [
            hall for hall in halls
            if hall.id not in visited_hall_ids and hall.id != current_hall_id
        ]

    if not remaining_halls:
        result = {
            "route_title": f"{remaining_minutes}分钟重规划路线",
            "route_theme": "",
            "target_fit_reason": "",
            "order_logic": "",
            "route_summary": "你已经看完当前可用的重点展区。",
            "selected_halls": [],
            "featured_exhibits": [],
            "stop_guides": [],
            "skip_strategy": "",
            "route_closing": "",
            "replan_reason": "系统检测到你已访问全部候选展区，因此没有新的推荐路线。",
            "source": "none",
        }
        _set_cache(_replan_cache, cache_key, result)
        return result

    remaining_halls = _sort_remaining_halls_for_replan(
        remaining_halls=remaining_halls,
        current_hall=current_hall,
        updated_goal=updated_goal,
        edge_map=edge_map,
        relation_map=relation_map,
    )

    selected_halls: list[models.MuseumHall] = []
    total_time = 0
    cursor_hall = current_hall

    while remaining_halls:
        best_hall = _pick_best_hall(
            candidates=remaining_halls,
            current_hall=cursor_hall,
            total_time=total_time,
            limit_minutes=remaining_minutes,
            interest=updated_goal,
            goal=updated_goal,
            first_visit=False,
            edge_map=edge_map,
            relation_map=relation_map,
            allow_over_time_when_empty=False,
        )

        if best_hall is None:
            break

        selected_halls.append(best_hall)
        total_time += best_hall.recommended_duration_min or 0
        cursor_hall = best_hall
        remaining_halls = [hall for hall in remaining_halls if hall.id != best_hall.id]

    if not selected_halls:
        fallback_hall = _pick_best_hall(
            candidates=[hall for hall in halls if hall.id not in visited_hall_ids and hall.id != current_hall_id],
            current_hall=current_hall,
            total_time=0,
            limit_minutes=remaining_minutes,
            interest=updated_goal,
            goal=updated_goal,
            first_visit=False,
            edge_map=edge_map,
            relation_map=relation_map,
            allow_over_time_when_empty=True,
        )
        if fallback_hall:
            selected_halls.append(fallback_hall)

    hall_ids = [hall.id for hall in selected_halls]
    hall_exhibit_map = _get_hall_exhibit_map(db, hall_ids, per_hall=3)

    featured_exhibits = crud.get_featured_exhibits_by_hall_ids(
        db,
        hall_ids,
        interest=updated_goal,
        visit_goal=updated_goal,
        limit=10,
    )
    featured_exhibits = _dedupe_featured_exhibits(featured_exhibits)
    if not featured_exhibits:
        featured_exhibits = _fallback_featured_exhibits(hall_exhibit_map, selected_halls)

    route_title = f"{remaining_minutes}分钟重规划路线"
    template_structure = _build_replan_structure_template(
        current_hall_name=current_hall_name,
        visited_hall_ids=visited_hall_ids,
        remaining_minutes=remaining_minutes,
        updated_goal=updated_goal,
        selected_halls=selected_halls,
        hall_exhibit_map=hall_exhibit_map,
        edge_map=edge_map,
        relation_map=relation_map,
    )

    source = "template"
    if ROUTE_USE_LLM and is_llm_configured() and selected_halls:
        try:
            system_prompt, user_prompt = _build_light_route_rewrite_prompt(
                available_minutes=remaining_minutes,
                interest=updated_goal,
                first_visit=False,
                visit_goal=updated_goal,
                template_structure=template_structure,
            )

            start_time = time.perf_counter()
            llm_text = chat_with_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.36,
                max_tokens=ROUTE_LLM_MAX_TOKENS_REPLAN,
                timeout=(4, ROUTE_LLM_TIMEOUT),
                max_retries=ROUTE_LLM_MAX_RETRIES,
            )
            template_structure = _parse_route_structure_result(
                llm_text,
                template_structure=template_structure,
                is_replan=True,
            )
            template_structure["replan_reason"] = template_structure.get("replan_reason") or _build_replan_reason_template(
                current_hall_name=current_hall_name,
                remaining_minutes=remaining_minutes,
                updated_goal=updated_goal,
                selected_halls=selected_halls,
            )
            elapsed = time.perf_counter() - start_time
            source = "llm"

            logger.info(
                "AI replan rewrite success | current_hall=%s | remaining_minutes=%s | elapsed=%.2fs",
                current_hall_name,
                remaining_minutes,
                elapsed,
            )
        except Exception as exc:
            logger.exception(
                "AI replan rewrite failed, fallback to template | error=%s",
                exc,
            )

    result = {
        "route_title": route_title,
        "route_theme": template_structure["route_theme"],
        "target_fit_reason": template_structure["target_fit_reason"],
        "order_logic": template_structure["order_logic"],
        "route_summary": template_structure["route_summary"],
        "selected_halls": [
            {
                "id": hall.id,
                "name": hall.name,
                "recommended_duration_min": hall.recommended_duration_min,
            }
            for hall in selected_halls
        ],
        "featured_exhibits": [_build_route_exhibit_item(exhibit) for exhibit in featured_exhibits],
        "stop_guides": template_structure["stop_guides"],
        "skip_strategy": template_structure["skip_strategy"],
        "route_closing": template_structure["route_closing"],
        "replan_reason": template_structure.get("replan_reason", ""),
        "source": source,
    }
    _set_cache(_replan_cache, cache_key, result)
    return result
