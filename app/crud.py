from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Session

from . import models


def _safe_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_score_text(*parts: str) -> str:
    return " ".join(_safe_text(part) for part in parts if _safe_text(part))


def _split_keywords(text: str) -> list[str]:
    raw = _safe_text(text)
    if not raw:
        return []

    for sep in ["，", "。", "；", ";", "、", "|", "/", "\n", "\t", "：", ":"]:
        raw = raw.replace(sep, " ")

    return [part.strip().lower() for part in raw.split() if part.strip()]


def _text_match_score(text: str, query_keywords: list[str]) -> float:
    if not text or not query_keywords:
        return 0.0

    lowered = text.lower()
    score = 0.0
    for keyword in query_keywords:
        if not keyword:
            continue
        if keyword in lowered:
            score += 1.0
    return score


def _build_exhibit_search_blob(exhibit: models.Exhibit) -> str:
    return _normalize_score_text(
        getattr(exhibit, "name", ""),
        getattr(exhibit, "era", ""),
        getattr(exhibit, "dynasty", ""),
        getattr(exhibit, "category", ""),
        getattr(exhibit, "sub_category", ""),
        getattr(exhibit, "material", ""),
        getattr(exhibit, "craft", ""),
        getattr(exhibit, "usage_desc", ""),
        getattr(exhibit, "short_intro", ""),
        getattr(exhibit, "deep_intro", ""),
        getattr(exhibit, "core_value", ""),
        getattr(exhibit, "story_points", ""),
        getattr(exhibit, "detail_points", ""),
        getattr(exhibit, "keywords", ""),
        getattr(exhibit, "historical_value", ""),
        getattr(exhibit, "art_value", ""),
        getattr(exhibit, "cultural_value", ""),
        getattr(exhibit, "style_tags", ""),
        getattr(exhibit, "symbolism", ""),
        getattr(exhibit, "creative_keywords", ""),
    )


def _exhibit_interest_score(
    exhibit: models.Exhibit,
    interest: str | None = None,
    visit_goal: str | None = None,
) -> float:
    query_keywords = _split_keywords(_normalize_score_text(interest or "", visit_goal or ""))
    blob = _build_exhibit_search_blob(exhibit)

    score = 0.0
    score += (getattr(exhibit, "is_featured", 0) or 0) * 3.0
    score += (getattr(exhibit, "recommended_priority", 0) or 0) * 0.08
    score += _text_match_score(blob, query_keywords) * 1.6

    if getattr(exhibit, "image_url", None):
        score += 0.2
    if getattr(exhibit, "deep_intro", None):
        score += 0.2
    if getattr(exhibit, "historical_value", None):
        score += 0.25
    if getattr(exhibit, "style_tags", None):
        score += 0.15

    return score


def get_all_halls(db: Session):
    return db.query(models.MuseumHall).order_by(models.MuseumHall.sort_order.asc()).all()


def get_hall_by_id(db: Session, hall_id: int):
    return db.query(models.MuseumHall).filter(models.MuseumHall.id == hall_id).first()


def get_all_exhibits(db: Session):
    return db.query(models.Exhibit).order_by(models.Exhibit.id.asc()).all()


def get_exhibit_by_id(db: Session, exhibit_id: int):
    return db.query(models.Exhibit).filter(models.Exhibit.id == exhibit_id).first()


def get_exhibits_by_hall_id(
    db: Session,
    hall_id: int,
    limit: int | None = None,
):
    query = db.query(models.Exhibit).filter(models.Exhibit.hall_id == hall_id)

    if hasattr(models.Exhibit, "recommended_priority"):
        query = query.order_by(models.Exhibit.recommended_priority.desc(), models.Exhibit.id.asc())
    else:
        query = query.order_by(models.Exhibit.id.asc())

    if limit:
        query = query.limit(limit)

    return query.all()


def get_featured_exhibits_by_hall_ids(
    db: Session,
    hall_ids: list[int],
    interest: str | None = None,
    visit_goal: str | None = None,
    limit: int = 10,
):
    if not hall_ids:
        return []

    exhibits = (
        db.query(models.Exhibit)
        .filter(models.Exhibit.hall_id.in_(hall_ids))
        .all()
    )

    exhibits.sort(
        key=lambda item: (
            -_exhibit_interest_score(item, interest=interest, visit_goal=visit_goal),
            -(getattr(item, "is_featured", 0) or 0),
            -(getattr(item, "recommended_priority", 0) or 0),
            getattr(item, "id", 0),
        )
    )

    return exhibits[:limit]


def get_related_exhibit_candidates(
    db: Session,
    exhibit_id: int,
    hall_id: int | None = None,
    limit: int = 6,
):
    query = db.query(models.Exhibit).filter(models.Exhibit.id != exhibit_id)
    if hall_id is not None:
        query = query.filter(models.Exhibit.hall_id == hall_id)

    if hasattr(models.Exhibit, "recommended_priority"):
        query = query.order_by(models.Exhibit.recommended_priority.desc(), models.Exhibit.id.asc())
    else:
        query = query.order_by(models.Exhibit.id.asc())

    return query.limit(limit).all()
