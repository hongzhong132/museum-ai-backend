import json
import logging
import re
import time
from typing import Any

from sqlalchemy.orm import Session

from app.services.context_builder import build_exhibit_context
from app.services.context_builder import get_related_exhibit_cards as _get_related_exhibit_cards
from app.services.llm_service import chat_with_llm, is_llm_configured

logger = logging.getLogger(__name__)

VALID_MODES = {"normal", "deep", "child"}


def get_related_exhibit_cards(
    db: Session,
    exhibit_id: int,
    limit: int = 3,
) -> list[dict]:
    return _get_related_exhibit_cards(db=db, exhibit_id=exhibit_id, limit=limit)


def _normalize_mode(mode: str | None) -> str:
    value = (mode or "normal").strip().lower()
    if value not in VALID_MODES:
        return "normal"
    return value


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _sanitize_single_user_tone(text: str) -> str:
    text = _safe_text(text)
    if not text:
        return ""

    replacements = [
        ("各位观众", "你"),
        ("各位游客", "你"),
        ("观众朋友们", "你"),
        ("大家", "你"),
        ("请大家注意", "你可以先注意"),
        ("请注意", "你可以先注意"),
        ("大家可以看到", "你可以看到"),
        ("我们可以看到", "你可以看到"),
        ("我们先来看", "你可以先看"),
        ("让我们来看", "你可以先看"),
        ("下面我们来看", "接下来你可以看"),
        ("接下来我们", "接下来你可以"),
        ("眼前这件", "这件"),
        ("来到这里", "走到这里"),
        ("游客", "参观者"),
    ]

    for old, new in replacements:
        text = text.replace(old, new)

    text = re.sub(r"我们现在看到的是", "现在你看到的是", text)
    text = re.sub(r"大家先看", "你可以先看", text)
    text = re.sub(r"请大家先看", "你可以先看", text)
    text = re.sub(r"各位先看", "你可以先看", text)

    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_sentence(text: str) -> str:
    text = _sanitize_single_user_tone(text)
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[。！？!?]+$", "", text)
    return text


def _ensure_sentence(text: str) -> str:
    text = _sanitize_single_user_tone(text)
    if not text:
        return ""
    if text[-1] not in "。！？":
        text += "。"
    return text


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    result: list[str] = []

    for item in items:
        text = _normalize_sentence(item)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)

    return result


def _join_sentences(parts: list[str], max_len: int | None = None) -> str:
    clean_parts = []
    seen = set()

    for part in parts:
        text = _normalize_sentence(part)
        if not text or text in seen:
            continue
        seen.add(text)
        clean_parts.append(text)

    if not max_len:
        result = "。".join(clean_parts)
        return result + "。" if result else ""

    result_parts = []
    current_len = 0

    for part in clean_parts:
        sentence = part + "。"
        if current_len + len(sentence) > max_len:
            break
        result_parts.append(part)
        current_len += len(sentence)

    result = "。".join(result_parts)
    return result + "。" if result else ""


def _coerce_sentence_list(value: Any, limit: int = 3) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = [_safe_text(item) for item in value]
        return _dedupe_keep_order([item for item in items if item])[:limit]

    text = _safe_text(value)
    if not text:
        return []

    parts = re.split(r"[\n；;、|]+", text)
    if len(parts) <= 1:
        parts = re.split(r"[。！？!?]+", text)

    return _dedupe_keep_order([part for part in parts if _safe_text(part)])[:limit]


def _get_mode_instruction(mode: str) -> str:
    if mode == "deep":
        return (
            "面向想认真看懂这件文物的人。信息密度可以更高，"
            "要主动把历史价值、艺术价值、文化寓意、工艺细节串起来，"
            "但仍然要像你站在展柜前给一个人解释，而不是写学术小论文。"
        )
    if mode == "child":
        return (
            "面向第一次参观的人或小朋友。句子更短，词更简单，"
            "重点说清先看哪里、它是做什么的、为什么容易记住，"
            "可以适当借助生活化比喻。"
        )
    return (
        "面向普通参观者。语气自然，像一个陪你逛展的人在你耳边解释重点，"
        "不要像百科摘要，也不要像广播式导游。"
    )


def _get_explanation_limit(mode: str) -> int:
    if mode == "deep":
        return 360
    if mode == "child":
        return 220
    return 280


def _pick_mode_specific_points(context: dict, mode: str) -> list[str]:
    if mode == "deep":
        return _dedupe_keep_order(
            list(context.get("deep_points", []) or [])
            + list(context.get("craft_value_points", []) or [])
            + list(context.get("historical_role_points", []) or [])
            + list(context.get("historical_value_points", []) or [])
            + list(context.get("art_value_points", []) or [])
            + list(context.get("cultural_value_points", []) or [])
            + list(context.get("symbolism_points", []) or [])
        )[:6]

    if mode == "child":
        return _dedupe_keep_order(
            list(context.get("kid_points", []) or [])
            + list(context.get("first_impression_candidates", []) or [])
            + list(context.get("core_facts", []) or [])
            + list(context.get("interesting_points", []) or [])
        )[:5]

    return _dedupe_keep_order(
        list(context.get("watch_points", []) or [])
        + list(context.get("detail_points", []) or [])
        + list(context.get("story_points", []) or [])
        + list(context.get("symbolism_points", []) or [])
    )[:5]


def _format_lines(title: str, items: list[str]) -> str:
    items = _dedupe_keep_order(items)
    if not items:
        return f"{title}：无"
    return title + "：\n" + "\n".join(f"- {item}" for item in items)


def _format_context_for_prompt(context: dict, mode: str) -> str:
    exhibit = context["exhibit"]
    hall = context.get("hall", {})
    mode_specific_points = _pick_mode_specific_points(context, mode)

    basic_lines = [
        f"展品名称：{exhibit['name']}",
        f"所属展区：{exhibit['hall_name']}",
        f"展区主题：{exhibit['hall_theme']}",
        f"展区摘要：{hall.get('summary') or '无'}",
        f"时代：{exhibit.get('era') or '未提供'}",
        f"朝代细分：{exhibit.get('dynasty') or '未提供'}",
        f"类别：{exhibit.get('category') or '未提供'}",
        f"细分类：{exhibit.get('sub_category') or '未提供'}",
        f"材质：{exhibit.get('material') or '未提供'}",
        f"工艺：{exhibit.get('craft') or '未提供'}",
        f"用途：{exhibit.get('usage_desc') or '未提供'}",
        f"形制：{exhibit.get('shape_desc') or '未提供'}",
        f"纹样/构成元素：{exhibit.get('pattern_elements') or '未提供'}",
        f"寓意/象征：{exhibit.get('symbolism') or '未提供'}",
        f"风格标签：{exhibit.get('style_tags') or '未提供'}",
        f"推荐配色：{exhibit.get('color_palette') or '未提供'}",
        f"简要介绍：{exhibit.get('short_intro') or '无'}",
        f"深入介绍：{exhibit.get('deep_intro') or '无'}",
        f"核心价值：{exhibit.get('core_value') or '无'}",
        f"历史价值：{exhibit.get('historical_value') or '无'}",
        f"艺术价值：{exhibit.get('art_value') or '无'}",
        f"文化价值：{exhibit.get('cultural_value') or '无'}",
        f"相关人物：{exhibit.get('related_people') or '无'}",
        f"相关事件：{exhibit.get('related_events') or '无'}",
        f"相关展品提示：{exhibit.get('related_exhibits_hint') or '无'}",
        f"文创关键词：{exhibit.get('creative_keywords') or '无'}",
        f"文创文案种子：{exhibit.get('poster_copy_seed') or '无'}",
        f"与当前上下文关系：{context.get('relation_hint') or '无'}",
    ]

    blocks = [
        "\n".join(basic_lines),
        _format_lines("核心事实", context.get("core_facts", []) or []),
        _format_lines("第一眼可抓的点", context.get("first_impression_candidates", []) or []),
        _format_lines("观看重点", context.get("watch_points", []) or []),
        _format_lines("历史作用线索", context.get("historical_role_points", []) or []),
        _format_lines("工艺与细节线索", context.get("craft_value_points", []) or []),
        _format_lines("历史价值线索", context.get("historical_value_points", []) or []),
        _format_lines("艺术价值线索", context.get("art_value_points", []) or []),
        _format_lines("文化价值线索", context.get("cultural_value_points", []) or []),
        _format_lines("故事线索", context.get("story_points", []) or []),
        _format_lines("寓意与象征", context.get("symbolism_points", []) or []),
        _format_lines("路线承接线索", context.get("route_connection_points", []) or []),
        _format_lines("对照提示", context.get("comparison_points", []) or []),
        _format_lines("相关展品", context.get("related_summary_lines", []) or []),
        _format_lines("有趣点", context.get("interesting_points", []) or []),
        _format_lines("模式重点", mode_specific_points),
    ]
    return "\n\n".join(blocks)


def _build_llm_prompts(context: dict, mode: str) -> tuple[str, str]:
    context_text = _format_context_for_prompt(context, mode)

    if mode == "deep":
        length_rule = "整段 explanation 最终控制在 230 到 360 字。"
    elif mode == "child":
        length_rule = "整段 explanation 最终控制在 120 到 210 字。"
    else:
        length_rule = "整段 explanation 最终控制在 180 到 280 字。"

    system_prompt = (
        "你是湖北博物院里的个人导览助手。"
        "你现在是在陪一个人参观，而不是面对旅行团的导游，也不是广播式讲解员。"
        "你的任务是把展柜前最值得看的重点自然地说清楚。"
        "你只能依据给定资料组织表达，不要补充资料里没有的具体史实。"
        "口吻要像陪逛、提醒和解释，不要像百科条目，也不要像宣传文案。"
    )

    user_prompt = f"""
请根据下面资料，输出一段真正对单个参观者有帮助的展品讲解。

硬性要求：
1. 只输出 JSON，不要输出 markdown 代码块，不要输出额外解释。
2. JSON 格式固定为：
{{
  "intro": "开场一句，先把注意力拉到这件展品上",
  "first_impression": "告诉参观者第一眼先看哪里",
  "core_watch_points": ["观看重点1", "观看重点2"],
  "historical_role": "解释它在当时扮演什么角色，最好结合历史价值或文化背景",
  "craft_value": "解释工艺、结构、材质、细节或视觉构成为什么值得看",
  "relation_to_route": "它为什么适合出现在这条路线的这一站，没有就写空字符串",
  "compare_hint": "和相关展品怎么连着看，没有就写空字符串",
  "one_sentence_takeaway": "一句话带走的印象",
  "why_now": "为什么此刻推荐看它"
}}
3. {length_rule}
4. 每个字段都用简体中文完整句子，core_watch_points 返回 2 到 3 条短句。
5. 不要编造具体年代、尺寸、出土地点、作者等资料里没有的信息。
6. intro 不要机械重复“某某位于某展区”，也不要用“各位观众”“大家可以看到”“让我们来看”这类群体导游口吻。
7. first_impression 必须具体，至少告诉参观者一个可以观察的点。
8. historical_role 不能只说“它很重要”，必须解释它为什么重要。
9. craft_value 优先写工艺、结构、材质、用途感受、视觉组织或观看细节。
10. relation_to_route 只有在资料里确实有承接线索时才写，没有就写空字符串。
11. compare_hint 只有资料里确实有对照对象时才写，没有就写空字符串。
12. one_sentence_takeaway 要像你陪看完之后留给对方的一句话。
13. why_now 要解释为什么此刻推荐看它，尽量结合当前展区主题或路线承接。
14. 讲解对象始终只有一个人，要像在陪对方看，不要像对一群人做讲解。
15. 当前模式要求：{_get_mode_instruction(mode)}

资料如下：
{context_text}
""".strip()

    return system_prompt, user_prompt


def _clean_json_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(0)

    return cleaned.strip()


def _compose_explanation(
    intro: str,
    first_impression: str,
    core_watch_points: list[str],
    historical_role: str,
    craft_value: str,
    relation_to_route: str,
    compare_hint: str,
    one_sentence_takeaway: str,
    mode: str,
) -> str:
    parts = [
        intro,
        first_impression,
        *core_watch_points[:2],
        historical_role,
        craft_value,
        relation_to_route,
        compare_hint,
        one_sentence_takeaway,
    ]
    return _join_sentences(parts, max_len=_get_explanation_limit(mode))


def _parse_llm_result(text: str, mode: str) -> dict:
    cleaned = _clean_json_text(text)
    data = json.loads(cleaned)

    explanation = _safe_text(data.get("explanation"))
    why_now = _safe_text(data.get("why_now"))
    relation_hint = _safe_text(data.get("relation_hint"))
    if explanation and why_now:
        return {
            "intro": "",
            "first_impression": "",
            "core_watch_points": [],
            "historical_role": "",
            "craft_value": "",
            "relation_to_route": _ensure_sentence(relation_hint) if relation_hint else "",
            "compare_hint": "",
            "one_sentence_takeaway": "",
            "explanation": _ensure_sentence(explanation),
            "why_now": _ensure_sentence(why_now),
            "relation_hint": relation_hint or None,
        }

    intro = _safe_text(data.get("intro") or data.get("opening"))
    first_impression = _safe_text(data.get("first_impression") or data.get("look_point"))
    core_watch_points = _coerce_sentence_list(data.get("core_watch_points"), limit=3)
    historical_role = _safe_text(data.get("historical_role") or data.get("meaning"))
    craft_value = _safe_text(data.get("craft_value") or data.get("detail"))
    relation_to_route = _safe_text(
        data.get("relation_to_route") or data.get("connection") or data.get("relation_hint")
    )
    compare_hint = _safe_text(data.get("compare_hint"))
    one_sentence_takeaway = _safe_text(data.get("one_sentence_takeaway"))
    why_now = _safe_text(data.get("why_now"))

    if not intro:
        raise ValueError("模型 intro 为空")
    if not first_impression:
        raise ValueError("模型 first_impression 为空")
    if not historical_role:
        raise ValueError("模型 historical_role 为空")
    if not why_now:
        raise ValueError("模型 why_now 为空")

    if not core_watch_points and first_impression:
        core_watch_points = [first_impression]

    explanation_text = _compose_explanation(
        intro=intro,
        first_impression=first_impression,
        core_watch_points=core_watch_points,
        historical_role=historical_role,
        craft_value=craft_value,
        relation_to_route=relation_to_route,
        compare_hint=compare_hint,
        one_sentence_takeaway=one_sentence_takeaway,
        mode=mode,
    )

    return {
        "intro": _ensure_sentence(intro),
        "first_impression": _ensure_sentence(first_impression),
        "core_watch_points": [_ensure_sentence(item) for item in core_watch_points[:3]],
        "historical_role": _ensure_sentence(historical_role),
        "craft_value": _ensure_sentence(craft_value) if craft_value else "",
        "relation_to_route": _ensure_sentence(relation_to_route) if relation_to_route else "",
        "compare_hint": _ensure_sentence(compare_hint) if compare_hint else "",
        "one_sentence_takeaway": _ensure_sentence(one_sentence_takeaway) if one_sentence_takeaway else "",
        "explanation": explanation_text,
        "why_now": _ensure_sentence(why_now),
        "relation_hint": relation_to_route or None,
    }


def _build_template_result(context: dict, mode: str) -> dict:
    exhibit = context["exhibit"]
    hall = context.get("hall", {})

    exhibit_name = exhibit["name"]
    hall_name = exhibit["hall_name"]
    hall_theme = exhibit["hall_theme"]
    relation_hint = context.get("relation_hint") or ""

    first_impression_candidates = list(context.get("first_impression_candidates", []) or [])
    watch_points = list(context.get("watch_points", []) or [])
    historical_role_points = list(context.get("historical_role_points", []) or [])
    craft_value_points = list(context.get("craft_value_points", []) or [])
    comparison_points = list(context.get("comparison_points", []) or [])
    compare_hint_lines = list(context.get("compare_hint_lines", []) or [])
    kid_points = list(context.get("kid_points", []) or [])
    deep_points = list(context.get("deep_points", []) or [])
    core_facts = list(context.get("core_facts", []) or [])
    symbolism_points = list(context.get("symbolism_points", []) or [])
    interesting_points = list(context.get("interesting_points", []) or [])
    visual_points = list(context.get("visual_points", []) or [])
    art_value_points = list(context.get("art_value_points", []) or [])
    cultural_value_points = list(context.get("cultural_value_points", []) or [])

    if mode == "deep":
        intro = f"走到{exhibit_name}这里，你可以稍微放慢一点，它值得看的地方不只是在名气上。"
        first_impression = (
            first_impression_candidates[0]
            if first_impression_candidates
            else "你可以先看它最直观的造型、结构或者表面处理，再往细节里走。"
        )
        core_watch_points = _dedupe_keep_order(watch_points + craft_value_points + visual_points)[:3] or [
            "先抓住最显眼的造型特点",
            "再看工艺和细节怎么服务于用途",
        ]
        historical_role = (
            historical_role_points[0]
            if historical_role_points
            else f"它真正重要的地方，在于能把“{hall_theme}”从抽象概念变成能被你具体看见的器物经验。"
        )
        craft_value = (
            craft_value_points[0]
            if craft_value_points
            else art_value_points[0]
            if art_value_points
            else deep_points[0]
            if deep_points
            else "真正值得停下来的地方，不只是它有名，而是工艺、用途和文化含义压在了同一件器物里。"
        )
        relation_to_route = (
            relation_hint
            or f"把它放在“{hall_name}”这一站先看，是为了让你更具体地理解这个展区到底在讲什么。"
        )
        compare_hint = (
            comparison_points[0]
            if comparison_points
            else compare_hint_lines[0]
            if compare_hint_lines
            else ""
        )
        if exhibit.get("core_value"):
            one_sentence_takeaway = exhibit["core_value"]
        elif cultural_value_points:
            one_sentence_takeaway = cultural_value_points[0]
        else:
            one_sentence_takeaway = "看懂它，不只是记住一件名物，而是开始看懂这条路线在这一站真正想立起来的重点。"
        why_now = "现在看它比较合适，因为它能把当前展区从“看到代表文物”推进到“真正理解这一站的意义”。"
    elif mode == "child":
        intro = f"你可以先看看{exhibit_name}，它通常是这一站里比较容易一下记住的东西。"
        first_impression = (
            first_impression_candidates[0]
            if first_impression_candidates
            else "你可以先看它最特别的样子，再想想古人为什么要把它做成这样。"
        )
        core_watch_points = _dedupe_keep_order(kid_points + watch_points + interesting_points)[:2] or [
            "先找最特别的外形",
            "再看哪里和现在不一样",
        ]
        historical_role = (
            historical_role_points[0]
            if historical_role_points
            else core_facts[0]
            if core_facts
            else "它能帮你更轻松地认识古人怎么生活、怎么表达重要的事情。"
        )
        craft_value = (
            craft_value_points[0]
            if craft_value_points
            else visual_points[0]
            if visual_points
            else "别只把它当成一个旧东西，很多有意思的地方都藏在细节里。"
        )
        relation_to_route = (
            relation_hint
            if relation_hint
            else f"现在先看到它，能比较快抓住“{hall_theme}”这一站到底在讲什么。"
        )
        compare_hint = compare_hint_lines[0] if compare_hint_lines else ""
        one_sentence_takeaway = f"记住它，就像记住了这个展区里最醒目的一条线索。"
        why_now = "现在先看它，后面再看别的内容时，你会更容易把这一站连起来。"
    else:
        intro = f"走到{exhibit_name}这里，你可以先停一下，它很适合帮你把这一站的主题迅速抓住。"
        first_impression = (
            first_impression_candidates[0]
            if first_impression_candidates
            else "站在展柜前，你可以先留意它最突出的造型、结构或者表面细节。"
        )
        core_watch_points = _dedupe_keep_order(watch_points + craft_value_points + symbolism_points)[:3] or [
            "先抓住最显眼的外形特点",
            "再看细节处理",
        ]
        historical_role = (
            historical_role_points[0]
            if historical_role_points
            else f"它之所以值得看，不只是因为有名，更因为它能把“{hall_theme}”讲得更具体。"
        )
        craft_value = (
            craft_value_points[0]
            if craft_value_points
            else visual_points[0]
            if visual_points
            else "真正有意思的地方往往不在名字，而在材质、工艺和使用意味是怎么合在一起的。"
        )
        relation_to_route = (
            relation_hint
            if relation_hint
            else f"把它放在“{hall_name}”这一站先看，能帮你更快建立对这个展区主题的整体感觉。"
        )
        compare_hint = (
            comparison_points[0]
            if comparison_points
            else compare_hint_lines[0]
            if compare_hint_lines
            else ""
        )
        one_sentence_takeaway = (
            exhibit.get("core_value")
            or hall.get("summary")
            or "它像这一站里最能把主题讲清楚的一件具体对象。"
        )
        why_now = f"现在推荐你先看它，是因为它能帮你更快抓住“{hall_theme}”这一站的核心，而不是只记住一个名字。"

    explanation = _compose_explanation(
        intro=intro,
        first_impression=first_impression,
        core_watch_points=core_watch_points,
        historical_role=historical_role,
        craft_value=craft_value,
        relation_to_route=relation_to_route,
        compare_hint=compare_hint,
        one_sentence_takeaway=one_sentence_takeaway,
        mode=mode,
    )

    return {
        "mode": mode,
        "intro": _ensure_sentence(intro),
        "first_impression": _ensure_sentence(first_impression),
        "core_watch_points": [_ensure_sentence(item) for item in core_watch_points[:3]],
        "historical_role": _ensure_sentence(historical_role),
        "craft_value": _ensure_sentence(craft_value) if craft_value else "",
        "relation_to_route": _ensure_sentence(relation_to_route) if relation_to_route else "",
        "compare_hint": _ensure_sentence(compare_hint) if compare_hint else "",
        "one_sentence_takeaway": _ensure_sentence(one_sentence_takeaway) if one_sentence_takeaway else "",
        "explanation": explanation,
        "why_now": _ensure_sentence(why_now),
        "relation_hint": relation_to_route or relation_hint or None,
        "related_exhibits": context.get("related_exhibits", []),
        "source": "template",
    }


def build_exhibit_explanation(
    db: Session,
    exhibit_id: int,
    mode: str = "normal",
    current_context_exhibit_id: int | None = None,
) -> dict:
    mode = _normalize_mode(mode)

    context = build_exhibit_context(
        db=db,
        exhibit_id=exhibit_id,
        current_context_exhibit_id=current_context_exhibit_id,
        related_limit=3,
    )
    if not context:
        return {
            "mode": mode,
            "intro": "",
            "first_impression": "",
            "core_watch_points": [],
            "historical_role": "",
            "craft_value": "",
            "relation_to_route": "",
            "compare_hint": "",
            "one_sentence_takeaway": "",
            "explanation": "未找到该展品。",
            "why_now": "当前无法生成讲解。",
            "relation_hint": None,
            "related_exhibits": [],
            "source": "none",
        }

    template_result = _build_template_result(context=context, mode=mode)

    if not is_llm_configured():
        logger.warning(
            "LLM not configured, fallback to template | exhibit_id=%s | exhibit_name=%s",
            context["exhibit"]["id"],
            context["exhibit"]["name"],
        )
        return template_result

    try:
        system_prompt, user_prompt = _build_llm_prompts(context=context, mode=mode)

        start_time = time.perf_counter()
        llm_text = chat_with_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.55,
            max_tokens=320,
            timeout=(4, 10),
            max_retries=0,
        )
        llm_result = _parse_llm_result(llm_text, mode=mode)
        elapsed = time.perf_counter() - start_time

        logger.info(
            "AI exhibit explanation success | exhibit_id=%s | exhibit_name=%s | mode=%s | elapsed=%.2fs",
            context["exhibit"]["id"],
            context["exhibit"]["name"],
            mode,
            elapsed,
        )

        return {
            "mode": mode,
            "intro": llm_result["intro"] or template_result["intro"],
            "first_impression": llm_result["first_impression"] or template_result["first_impression"],
            "core_watch_points": llm_result["core_watch_points"] or template_result["core_watch_points"],
            "historical_role": llm_result["historical_role"] or template_result["historical_role"],
            "craft_value": llm_result["craft_value"] or template_result["craft_value"],
            "relation_to_route": llm_result["relation_to_route"] or template_result["relation_to_route"],
            "compare_hint": llm_result["compare_hint"] or template_result["compare_hint"],
            "one_sentence_takeaway": llm_result["one_sentence_takeaway"] or template_result["one_sentence_takeaway"],
            "explanation": llm_result["explanation"] or template_result["explanation"],
            "why_now": llm_result["why_now"] or template_result["why_now"],
            "relation_hint": llm_result["relation_hint"] or template_result["relation_hint"],
            "related_exhibits": context.get("related_exhibits", []),
            "source": "llm",
        }
    except Exception as exc:
        logger.exception(
            "AI exhibit explanation failed, fallback to template | exhibit_id=%s | exhibit_name=%s | error=%s",
            context["exhibit"]["id"],
            context["exhibit"]["name"],
            exc,
        )
        return template_result