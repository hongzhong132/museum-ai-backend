from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import crud, models
from app.database import get_db
from app.schemas import (
    CreativePosterRequest,
    CreativePosterResponse,
    ExhibitAssetResponse,
    ExhibitBase,
    ExhibitDetailResponse,
    ExhibitExplainResponse,
    ExhibitGraphResponse,
    ExplainRequest,
    RelatedExhibitCard,
)
from app.services.creative_service import generate_creative_poster
from app.services.explainer import build_exhibit_explanation, get_related_exhibit_cards
from app.services.tts_service import get_or_create_tts_audio

router = APIRouter(prefix="/api/exhibits", tags=["exhibits"])


RELATION_TYPE_LABELS = {
    "same_theme": "同主题",
    "same_craft": "同工艺",
    "same_material": "同材质",
    "same_hall": "同馆延伸",
    "background_for": "背景补充",
    "contrast": "对照观看",
    "route_next": "推荐下一站",
    "thematic": "专题延展",
}

ERA_RANK_KEYWORDS = [
    ("新石器", 0),
    ("夏", 1),
    ("商", 2),
    ("西周", 3),
    ("东周", 4),
    ("春秋", 5),
    ("战国", 6),
    ("先秦", 7),
    ("秦", 8),
    ("西汉", 9),
    ("东汉", 10),
    ("汉", 11),
    ("三国", 12),
    ("晋", 13),
    ("南北朝", 14),
    ("隋", 15),
    ("唐", 16),
    ("宋", 17),
    ("元", 18),
    ("明", 19),
    ("清", 20),
    ("近代", 21),
]


def _safe_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _split_tag_text(value) -> list[str]:
    raw = _safe_text(value)
    if not raw:
        return []
    for sep in ["，", ",", "、", "；", ";", "|", "\n", "\t"]:
        raw = raw.replace(sep, " ")
    return [item.strip() for item in raw.split(" ") if item.strip()]


def _merge_unique_strings(*groups) -> list[str]:
    result = []
    seen = set()
    for group in groups:
        if not group:
            continue
        for value in group:
            text = _safe_text(value)
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
    return result


def _serialize_exhibit_base(exhibit: models.Exhibit) -> dict:
    return {
        "id": exhibit.id,
        "hall_id": exhibit.hall_id,
        "name": exhibit.name,
        "code": exhibit.code,
        "era": getattr(exhibit, "era", None),
        "dynasty": getattr(exhibit, "dynasty", None),
        "category": getattr(exhibit, "category", None),
        "sub_category": getattr(exhibit, "sub_category", None),
        "material": getattr(exhibit, "material", None),
        "craft": getattr(exhibit, "craft", None),
        "usage_desc": getattr(exhibit, "usage_desc", None),
        "short_intro": getattr(exhibit, "short_intro", None),
        "deep_intro": getattr(exhibit, "deep_intro", None),
        "core_value": getattr(exhibit, "core_value", None),
        "historical_value": getattr(exhibit, "historical_value", None),
        "art_value": getattr(exhibit, "art_value", None),
        "cultural_value": getattr(exhibit, "cultural_value", None),
        "watch_points": getattr(exhibit, "watch_points", None),
        "story_points": getattr(exhibit, "story_points", None),
        "detail_points": getattr(exhibit, "detail_points", None),
        "kid_points": getattr(exhibit, "kid_points", None),
        "deep_points": getattr(exhibit, "deep_points", None),
        "shape_desc": getattr(exhibit, "shape_desc", None),
        "pattern_elements": getattr(exhibit, "pattern_elements", None),
        "symbolism": getattr(exhibit, "symbolism", None),
        "style_tags": getattr(exhibit, "style_tags", None),
        "color_palette": getattr(exhibit, "color_palette", None),
        "interesting_points": getattr(exhibit, "interesting_points", None),
        "related_people": getattr(exhibit, "related_people", None),
        "related_events": getattr(exhibit, "related_events", None),
        "related_exhibits_hint": getattr(exhibit, "related_exhibits_hint", None),
        "keywords": getattr(exhibit, "keywords", None),
        "creative_keywords": getattr(exhibit, "creative_keywords", None),
        "poster_copy_seed": getattr(exhibit, "poster_copy_seed", None),
        "image_prompt_seed": getattr(exhibit, "image_prompt_seed", None),
        "is_featured": getattr(exhibit, "is_featured", None),
        "recommended_priority": getattr(exhibit, "recommended_priority", None),
        "recommended_duration_min": getattr(exhibit, "recommended_duration_min", None),
        "image_url": getattr(exhibit, "image_url", None),
    }


def _build_absolute_url(request: Request | None, relative_url: str | None) -> str | None:
    if not request or not relative_url:
        return None
    return f"{str(request.base_url).rstrip('/')}" + relative_url


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _relation_rank(relation: models.NarrativeRelation | None) -> float:
    return _safe_float(getattr(relation, "strength_score", None)) or 0.0


def _relation_label(relation_type: str | None) -> str | None:
    text = _safe_text(relation_type)
    if not text:
        return None
    return RELATION_TYPE_LABELS.get(text) or text


def _era_rank(text: str | None) -> int:
    raw = _safe_text(text)
    if not raw:
        return 999
    for keyword, rank in ERA_RANK_KEYWORDS:
        if keyword in raw:
            return rank
    return 999


def _get_assets_map(db: Session, exhibit_ids: list[int]) -> dict[int, models.ExhibitAsset]:
    if not exhibit_ids:
        return {}
    assets = (
        db.query(models.ExhibitAsset)
        .filter(models.ExhibitAsset.exhibit_id.in_(exhibit_ids))
        .all()
    )
    return {asset.exhibit_id: asset for asset in assets}


def _get_halls_map(db: Session, hall_ids: list[int]) -> dict[int, models.MuseumHall]:
    if not hall_ids:
        return {}
    halls = db.query(models.MuseumHall).filter(models.MuseumHall.id.in_(hall_ids)).all()
    return {hall.id: hall for hall in halls}


def _get_display_image(exhibit: models.Exhibit, asset: models.ExhibitAsset | None = None) -> str | None:
    image_url = getattr(exhibit, "image_url", None)
    if image_url:
        return image_url
    if asset and getattr(asset, "cover_image_url", None):
        return asset.cover_image_url
    return None


def _serialize_asset(
    asset: models.ExhibitAsset | None,
    request: Request | None = None,
    exhibit: models.Exhibit | None = None,
) -> dict:
    if not asset:
        return {
            "has_assets": False,
            "cover_image_url": None,
            "detail_image_url_1": None,
            "detail_image_url_2": None,
            "detail_image_urls": [],
            "image_caption": None,
            "source_name": None,
            "source_url": None,
            "copyright_note": None,
            "audio_script": None,
            "audio_url": None,
            "graph_summary": None,
        }

    detail_image_url_1 = getattr(asset, "detail_image_url_1", None)
    detail_image_url_2 = getattr(asset, "detail_image_url_2", None)
    detail_urls = [url for url in [detail_image_url_1, detail_image_url_2] if url]

    audio_url = None
    if exhibit and getattr(asset, "audio_script", None):
        try:
            relative_audio_url = get_or_create_tts_audio(exhibit.code, asset.audio_script)
            audio_url = _build_absolute_url(request, relative_audio_url)
        except Exception as exc:
            print(f"[tts] 生成失败 exhibit={exhibit.code}: {exc}")
            audio_url = None

    return {
        "has_assets": True,
        "cover_image_url": getattr(asset, "cover_image_url", None),
        "detail_image_url_1": detail_image_url_1,
        "detail_image_url_2": detail_image_url_2,
        "detail_image_urls": detail_urls,
        "image_caption": getattr(asset, "image_caption", None),
        "source_name": getattr(asset, "source_name", None),
        "source_url": getattr(asset, "source_url", None),
        "copyright_note": getattr(asset, "copyright_note", None),
        "audio_script": getattr(asset, "audio_script", None),
        "audio_url": audio_url,
        "graph_summary": getattr(asset, "graph_summary", None),
    }


def _serialize_graph_node(
    exhibit: models.Exhibit,
    hall: models.MuseumHall | None = None,
    relation: models.NarrativeRelation | None = None,
    asset: models.ExhibitAsset | None = None,
    is_center: bool = False,
) -> dict:
    return {
        "id": exhibit.id,
        "name": exhibit.name,
        "hall_id": exhibit.hall_id,
        "hall_name": getattr(hall, "name", None),
        "era": getattr(exhibit, "era", None),
        "dynasty": getattr(exhibit, "dynasty", None),
        "category": getattr(exhibit, "category", None),
        "sub_category": getattr(exhibit, "sub_category", None),
        "material": getattr(exhibit, "material", None),
        "craft": getattr(exhibit, "craft", None),
        "usage_desc": getattr(exhibit, "usage_desc", None),
        "shape_desc": getattr(exhibit, "shape_desc", None),
        "pattern_elements": getattr(exhibit, "pattern_elements", None),
        "symbolism": getattr(exhibit, "symbolism", None),
        "style_tags": getattr(exhibit, "style_tags", None),
        "color_palette": getattr(exhibit, "color_palette", None),
        "creative_keywords": getattr(exhibit, "creative_keywords", None),
        "core_value": getattr(exhibit, "core_value", None),
        "short_intro": getattr(exhibit, "short_intro", None),
        "image_url": _get_display_image(exhibit, asset),
        "relation_type": getattr(relation, "relation_type", None),
        "relation_summary": getattr(relation, "relation_summary", None),
        "strength_score": _safe_float(getattr(relation, "strength_score", None)) if relation else None,
        "is_center": is_center,
    }


def _serialize_graph_edge(
    source_exhibit: models.Exhibit,
    target_exhibit: models.Exhibit,
    relation: models.NarrativeRelation,
) -> dict:
    return {
        "source_id": source_exhibit.id,
        "source_name": source_exhibit.name,
        "target_id": target_exhibit.id,
        "target_name": target_exhibit.name,
        "relation_type": getattr(relation, "relation_type", None),
        "relation_summary": getattr(relation, "relation_summary", None),
        "strength_score": _safe_float(getattr(relation, "strength_score", None)),
    }


def _build_graph_summary(asset: models.ExhibitAsset | None, related_nodes: list[dict]) -> str | None:
    asset_summary = getattr(asset, "graph_summary", None) if asset else None
    if asset_summary:
        return asset_summary
    if not related_nodes:
        return None
    top_labels = []
    for node in related_nodes[:3]:
        label = _relation_label(node.get("relation_type"))
        if label and label not in top_labels:
            top_labels.append(label)
    if top_labels:
        return f"当前可从{'、'.join(top_labels)}等角度继续延伸理解这件文物。"
    return "当前可以沿着相关文物继续展开理解。"


def _build_relation_type_stats(related_nodes: list[dict]) -> list[dict]:
    counter: dict[str, int] = defaultdict(int)
    for node in related_nodes:
        key = _safe_text(node.get("relation_type")) or "other"
        counter[key] += 1
    result = [
        {"type": key, "label": _relation_label(key) or "其他关联", "count": count}
        for key, count in counter.items()
    ]
    result.sort(key=lambda item: item["count"], reverse=True)
    return result


def _build_timeline_nodes(exhibit: models.Exhibit, center_node: dict, related_nodes: list[dict]) -> list[dict]:
    dedup: dict[int, dict] = {}
    for node in [center_node, *related_nodes]:
        node_id = node.get("id")
        if not node_id:
            continue
        dedup[node_id] = node

    def sort_key(item: dict):
        time_text = _safe_text(item.get("dynasty")) or _safe_text(item.get("era"))
        return (_era_rank(time_text), 0 if item.get("is_center") else 1, -(_safe_float(item.get("strength_score")) or 0.0), item.get("id") or 0)

    timeline_items = []
    for node in sorted(dedup.values(), key=sort_key):
        summary = _safe_text(node.get("relation_summary")) or _safe_text(node.get("short_intro"))
        if node.get("is_center"):
            summary = _safe_text(getattr(exhibit, "core_value", None)) or _safe_text(getattr(exhibit, "short_intro", None)) or summary
        timeline_items.append({
            "id": node.get("id"),
            "name": node.get("name"),
            "time_label": _safe_text(node.get("dynasty")) or _safe_text(node.get("era")),
            "subtitle": " · ".join([
                text
                for text in [
                    _safe_text(node.get("era")),
                    _safe_text(node.get("category")),
                    _relation_label(node.get("relation_type")) if not node.get("is_center") else "中心文物",
                ]
                if text
            ]),
            "summary": summary,
            "relation_type": node.get("relation_type"),
            "relation_label": _relation_label(node.get("relation_type")) if not node.get("is_center") else "中心文物",
            "is_center": bool(node.get("is_center")),
        })
    return timeline_items


def _build_craft_sections(exhibit: models.Exhibit, related_nodes: list[dict]) -> list[dict]:
    current_tags = _merge_unique_strings(
        [getattr(exhibit, "material", None)],
        [getattr(exhibit, "craft", None)],
        [getattr(exhibit, "usage_desc", None)],
        [getattr(exhibit, "shape_desc", None)],
    )[:6]

    same_craft_nodes = [node for node in related_nodes if _safe_text(node.get("relation_type")) in {"same_craft", "same_material"}]
    contrast_nodes = [node for node in related_nodes if _safe_text(node.get("relation_type")) in {"contrast", "background_for"}]
    same_theme_nodes = [node for node in related_nodes if _safe_text(node.get("relation_type")) in {"same_theme", "thematic", "same_hall"}]

    sections = [
        {
            "key": "current",
            "title": "当前文物的工艺指纹",
            "subtitle": "从材质、工艺、用途和器型先建立基础理解",
            "description": _safe_text(getattr(exhibit, "core_value", None)) or _safe_text(getattr(exhibit, "short_intro", None)) or "先抓住当前文物本身的工艺与用途，再去看延伸对象。",
            "tags": current_tags,
            "related_nodes": [],
        }
    ]

    if same_craft_nodes:
        sections.append({
            "key": "same_craft",
            "title": "同工艺 / 同材质对照",
            "subtitle": "适合看“怎么做出来”与“同材质不同表达”",
            "description": "把当前文物和这些相关文物放在一起看，更容易建立工艺谱系感。",
            "tags": _merge_unique_strings(
                *[_split_tag_text(node.get("material")) for node in same_craft_nodes],
                *[_split_tag_text(node.get("craft")) for node in same_craft_nodes],
            )[:6],
            "related_nodes": same_craft_nodes[:3],
        })

    if contrast_nodes:
        sections.append({
            "key": "contrast",
            "title": "用途与表达对照",
            "subtitle": "适合观察礼器、兵器、生活器用之间的气质差异",
            "description": "这些关联点往往不是“做法一样”，而是“对照之后更好懂”。",
            "tags": _merge_unique_strings(
                *[_split_tag_text(node.get("category")) for node in contrast_nodes],
                *[_split_tag_text(node.get("usage_desc")) for node in contrast_nodes],
            )[:6],
            "related_nodes": contrast_nodes[:3],
        })

    if same_theme_nodes:
        sections.append({
            "key": "theme_extend",
            "title": "主题延展补充",
            "subtitle": "适合把单件文物放回更完整的文化语境",
            "description": "这些节点更偏向主题、馆区与叙事线索的补充。",
            "tags": _merge_unique_strings(
                *[_split_tag_text(node.get("hall_name")) for node in same_theme_nodes],
                *[_split_tag_text(node.get("category")) for node in same_theme_nodes],
            )[:6],
            "related_nodes": same_theme_nodes[:3],
        })

    return sections


def _build_creative_groups(exhibit: models.Exhibit, related_nodes: list[dict]) -> list[dict]:
    pattern_values = _merge_unique_strings(
        _split_tag_text(getattr(exhibit, "pattern_elements", None)),
        *[_split_tag_text(node.get("pattern_elements")) for node in related_nodes],
    )
    style_values = _merge_unique_strings(
        _split_tag_text(getattr(exhibit, "style_tags", None)),
        *[_split_tag_text(node.get("style_tags")) for node in related_nodes],
        _split_tag_text(getattr(exhibit, "color_palette", None)),
        *[_split_tag_text(node.get("color_palette")) for node in related_nodes],
    )
    meaning_values = _merge_unique_strings(
        _split_tag_text(getattr(exhibit, "symbolism", None)),
        *[_split_tag_text(node.get("symbolism")) for node in related_nodes],
    )
    creative_values = _merge_unique_strings(
        _split_tag_text(getattr(exhibit, "creative_keywords", None)),
        *[_split_tag_text(node.get("creative_keywords")) for node in related_nodes],
    )
    prompt_values = _merge_unique_strings(
        [getattr(exhibit, "poster_copy_seed", None)],
        [getattr(exhibit, "image_prompt_seed", None)],
    )

    groups = []
    if pattern_values:
        groups.append({
            "key": "pattern",
            "title": "纹样元素",
            "description": "可直接作为文创海报、周边纹样和装饰元素的文化来源。",
            "values": pattern_values[:8],
        })
    if style_values:
        groups.append({
            "key": "style",
            "title": "风格与色彩",
            "description": "适合转成画面气质、配色方案和视觉风格标签。",
            "values": style_values[:8],
        })
    if meaning_values:
        groups.append({
            "key": "meaning",
            "title": "文化寓意",
            "description": "适合放进文创文案或生成图的文化说明层。",
            "values": meaning_values[:8],
        })
    if creative_values:
        groups.append({
            "key": "creative",
            "title": "文创关键词",
            "description": "当前最适合直接拿来拼提示词的一组关键词。",
            "values": creative_values[:10],
        })
    if prompt_values:
        groups.append({
            "key": "prompt_seed",
            "title": "文案 / 提示词种子",
            "description": "这些句子可以继续加工成海报文案或生图提示词。",
            "values": prompt_values[:3],
        })
    return groups


def _get_top_hall_exhibits(db: Session, hall_id: int, exclude_exhibit_id: int | None = None, limit: int = 3):
    query = db.query(models.Exhibit).filter(models.Exhibit.hall_id == hall_id)
    if exclude_exhibit_id:
        query = query.filter(models.Exhibit.id != exclude_exhibit_id)
    exhibits = query.all()
    exhibits.sort(
        key=lambda item: (
            -(getattr(item, "is_featured", 0) or 0),
            -(getattr(item, "recommended_priority", 0) or 0),
            getattr(item, "id", 0),
        )
    )
    return exhibits[:limit]


def _build_hall_chain(
    db: Session,
    exhibit: models.Exhibit,
    center_hall: models.MuseumHall | None,
    assets_map: dict[int, models.ExhibitAsset],
    halls_map: dict[int, models.MuseumHall],
) -> dict | None:
    if not center_hall:
        return None

    current_hall = {
        "id": center_hall.id,
        "name": center_hall.name,
        "code": center_hall.code,
        "floor": center_hall.floor,
        "zone": center_hall.zone,
        "theme": center_hall.theme,
        "summary": center_hall.summary,
        "recommended_duration_min": center_hall.recommended_duration_min,
    }

    same_hall_exhibits = []
    for item in _get_top_hall_exhibits(db, center_hall.id, exclude_exhibit_id=exhibit.id, limit=4):
        same_hall_exhibits.append(
            _serialize_graph_node(
                item,
                hall=center_hall,
                asset=assets_map.get(item.id),
            )
        )

    hall_relations = (
        db.query(models.NarrativeRelation)
        .filter(
            models.NarrativeRelation.source_type == "hall",
            models.NarrativeRelation.target_type == "hall",
            models.NarrativeRelation.source_id == center_hall.id,
        )
        .all()
    )
    strongest_hall_relation_by_target: dict[int, models.NarrativeRelation] = {}
    for relation in hall_relations:
        existing = strongest_hall_relation_by_target.get(relation.target_id)
        if not existing or _relation_rank(relation) > _relation_rank(existing):
            strongest_hall_relation_by_target[relation.target_id] = relation

    edges = (
        db.query(models.HallEdge)
        .filter(models.HallEdge.from_hall_id == center_hall.id)
        .all()
    )
    edge_by_target: dict[int, models.HallEdge] = {}
    for edge in edges:
        existing = edge_by_target.get(edge.to_hall_id)
        if not existing:
            edge_by_target[edge.to_hall_id] = edge
            continue
        existing_weight = (getattr(existing, "is_recommended", 0) or 0, -(getattr(existing, "walk_minutes", 999) or 999))
        current_weight = (getattr(edge, "is_recommended", 0) or 0, -(getattr(edge, "walk_minutes", 999) or 999))
        if current_weight > existing_weight:
            edge_by_target[edge.to_hall_id] = edge

    target_hall_ids = _merge_unique_strings([str(k) for k in edge_by_target.keys()], [str(k) for k in strongest_hall_relation_by_target.keys()])
    target_hall_ids = [int(item) for item in target_hall_ids if str(item).isdigit()]

    next_halls = []
    for hall_id in target_hall_ids:
        hall = halls_map.get(hall_id) or crud.get_hall_by_id(db, hall_id)
        if not hall:
            continue
        edge = edge_by_target.get(hall_id)
        relation = strongest_hall_relation_by_target.get(hall_id)
        key_exhibits = [item.name for item in _get_top_hall_exhibits(db, hall_id, limit=3)]
        next_halls.append({
            "hall_id": hall.id,
            "name": hall.name,
            "theme": hall.theme,
            "summary": hall.summary,
            "walk_minutes": getattr(edge, "walk_minutes", None) if edge else None,
            "relation_type": getattr(relation, "relation_type", None),
            "relation_label": _relation_label(getattr(relation, "relation_type", None)),
            "relation_summary": getattr(relation, "relation_summary", None) or getattr(edge, "remark", None),
            "key_exhibits": key_exhibits,
        })

    next_halls.sort(
        key=lambda item: (
            0 if item.get("relation_label") else 1,
            999 if item.get("walk_minutes") is None else item.get("walk_minutes"),
            item.get("hall_id") or 0,
        )
    )

    return {
        "current_hall": current_hall,
        "same_hall_exhibits": same_hall_exhibits,
        "next_halls": next_halls[:4],
    }


def _build_exhibit_graph_payload(db: Session, exhibit_id: int, limit: int = 6) -> dict | None:
    exhibit = crud.get_exhibit_by_id(db, exhibit_id)
    if not exhibit:
        return None

    center_asset = (
        db.query(models.ExhibitAsset)
        .filter(models.ExhibitAsset.exhibit_id == exhibit.id)
        .first()
    )
    center_hall = crud.get_hall_by_id(db, exhibit.hall_id)

    relations = (
        db.query(models.NarrativeRelation)
        .filter(
            models.NarrativeRelation.source_type == "exhibit",
            models.NarrativeRelation.target_type == "exhibit",
            or_(
                models.NarrativeRelation.source_id == exhibit.id,
                models.NarrativeRelation.target_id == exhibit.id,
            ),
        )
        .all()
    )

    strongest_relation_by_other_id: dict[int, models.NarrativeRelation] = {}
    for relation in relations:
        other_id = relation.target_id if relation.source_id == exhibit.id else relation.source_id
        if other_id == exhibit.id:
            continue
        existing = strongest_relation_by_other_id.get(other_id)
        if not existing or _relation_rank(relation) > _relation_rank(existing):
            strongest_relation_by_other_id[other_id] = relation

    sorted_pairs = sorted(
        strongest_relation_by_other_id.items(),
        key=lambda item: _relation_rank(item[1]),
        reverse=True,
    )[:limit]

    related_ids = [other_id for other_id, _ in sorted_pairs]
    related_exhibits = []
    if related_ids:
        related_exhibits = db.query(models.Exhibit).filter(models.Exhibit.id.in_(related_ids)).all()

    related_exhibit_map = {item.id: item for item in related_exhibits}
    assets_map = _get_assets_map(db, [exhibit.id, *related_ids])
    hall_ids = [exhibit.hall_id] + [item.hall_id for item in related_exhibits if item.hall_id]
    halls_map = _get_halls_map(db, hall_ids)

    center_node = _serialize_graph_node(
        exhibit,
        hall=center_hall or halls_map.get(exhibit.hall_id),
        asset=assets_map.get(exhibit.id, center_asset),
        is_center=True,
    )

    related_nodes = []
    edges = []
    for other_id, relation in sorted_pairs:
        related_exhibit = related_exhibit_map.get(other_id)
        if not related_exhibit:
            continue

        related_nodes.append(
            _serialize_graph_node(
                related_exhibit,
                hall=halls_map.get(related_exhibit.hall_id),
                relation=relation,
                asset=assets_map.get(related_exhibit.id),
            )
        )

        source_exhibit = exhibit if relation.source_id == exhibit.id else related_exhibit
        target_exhibit = exhibit if relation.target_id == exhibit.id else related_exhibit
        edges.append(_serialize_graph_edge(source_exhibit, target_exhibit, relation))

    return {
        "exhibit_id": exhibit.id,
        "exhibit_name": exhibit.name,
        "graph_summary": _build_graph_summary(center_asset, related_nodes),
        "center_node": center_node,
        "related_nodes": related_nodes,
        "edges": edges,
        "relation_type_stats": _build_relation_type_stats(related_nodes),
        "timeline_nodes": _build_timeline_nodes(exhibit, center_node, related_nodes),
        "craft_sections": _build_craft_sections(exhibit, related_nodes),
        "creative_groups": _build_creative_groups(exhibit, related_nodes),
        "hall_chain": _build_hall_chain(db, exhibit, center_hall, assets_map, halls_map),
    }


@router.get("/", response_model=list[ExhibitBase])
def read_exhibits(db: Session = Depends(get_db)):
    exhibits = crud.get_all_exhibits(db)
    return [_serialize_exhibit_base(exhibit) for exhibit in exhibits]


@router.post("/creative/poster", response_model=CreativePosterResponse)
def create_creative_poster(request: Request, data: CreativePosterRequest, db: Session = Depends(get_db)):
    try:
        result = generate_creative_poster(db=db, data=data)
        poster_image_url = result.get("poster_image_url")
        fallback_cover_image_url = result.get("fallback_cover_image_url")
        if poster_image_url and poster_image_url.startswith("/media/"):
            result["poster_image_url"] = _build_absolute_url(request, poster_image_url)
        if fallback_cover_image_url and fallback_cover_image_url.startswith("/media/"):
            result["fallback_cover_image_url"] = _build_absolute_url(request, fallback_cover_image_url)
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{exhibit_id}", response_model=ExhibitDetailResponse)
def read_exhibit_detail(exhibit_id: int, db: Session = Depends(get_db)):
    exhibit = crud.get_exhibit_by_id(db, exhibit_id)
    if not exhibit:
        raise HTTPException(status_code=404, detail="展品不存在")

    hall = crud.get_hall_by_id(db, exhibit.hall_id)
    related_exhibits = get_related_exhibit_cards(db, exhibit.id, limit=4)
    asset = (
        db.query(models.ExhibitAsset)
        .filter(models.ExhibitAsset.exhibit_id == exhibit.id)
        .first()
    )

    result = _serialize_exhibit_base(exhibit)

    if not result.get("image_url") and asset and getattr(asset, "cover_image_url", None):
        result["image_url"] = asset.cover_image_url

    result.update(
        {
            "hall": {
                "id": hall.id,
                "name": hall.name,
                "theme": hall.theme,
                "summary": hall.summary,
            }
            if hall
            else None,
            "related_exhibits": related_exhibits,
        }
    )
    return result


@router.get("/{exhibit_id}/assets", response_model=ExhibitAssetResponse)
def read_exhibit_assets(exhibit_id: int, request: Request, db: Session = Depends(get_db)):
    exhibit = crud.get_exhibit_by_id(db, exhibit_id)
    if not exhibit:
        raise HTTPException(status_code=404, detail="展品不存在")

    asset = (
        db.query(models.ExhibitAsset)
        .filter(models.ExhibitAsset.exhibit_id == exhibit.id)
        .first()
    )

    return {
        "exhibit_id": exhibit.id,
        "exhibit_name": exhibit.name,
        **_serialize_asset(asset, request=request, exhibit=exhibit),
    }


@router.get("/{exhibit_id}/graph", response_model=ExhibitGraphResponse)
def read_exhibit_graph(exhibit_id: int, db: Session = Depends(get_db)):
    graph_payload = _build_exhibit_graph_payload(db, exhibit_id, limit=6)
    if not graph_payload:
        raise HTTPException(status_code=404, detail="展品不存在")
    return graph_payload


@router.get("/{exhibit_id}/related", response_model=list[RelatedExhibitCard])
def read_related_exhibits(exhibit_id: int, db: Session = Depends(get_db)):
    exhibit = crud.get_exhibit_by_id(db, exhibit_id)
    if not exhibit:
        raise HTTPException(status_code=404, detail="展品不存在")
    return get_related_exhibit_cards(db, exhibit_id, limit=6)


@router.post("/{exhibit_id}/explain", response_model=ExhibitExplainResponse)
def explain_exhibit(exhibit_id: int, data: ExplainRequest, db: Session = Depends(get_db)):
    exhibit = crud.get_exhibit_by_id(db, exhibit_id)
    if not exhibit:
        raise HTTPException(status_code=404, detail="展品不存在")

    explanation_result = build_exhibit_explanation(
        db=db,
        exhibit_id=exhibit_id,
        mode=data.mode,
        current_context_exhibit_id=data.current_context_exhibit_id,
    )

    related_exhibits = get_related_exhibit_cards(db, exhibit_id, limit=4)

    return {
        "exhibit_id": exhibit.id,
        "exhibit_name": exhibit.name,
        "mode": explanation_result["mode"],
        "intro": explanation_result.get("intro", ""),
        "first_impression": explanation_result.get("first_impression", ""),
        "core_watch_points": explanation_result.get("core_watch_points", []),
        "historical_role": explanation_result.get("historical_role", ""),
        "craft_value": explanation_result.get("craft_value", ""),
        "relation_to_route": explanation_result.get("relation_to_route", ""),
        "compare_hint": explanation_result.get("compare_hint", ""),
        "one_sentence_takeaway": explanation_result.get("one_sentence_takeaway", ""),
        "explanation": explanation_result.get("explanation", ""),
        "why_now": explanation_result.get("why_now", ""),
        "relation_hint": explanation_result.get("relation_hint"),
        "source": explanation_result.get("source", "template"),
        "related_exhibits": related_exhibits,
    }
