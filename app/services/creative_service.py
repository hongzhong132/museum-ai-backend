from __future__ import annotations

import json
import re
from datetime import date
from typing import Iterable

from sqlalchemy.orm import Session

from app import models
from app.schemas import CreativePosterRequest
from app.services.image_gen_service import generate_image_relative_url
from app.services.llm_service import chat_with_llm


STYLE_HINTS = {
    "楚风雅韵": "清透明亮、清雅蓝青色调、温润、精美、文艺、克制留白，强调器物细节与诗性气息",
    "青铜史诗": "暖色偏亮、金铜与赭色层次、壮观、宏伟、开阔、史诗感，强调震撼与展陈级主视觉",
    "礼乐庄重": "偏暗黑红、深褐与古金点缀、厚重、庄严、肃穆、仪式感，强调秩序与礼乐气场",
}

CATEGORY_NEGATIVE = {
    "weapon": "人物, 人脸, 肖像, 古装人物, 武侠人物, 战士, 手持武器, 手, 身体, 战场, 历史人物场景, 动作姿势, 满月, 山水拼贴, 飞鸟装饰, 武侠海报",
    "bronze": "人物, 人脸, 群像, 古装人物, 宴会人物, 乐师人物, 剧照感, 大月亮, 山水拼贴, 悬浮祥云, 过度国潮装饰, 多件器物堆叠",
    "jade": "人物, 人脸, 模特佩戴, 首饰广告人物, 手持展示, 电商珠宝图, 网红产品照, 俗艳高饱和, 商业广告打光",
    "slip": "人物, 人脸, 书写者, 学者形象, 手拿竹简, 书房人物, 场景插画, 满月, 山水拼贴, 影视感人物场景",
    "lacquer": "人物, 人脸, 手持器物, 餐桌摆拍, 商业餐具广告图, 网图感, 生活方式广告",
    "generic": "人物, 人脸, 古装人物, 商业广告模特, 影视剧海报, 山水拼贴, 满月, 飞鸟装饰, 对称模板, 网图感, 俗艳国风素材"
}


def _safe_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _split_tags(value: str | None) -> list[str]:
    raw = _safe_text(value)
    if not raw:
        return []
    return [item.strip() for item in re.split(r"[，,、；;|\n]+", raw) if item.strip()]


def _unique_strings(values: Iterable[str], limit: int | None = None) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = _safe_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if limit is not None and len(result) >= limit:
            break
    return result


def _extract_json(text: str) -> dict | None:
    raw = _safe_text(text)
    if not raw:
        return None

    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        return None

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _shorten(text: str | None, limit: int) -> str:
    raw = _safe_text(text)
    if len(raw) <= limit:
        return raw
    return raw[:limit].rstrip("，,、；;：: ") + "…"


def _get_display_image(exhibit: models.Exhibit, asset: models.ExhibitAsset | None) -> str | None:
    image_url = getattr(exhibit, "image_url", None)
    if image_url:
        return image_url
    if asset and getattr(asset, "cover_image_url", None):
        return asset.cover_image_url
    return None


def _resolve_source_exhibits(db: Session, data: CreativePosterRequest) -> list[models.Exhibit]:
    raw_ids = []
    if data.exhibit_id:
        raw_ids.append(int(data.exhibit_id))
    raw_ids.extend(int(item) for item in (data.exhibit_ids or []) if item)

    exhibit_ids = []
    seen = set()
    for item in raw_ids:
        if item in seen:
            continue
        seen.add(item)
        exhibit_ids.append(item)

    if not exhibit_ids:
        return (
            db.query(models.Exhibit)
            .order_by(models.Exhibit.recommended_priority.desc(), models.Exhibit.id.asc())
            .limit(3)
            .all()
        )

    exhibits = db.query(models.Exhibit).filter(models.Exhibit.id.in_(exhibit_ids)).all()
    exhibit_map = {item.id: item for item in exhibits}
    return [exhibit_map[item_id] for item_id in exhibit_ids if item_id in exhibit_map][:3]


def _build_source_cards(db: Session, exhibits: list[models.Exhibit]) -> tuple[list[dict], str | None]:
    if not exhibits:
        return [], None

    exhibit_ids = [item.id for item in exhibits]
    hall_ids = [item.hall_id for item in exhibits if item.hall_id]

    assets = db.query(models.ExhibitAsset).filter(models.ExhibitAsset.exhibit_id.in_(exhibit_ids)).all()
    halls = db.query(models.MuseumHall).filter(models.MuseumHall.id.in_(hall_ids)).all()
    asset_map = {item.exhibit_id: item for item in assets}
    hall_map = {item.id: item for item in halls}

    cards = []
    first_cover = None
    for exhibit in exhibits:
        asset = asset_map.get(exhibit.id)
        hall = hall_map.get(exhibit.hall_id)
        cover_image_url = _get_display_image(exhibit, asset)
        if not first_cover and cover_image_url:
            first_cover = cover_image_url

        cards.append({
            "exhibit_id": exhibit.id,
            "exhibit_name": exhibit.name,
            "hall_name": getattr(hall, "name", None),
            "image_url": cover_image_url,
            "source_name": getattr(asset, "source_name", None),
            "source_url": getattr(asset, "source_url", None),
            "pattern_elements": _split_tags(getattr(exhibit, "pattern_elements", None))[:5],
            "style_tags": _split_tags(getattr(exhibit, "style_tags", None))[:5],
            "color_palette": _split_tags(getattr(exhibit, "color_palette", None))[:5],
            "symbolism": _split_tags(getattr(exhibit, "symbolism", None))[:5],
            "creative_keywords": _split_tags(getattr(exhibit, "creative_keywords", None))[:5],
        })
    return cards, first_cover


def _build_visual_keywords(source_cards: list[dict]) -> list[str]:
    tags = []
    for card in source_cards:
        tags.extend(card["creative_keywords"])
        tags.extend(card["style_tags"])
        tags.extend(card["pattern_elements"])
        tags.extend(card["symbolism"])
    return _unique_strings(tags, limit=10)


def _build_color_palette(source_cards: list[dict]) -> list[str]:
    tags = []
    for card in source_cards:
        tags.extend(card["color_palette"])
    return _unique_strings(tags, limit=6)


def _detect_subject_type(exhibit: models.Exhibit) -> str:
    blob = " ".join([
        _safe_text(getattr(exhibit, "name", None)),
        _safe_text(getattr(exhibit, "category", None)),
        _safe_text(getattr(exhibit, "sub_category", None)),
        _safe_text(getattr(exhibit, "usage_desc", None)),
    ]).lower()

    if any(key in blob for key in ["剑", "戈", "兵器", "矛", "戟", "weapon"]):
        return "weapon"
    if any(key in blob for key in ["玉", "玉佩", "jade"]):
        return "jade"
    if any(key in blob for key in ["简", "简牍", "竹木", "文字资料", "楚简", "slip"]):
        return "slip"
    if any(key in blob for key in ["漆", "lacquer"]):
        return "lacquer"
    if any(key in blob for key in ["鼓", "编钟", "编磬", "乐器", "钟", "磬"]):
        return "bronze"
    if any(key in blob for key in ["鼎", "尊", "盘", "礼器", "青铜", "bronze"]):
        return "bronze"
    return "generic"


def _infer_message_mood(message: str | None, style_mode: str) -> str:
    text = _safe_text(message)
    if not text:
        if style_mode == "楚风雅韵":
            return "宁静、清透、文艺、留白"
        if style_mode == "青铜史诗":
            return "壮阔、开阔、明亮、宏伟"
        return "肃穆、克制、庄严、厚重"

    blob = text.lower()
    if any(key in blob for key in ["静", "清", "风", "月", "回望", "悠长", "柔", "温", "诗", "梦"]):
        return "宁静、清透、诗性、文艺、留白"
    if any(key in blob for key in ["宏伟", "壮观", "史诗", "辽阔", "震撼", "炽热", "辉煌", "高昂"]):
        return "壮阔、明亮、宏伟、暖光、张力"
    if any(key in blob for key in ["庄", "重", "礼", "肃", "敬", "沉", "厚", "仪式"]):
        return "庄严、肃穆、厚重、克制、仪式感"
    return "克制、文艺、博物馆高级感、含蓄留白"


def _build_title(data: CreativePosterRequest, first_exhibit_name: str) -> str:
    first_name = _safe_text(first_exhibit_name)
    if first_name and len(first_name) <= 10:
        return first_name
    route_theme = _safe_text(data.route_theme)
    if route_theme:
        return _shorten(route_theme, 10) or "楚韵观览"
    return "楚韵观览"


def _fallback_creative_result(
    data: CreativePosterRequest,
    exhibits: list[models.Exhibit],
    source_cards: list[dict],
    cover_image_url: str | None,
) -> dict:
    first_exhibit = exhibits[0] if exhibits else None
    first_name = _safe_text(getattr(first_exhibit, "name", None)) or (source_cards[0]["exhibit_name"] if source_cards else "湖北省博物馆")
    visit_date = _safe_text(data.visit_date) or str(date.today())
    visitor_name = _safe_text(data.visitor_name)
    style_mode = _safe_text(data.style_mode) or "楚风雅韵"
    visual_keywords = _build_visual_keywords(source_cards)
    palette = _build_color_palette(source_cards)

    return {
        "title": _build_title(data, first_name),
        "subtitle": "湖北省博物馆数字纪念",
        "poster_copy": "",
        "commemorative_text": _shorten(_safe_text(data.message) or "愿此刻可长久回望。", 12),
        "image_prompt": "",
        "style_mode": style_mode,
        "route_title": _safe_text(data.route_title) or None,
        "route_theme": _safe_text(data.route_theme) or None,
        "route_summary": _safe_text(data.route_summary) or None,
        "visitor_name": visitor_name or None,
        "visit_date": visit_date,
        "poster_image_url": None,
        "fallback_cover_image_url": cover_image_url,
        "visual_keywords": visual_keywords,
        "color_palette": palette,
        "source": "template",
        "image_source": "fallback",
        "source_exhibits": source_cards,
    }


def _build_llm_prompts(data: CreativePosterRequest, exhibits: list[models.Exhibit], source_cards: list[dict]) -> tuple[str, str]:
    style_mode = _safe_text(data.style_mode) or "楚风雅韵"
    style_hint = STYLE_HINTS.get(style_mode, STYLE_HINTS["楚风雅韵"])

    system_prompt = (
        "你是湖北省博物馆 AI 文创策展助手。请基于路线主题、重点文物和个人寄语，"
        "生成极简、克制、适合放在海报图下方信息区的短文案。"
        "整体必须重画面、轻文本，不能像宣传稿，也不能堆砌形容词。"
        "必须严格输出 JSON，不要输出任何额外说明。"
    )

    exhibit_lines = []
    for exhibit, card in zip(exhibits, source_cards):
        exhibit_lines.append(
            "\n".join([
                f"文物：{exhibit.name}",
                f"朝代/时代：{_safe_text(getattr(exhibit, 'dynasty', None)) or _safe_text(getattr(exhibit, 'era', None))}",
                f"类别：{_safe_text(getattr(exhibit, 'category', None))}",
                f"纹样元素：{'、'.join(card['pattern_elements'])}",
                f"风格标签：{'、'.join(card['style_tags'])}",
                f"色彩建议：{'、'.join(card['color_palette'])}",
                f"文化寓意：{'、'.join(card['symbolism'])}",
                f"文创关键词：{'、'.join(card['creative_keywords'])}",
                f"海报文案种子：{_safe_text(getattr(exhibit, 'poster_copy_seed', None))}",
            ])
        )

    user_prompt = f"""
请基于以下信息生成湖北省博物馆数字纪念海报的极简文字。

路线标题：{_safe_text(data.route_title)}
路线主题：{_safe_text(data.route_theme)}
路线摘要：{_safe_text(data.route_summary)}
海报风格：{style_mode}
风格提示：{style_hint}
参观者署名：{_safe_text(data.visitor_name)}
参观日期：{_safe_text(data.visit_date) or str(date.today())}
寄语：{_safe_text(data.message)}

核心文物信息：
{chr(10).join(exhibit_lines)}

输出要求：
1. 整体重画面轻文本。
2. title 控制在 4 到 10 个字，优先直接用文物名。
3. subtitle 控制在 6 到 14 个字。
4. poster_copy 必须为空字符串。
5. commemorative_text 控制在 6 到 12 个字，要符合寄语气质与风格。
6. 不要生成长句，不要煽情，不要解释。

请输出 JSON，字段必须严格为：
{{
  "title": "主标题",
  "subtitle": "副标题",
  "poster_copy": "",
  "commemorative_text": "短纪念语"
}}
"""
    return system_prompt, user_prompt


def _merge_llm_result(fallback: dict, parsed: dict | None) -> dict:
    if not parsed:
        return fallback

    return {
        **fallback,
        "title": _shorten(parsed.get("title"), 10) or fallback["title"],
        "subtitle": _shorten(parsed.get("subtitle"), 14) or fallback["subtitle"],
        "poster_copy": "",
        "commemorative_text": _shorten(parsed.get("commemorative_text"), 12) or fallback["commemorative_text"],
        "source": "llm",
    }


def _join_values(values: Iterable[str], limit: int = 5) -> str:
    picked = _unique_strings(values, limit=limit)
    return "、".join(picked)


def _build_object_prompt(data: CreativePosterRequest, exhibit: models.Exhibit, source_cards: list[dict]) -> tuple[str, str]:
    style_mode = _safe_text(data.style_mode) or "楚风雅韵"
    style_hint = STYLE_HINTS.get(style_mode, STYLE_HINTS["楚风雅韵"])
    subject_type = _detect_subject_type(exhibit)
    mood_hint = _infer_message_mood(data.message, style_mode)

    tags = _build_visual_keywords(source_cards)
    palette = _build_color_palette(source_cards)
    route_theme = _safe_text(data.route_theme) or _safe_text(data.route_title)
    exhibit_name = _safe_text(getattr(exhibit, "name", None)) or "馆藏文物"

    material = _safe_text(getattr(exhibit, "material", None))
    craft = _safe_text(getattr(exhibit, "craft", None))
    shape_desc = _safe_text(getattr(exhibit, "shape_desc", None))
    pattern = _join_values(_split_tags(getattr(exhibit, "pattern_elements", None)), limit=4)
    symbolism = _join_values(_split_tags(getattr(exhibit, "symbolism", None)), limit=3)
    color_text = _join_values(palette, limit=4) or _join_values(_split_tags(getattr(exhibit, "color_palette", None)), limit=4)
    keyword_text = _join_values(tags, limit=6)
    prompt_seed = _safe_text(getattr(exhibit, "image_prompt_seed", None))

    common_lines = [
        f"以{exhibit_name}文物本体为唯一主视觉。",
        "中国博物馆高级艺术海报主视觉，重画面、轻文本，主体绝对明确。",
        "构图克制，画面干净，留白充足，细节精致，不要拼贴感，不要素材堆砌。",
        "背景只作为衬托，不要抢主体，不加入无关的大月亮、山水、飞鸟、祥云、人物或其他主角。",
        f"整体风格：{style_hint}。",
        f"寄语转化后的画面气质：{mood_hint}。",
    ]

    if route_theme:
        common_lines.append(f"参观主题参考：{route_theme}。")
    if material:
        common_lines.append(f"材质质感：{material}。")
    if craft:
        common_lines.append(f"工艺特征：{craft}。")
    if shape_desc:
        common_lines.append(f"器形特征：{shape_desc}。")
    if pattern:
        common_lines.append(f"纹样元素：{pattern}。")
    if symbolism:
        common_lines.append(f"文化寓意：{symbolism}。")
    if color_text:
        common_lines.append(f"主色方向：{color_text}。")
    if keyword_text:
        common_lines.append(f"视觉关键词：{keyword_text}。")
    if prompt_seed:
        common_lines.append(f"补充提示：{prompt_seed}。")

    if subject_type == "weapon":
        subject_lines = [
            "突出单件兵器本体，垂直或中轴式构图，修长、锋利、精致、克制。",
            "强调金属冷光、器物纹饰、刃部细节与王权式压迫感。",
            "不要人物持剑，不要动作场面，不要武侠或历史人物海报。"
        ]
    elif subject_type == "jade":
        subject_lines = [
            "突出玉器温润、细腻、通透的材质美感，近景或半近景构图。",
            "整体更清雅、更文艺，避免电商首饰图和俗艳珠宝广告感。",
            "强调精美、细节、呼吸感和雅致留白。"
        ]
    elif subject_type == "slip":
        subject_lines = [
            "突出简牍本体、编联结构与书写痕迹，画面清瘦、安静、克制。",
            "强调文字载体的历史气息与书写质感，不做人物书写场景。"
        ]
    elif subject_type == "lacquer":
        subject_lines = [
            "突出漆器表面光泽、层次、朱黑或深色漆感，画面精致且生活审美突出。",
            "避免商业餐具广告图或家居样板间氛围。"
        ]
    else:
        subject_lines = [
            "突出单件器物本体与展陈级光影，画面庄重、完整、具有高级感。",
            "避免模板化国潮拼贴和装饰素材堆砌。"
        ]

    prompt = " ".join(common_lines + subject_lines)

    extra_negative = CATEGORY_NEGATIVE.get(subject_type, CATEGORY_NEGATIVE["generic"])
    extra_negative += ", 大月亮, 山水背景主角化, 飞鸟装饰, 悬浮装饰元素, 对称模板, 国潮拼贴, 复杂边框, 海报大片文字"
    return prompt, extra_negative


def generate_creative_poster(db: Session, data: CreativePosterRequest) -> dict:
    exhibits = _resolve_source_exhibits(db, data)
    if not exhibits:
        raise RuntimeError("当前没有可用于生成文创的文物数据。")

    source_cards, cover_image_url = _build_source_cards(db, exhibits)
    result = _fallback_creative_result(data, exhibits, source_cards, cover_image_url)

    try:
        system_prompt, user_prompt = _build_llm_prompts(data, exhibits, source_cards)
        llm_text = chat_with_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.55,
            max_tokens=220,
            timeout=14,
            max_retries=0,
        )
        parsed = _extract_json(llm_text)
        result = _merge_llm_result(result, parsed)
    except Exception:
        pass

    first_exhibit = exhibits[0]
    positive_prompt, extra_negative = _build_object_prompt(data, first_exhibit, source_cards)
    result["image_prompt"] = positive_prompt

    try:
        relative_url, image_meta = generate_image_relative_url(
            positive_prompt,
            extra_negative_prompt=extra_negative,
        )
        result["poster_image_url"] = relative_url
        result["image_source"] = "generated"
        result["image_seed"] = image_meta.get("seed")
    except Exception:
        result["poster_image_url"] = None
        result["image_source"] = "fallback"

    return result
