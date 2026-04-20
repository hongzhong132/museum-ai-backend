import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from app import models

logger = logging.getLogger(__name__)

LIST_SEPARATORS = ["\n", "；", ";", "|", "、", ",", "，"]


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_attr(obj: Any, *names: str) -> str:
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            text = _safe_text(value)
            if text:
                return text
    return ""


def _normalize_line(text: str) -> str:
    text = _safe_text(text)
    if not text:
        return ""
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[，,；;。.!！?？]+$", "", text)
    return text


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    result: list[str] = []

    for item in items:
        text = _normalize_line(item)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)

    return result


def _split_text_list(text: str, limit: int = 6) -> list[str]:
    text = _safe_text(text)
    if not text:
        return []

    normalized = text
    for sep in LIST_SEPARATORS:
        normalized = normalized.replace(sep, "\n")

    parts = [part.strip() for part in normalized.splitlines() if part.strip()]
    if len(parts) <= 1:
        parts = re.split(r"[。！？!?]+", text)

    result: list[str] = []
    for part in parts:
        line = _normalize_line(part)
        if not line:
            continue
        result.append(line)
        if len(result) >= limit:
            break

    return _dedupe_keep_order(result)


def _truncate(text: str, limit: int = 60) -> str:
    text = _safe_text(text)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip("，。；;,. ") + "…"


def _float_value(value: Any) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _find_relation_record(
    db: Session,
    source_exhibit_id: int,
    target_exhibit_id: int,
) -> dict | None:
    relation = (
        db.query(models.NarrativeRelation)
        .filter(
            models.NarrativeRelation.source_type == "exhibit",
            models.NarrativeRelation.source_id == source_exhibit_id,
            models.NarrativeRelation.target_type == "exhibit",
            models.NarrativeRelation.target_id == target_exhibit_id,
        )
        .first()
    )

    if relation:
        return {
            "relation_type": _safe_text(getattr(relation, "relation_type", "")),
            "relation_summary": _safe_text(getattr(relation, "relation_summary", "")),
            "strength_score": _float_value(getattr(relation, "strength_score", 0)),
            "direction": "forward",
        }

    reverse_relation = (
        db.query(models.NarrativeRelation)
        .filter(
            models.NarrativeRelation.source_type == "exhibit",
            models.NarrativeRelation.source_id == target_exhibit_id,
            models.NarrativeRelation.target_type == "exhibit",
            models.NarrativeRelation.target_id == source_exhibit_id,
        )
        .first()
    )

    if reverse_relation:
        return {
            "relation_type": _safe_text(getattr(reverse_relation, "relation_type", "")),
            "relation_summary": _safe_text(getattr(reverse_relation, "relation_summary", "")),
            "strength_score": _float_value(getattr(reverse_relation, "strength_score", 0)),
            "direction": "reverse",
        }

    return None


def _dedupe_related_cards(items: list[dict]) -> list[dict]:
    seen = set()
    result = []

    for item in items:
        key = (item.get("name"), item.get("hall_id"))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)

    return result


def get_related_exhibit_cards(db: Session, exhibit_id: int, limit: int = 3) -> list[dict]:
    result: list[dict] = []

    relations = (
        db.query(models.NarrativeRelation)
        .filter(
            models.NarrativeRelation.source_type == "exhibit",
            models.NarrativeRelation.source_id == exhibit_id,
            models.NarrativeRelation.target_type == "exhibit",
        )
        .order_by(models.NarrativeRelation.strength_score.desc())
        .all()
    )

    related_ids = [r.target_id for r in relations if getattr(r, "target_id", None) is not None]
    if related_ids:
        exhibits = db.query(models.Exhibit).filter(models.Exhibit.id.in_(related_ids)).all()
        exhibit_map = {e.id: e for e in exhibits}
        relation_map = {r.target_id: r for r in relations}

        for rid in related_ids:
            exhibit = exhibit_map.get(rid)
            if not exhibit:
                continue

            relation = relation_map.get(rid)
            relation_summary = _safe_text(getattr(relation, "relation_summary", ""))
            relation_type = _safe_text(getattr(relation, "relation_type", ""))
            strength_score = _float_value(getattr(relation, "strength_score", 0))

            result.append(
                {
                    "id": exhibit.id,
                    "name": _safe_attr(exhibit, "name"),
                    "hall_id": getattr(exhibit, "hall_id", None),
                    "era": _safe_attr(exhibit, "era"),
                    "dynasty": _safe_attr(exhibit, "dynasty"),
                    "category": _safe_attr(exhibit, "category"),
                    "sub_category": _safe_attr(exhibit, "sub_category"),
                    "short_intro": _safe_attr(exhibit, "short_intro"),
                    "usage_desc": _safe_attr(exhibit, "usage_desc", "function", "usage"),
                    "symbolism": _safe_attr(exhibit, "symbolism"),
                    "style_tags": _safe_attr(exhibit, "style_tags"),
                    "image_url": _safe_attr(exhibit, "image_url"),
                    "relation_type": relation_type,
                    "relation_summary": relation_summary,
                    "strength_score": strength_score,
                }
            )

    if len(result) < limit:
        current_exhibit = db.query(models.Exhibit).filter(models.Exhibit.id == exhibit_id).first()
        if current_exhibit:
            same_hall_query = db.query(models.Exhibit).filter(
                models.Exhibit.hall_id == current_exhibit.hall_id,
                models.Exhibit.id != exhibit_id,
            )
            if hasattr(models.Exhibit, "recommended_priority"):
                same_hall_query = same_hall_query.order_by(models.Exhibit.recommended_priority.desc())
            else:
                same_hall_query = same_hall_query.order_by(models.Exhibit.id.asc())

            same_hall_exhibits = same_hall_query.all()
            existing_ids = {item["id"] for item in result}

            for exhibit in same_hall_exhibits:
                if exhibit.id in existing_ids:
                    continue

                result.append(
                    {
                        "id": exhibit.id,
                        "name": _safe_attr(exhibit, "name"),
                        "hall_id": getattr(exhibit, "hall_id", None),
                        "era": _safe_attr(exhibit, "era"),
                        "dynasty": _safe_attr(exhibit, "dynasty"),
                        "category": _safe_attr(exhibit, "category"),
                        "sub_category": _safe_attr(exhibit, "sub_category"),
                        "short_intro": _safe_attr(exhibit, "short_intro"),
                        "usage_desc": _safe_attr(exhibit, "usage_desc", "function", "usage"),
                        "symbolism": _safe_attr(exhibit, "symbolism"),
                        "style_tags": _safe_attr(exhibit, "style_tags"),
                        "image_url": _safe_attr(exhibit, "image_url"),
                        "relation_type": "",
                        "relation_summary": "",
                        "strength_score": 0.0,
                    }
                )
                if len(result) >= limit:
                    break

    result = _dedupe_related_cards(result)
    return result[:limit]


def _build_profile_lines(
    name: str,
    era: str,
    dynasty: str,
    category: str,
    sub_category: str,
    material: str,
    craft: str,
    usage_desc: str,
    hall_name: str,
    hall_theme: str,
    hall_summary: str,
) -> list[str]:
    lines: list[str] = []

    time_label = dynasty or era
    if time_label and category and sub_category:
        lines.append(f"{name}一般可放在{time_label}时期的{category}里的{sub_category}去理解")
    elif time_label and category:
        lines.append(f"{name}一般被归入{time_label}时期的{category}类展品")
    elif time_label:
        lines.append(f"{name}和{time_label}时期的历史背景相关")
    elif category:
        lines.append(f"{name}属于{category}类展品")

    if material:
        lines.append(f"它的主要材质是{material}")
    if craft:
        lines.append(f"工艺上可以重点留意{craft}")
    if usage_desc:
        lines.append(f"它和{usage_desc}有关")
    if hall_summary:
        lines.append(f"它放在“{hall_name}”展区，是为了帮助理解{hall_theme}这一主题")

    return lines


def _build_route_connection_points(
    hall_name: str,
    hall_theme: str,
    hall_summary: str,
    relation_hint: str,
) -> list[str]:
    points: list[str] = []

    if relation_hint:
        points.append(f"它和当前上下文的承接点在于：{relation_hint}")
    if hall_theme:
        points.append(f"现在看它，是在用一件具体器物把“{hall_theme}”这个展区主题落下来")
    if hall_summary:
        points.append(_truncate(hall_summary, 56))
    if hall_name:
        points.append(f"它属于“{hall_name}”这一站比较适合停下来细看的代表对象")

    return _dedupe_keep_order(points)


def build_exhibit_context(
    db: Session,
    exhibit_id: int,
    current_context_exhibit_id: int | None = None,
    related_limit: int = 3,
) -> dict | None:
    exhibit = db.query(models.Exhibit).filter(models.Exhibit.id == exhibit_id).first()
    if not exhibit:
        return None

    hall = None
    if getattr(exhibit, "hall_id", None) is not None:
        hall = db.query(models.MuseumHall).filter(models.MuseumHall.id == exhibit.hall_id).first()

    relation_record = None
    if current_context_exhibit_id is not None:
        relation_record = _find_relation_record(db, current_context_exhibit_id, exhibit_id)

    relation_hint = _safe_text(relation_record.get("relation_summary")) if relation_record else ""

    name = _safe_attr(exhibit, "name") or "该展品"
    era = _safe_attr(exhibit, "era")
    dynasty = _safe_attr(exhibit, "dynasty")
    category = _safe_attr(exhibit, "category")
    sub_category = _safe_attr(exhibit, "sub_category")
    material = _safe_attr(exhibit, "material")
    craft = _safe_attr(exhibit, "craft")
    usage_desc = _safe_attr(exhibit, "usage_desc", "function", "usage")
    short_intro = _safe_attr(exhibit, "short_intro")
    deep_intro = _safe_attr(exhibit, "deep_intro") or short_intro
    core_value = _safe_attr(exhibit, "core_value")
    keywords = _safe_attr(exhibit, "keywords")

    historical_value = _safe_attr(exhibit, "historical_value")
    art_value = _safe_attr(exhibit, "art_value")
    cultural_value = _safe_attr(exhibit, "cultural_value")
    shape_desc = _safe_attr(exhibit, "shape_desc")
    pattern_elements = _safe_attr(exhibit, "pattern_elements")
    symbolism = _safe_attr(exhibit, "symbolism")
    style_tags = _safe_attr(exhibit, "style_tags")
    color_palette = _safe_attr(exhibit, "color_palette")
    interesting_points = _safe_attr(exhibit, "interesting_points")
    related_people = _safe_attr(exhibit, "related_people")
    related_events = _safe_attr(exhibit, "related_events")
    related_exhibits_hint = _safe_attr(exhibit, "related_exhibits_hint")
    creative_keywords = _safe_attr(exhibit, "creative_keywords")
    poster_copy_seed = _safe_attr(exhibit, "poster_copy_seed")
    image_prompt_seed = _safe_attr(exhibit, "image_prompt_seed")

    hall_name = _safe_attr(hall, "name") or "未知展区"
    hall_theme = _safe_attr(hall, "theme") or "未知主题"
    hall_summary = _safe_attr(hall, "summary")
    hall_floor = _safe_attr(hall, "floor")
    hall_zone = _safe_attr(hall, "zone")

    watch_points = _split_text_list(_safe_attr(exhibit, "watch_points"), limit=5)
    story_points = _split_text_list(_safe_attr(exhibit, "story_points"), limit=5)
    detail_points = _split_text_list(_safe_attr(exhibit, "detail_points"), limit=5)
    kid_points = _split_text_list(_safe_attr(exhibit, "kid_points"), limit=4)
    deep_points = _split_text_list(_safe_attr(exhibit, "deep_points"), limit=6)

    short_sentences = _split_text_list(short_intro, limit=3)
    deep_sentences = _split_text_list(deep_intro, limit=4)

    historical_value_points = _split_text_list(historical_value, limit=4)
    art_value_points = _split_text_list(art_value, limit=4)
    cultural_value_points = _split_text_list(cultural_value, limit=4)
    pattern_points = _split_text_list(pattern_elements, limit=5)
    symbolism_points = _split_text_list(symbolism, limit=5)
    interesting_point_list = _split_text_list(interesting_points, limit=5)
    related_people_points = _split_text_list(related_people, limit=4)
    related_events_points = _split_text_list(related_events, limit=4)
    related_exhibits_hint_points = _split_text_list(related_exhibits_hint, limit=5)
    poster_copy_points = _split_text_list(poster_copy_seed, limit=3)

    profile_lines = _build_profile_lines(
        name=name,
        era=era,
        dynasty=dynasty,
        category=category,
        sub_category=sub_category,
        material=material,
        craft=craft,
        usage_desc=usage_desc,
        hall_name=hall_name,
        hall_theme=hall_theme,
        hall_summary=hall_summary,
    )

    related_exhibits = get_related_exhibit_cards(db=db, exhibit_id=exhibit_id, limit=related_limit)

    related_summary_lines: list[str] = []
    comparison_points: list[str] = []
    compare_hint_lines: list[str] = []

    for item in related_exhibits:
        relation_summary = _safe_text(item.get("relation_summary"))
        short = _safe_text(item.get("short_intro"))
        usage = _safe_text(item.get("usage_desc"))
        symbolism_text = _safe_text(item.get("symbolism"))
        if relation_summary:
            related_summary_lines.append(f"{item['name']}：{relation_summary}")
            comparison_points.append(f"可以和{item['name']}对照着看：{relation_summary}")
            compare_hint_lines.append(f"和{item['name']}连着看，更容易看出它们之间的承接关系")
        elif short:
            related_summary_lines.append(f"{item['name']}：{_truncate(short, 44)}")
            compare_hint_lines.append(f"也可以顺手看看{item['name']}，把同一展区里的内容连起来")
        elif symbolism_text:
            related_summary_lines.append(f"{item['name']}：可从{symbolism_text}这一层去联动理解")
        elif usage:
            related_summary_lines.append(f"{item['name']}：与{usage}相关")
        else:
            related_summary_lines.append(f"{item['name']}：可作为联动讲解对象")

    if related_exhibits_hint_points:
        for hint_name in related_exhibits_hint_points[:3]:
            compare_hint_lines.append(f"也可以把它和{hint_name}放在一起看，理解同一条线索的不同展开")

    first_impression_candidates = _dedupe_keep_order(
        watch_points
        + detail_points
        + ([f"你可以先看它的形制：{shape_desc}"] if shape_desc else [])
        + ([f"也可以先从{pattern_points[0]}这样的表面元素入手"] if pattern_points else [])
        + short_sentences
        + deep_sentences
    )[:6]

    historical_role_points = _dedupe_keep_order(
        ([f"它和{usage_desc}有关"] if usage_desc else [])
        + story_points
        + historical_value_points
        + ([f"相关人物可以想到{related_people}"] if related_people else [])
        + ([f"相关历史背景可以连到{related_events}"] if related_events else [])
        + ([core_value] if core_value else [])
    )[:6]

    craft_value_points = _dedupe_keep_order(
        ([f"工艺上可以重点留意{craft}"] if craft else [])
        + detail_points
        + watch_points
        + ([f"形制上可先抓{shape_desc}"] if shape_desc else [])
        + ([f"表面元素可注意{pattern_elements}"] if pattern_elements else [])
        + art_value_points
        + deep_points
    )[:6]

    route_connection_points = _build_route_connection_points(
        hall_name=hall_name,
        hall_theme=hall_theme,
        hall_summary=hall_summary,
        relation_hint=relation_hint,
    )

    visual_points = _dedupe_keep_order(
        ([f"形制上可以先抓住{shape_desc}"] if shape_desc else [])
        + ([f"表面元素可留意{pattern_elements}"] if pattern_elements else [])
        + ([f"整体气质偏向{style_tags}"] if style_tags else [])
        + ([f"视觉上可联想到{color_palette}"] if color_palette else [])
    )[:5]

    value_points = _dedupe_keep_order(
        historical_value_points + art_value_points + cultural_value_points + ([core_value] if core_value else [])
    )[:6]

    creative_context_points = _dedupe_keep_order(
        ([f"文创关键词：{creative_keywords}"] if creative_keywords else [])
        + ([f"可提炼的寓意：{symbolism}"] if symbolism else [])
        + ([f"可借用的风格标签：{style_tags}"] if style_tags else [])
        + ([f"适合的主色方向：{color_palette}"] if color_palette else [])
        + poster_copy_points
        + ([image_prompt_seed] if image_prompt_seed else [])
    )[:6]

    context = {
        "exhibit": {
            "id": exhibit.id,
            "name": name,
            "hall_id": getattr(exhibit, "hall_id", None),
            "hall_name": hall_name,
            "hall_theme": hall_theme,
            "era": era,
            "dynasty": dynasty,
            "category": category,
            "sub_category": sub_category,
            "material": material,
            "craft": craft,
            "usage_desc": usage_desc,
            "short_intro": short_intro,
            "deep_intro": deep_intro,
            "core_value": core_value,
            "historical_value": historical_value,
            "art_value": art_value,
            "cultural_value": cultural_value,
            "shape_desc": shape_desc,
            "pattern_elements": pattern_elements,
            "symbolism": symbolism,
            "style_tags": style_tags,
            "color_palette": color_palette,
            "interesting_points": interesting_points,
            "related_people": related_people,
            "related_events": related_events,
            "related_exhibits_hint": related_exhibits_hint,
            "creative_keywords": creative_keywords,
            "poster_copy_seed": poster_copy_seed,
            "image_prompt_seed": image_prompt_seed,
            "keywords": keywords,
            "image_url": _safe_attr(exhibit, "image_url"),
        },
        "hall": {
            "id": getattr(hall, "id", None) if hall else None,
            "name": hall_name,
            "theme": hall_theme,
            "summary": hall_summary,
            "floor": hall_floor,
            "zone": hall_zone,
            "recommended_duration_min": getattr(hall, "recommended_duration_min", None) if hall else None,
            "sort_order": getattr(hall, "sort_order", None) if hall else None,
        },
        "hall_summary": hall_summary,
        "relation_hint": relation_hint or None,
        "relation_type": _safe_text(relation_record.get("relation_type")) if relation_record else "",
        "core_facts": _dedupe_keep_order(profile_lines + short_sentences + deep_sentences + value_points)[:8],
        "watch_points": _dedupe_keep_order(watch_points + detail_points + deep_sentences + visual_points)[:6],
        "story_points": _dedupe_keep_order(story_points + deep_sentences + short_sentences + historical_value_points)[:6],
        "detail_points": _dedupe_keep_order(detail_points + watch_points + visual_points)[:6],
        "kid_points": _dedupe_keep_order(kid_points + watch_points + short_sentences + interesting_point_list)[:5],
        "deep_points": _dedupe_keep_order(
            deep_points + detail_points + story_points + value_points + visual_points
        )[:8],
        "historical_value_points": historical_value_points,
        "art_value_points": art_value_points,
        "cultural_value_points": cultural_value_points,
        "visual_points": visual_points,
        "symbolism_points": _dedupe_keep_order(symbolism_points)[:5],
        "interesting_points": interesting_point_list,
        "related_people_points": related_people_points,
        "related_events_points": related_events_points,
        "creative_points": creative_context_points,
        "first_impression_candidates": first_impression_candidates,
        "historical_role_points": historical_role_points,
        "craft_value_points": craft_value_points,
        "route_connection_points": route_connection_points,
        "comparison_points": _dedupe_keep_order(comparison_points)[:4],
        "compare_hint_lines": _dedupe_keep_order(compare_hint_lines)[:4],
        "related_exhibits": related_exhibits,
        "related_summary_lines": related_summary_lines[:5],
    }

    logger.debug(
        "Built exhibit context | exhibit_id=%s | exhibit_name=%s | facts=%s | watch=%s | deep=%s",
        exhibit.id,
        name,
        len(context["core_facts"]),
        len(context["watch_points"]),
        len(context["deep_points"]),
    )

    return context
