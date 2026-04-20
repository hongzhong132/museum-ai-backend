import csv
import os
from pathlib import Path

from app import models
from app.database import SessionLocal

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DELETE_MISSING = os.getenv("DELETE_MISSING", "0").strip().lower() in {"1", "true", "yes", "on"}


def to_int(value: str | None, default: int = 0) -> int:
    if value is None or str(value).strip() == "":
        return default
    return int(str(value).strip())


def to_float(value: str | None, default: float = 0.0) -> float:
    if value is None or str(value).strip() == "":
        return default
    return float(str(value).strip())


def to_bool_int(value: str | None, default: int = 0) -> int:
    if value is None:
        return default
    value = str(value).strip().lower()
    return 1 if value in {"1", "true", "yes", "y", "on"} else 0


def safe_str(value: str | None) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None


def load_csv_rows(filename: str) -> tuple[list[dict[str, str]], bool]:
    path = DATA_DIR / filename
    if not path.exists():
        print(f"未找到 {filename}，跳过。")
        return [], False

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), True


def import_halls(db) -> set[str]:
    rows, exists = load_csv_rows("halls.csv")
    if not exists:
        return set()

    created = 0
    updated = 0
    csv_codes: set[str] = set()

    for row in rows:
        code = row["code"].strip()
        csv_codes.add(code)

        existing = db.query(models.MuseumHall).filter(models.MuseumHall.code == code).first()

        payload = {
            "code": code,
            "name": row["name"].strip(),
            "floor": safe_str(row.get("floor")),
            "zone": safe_str(row.get("zone")),
            "theme": safe_str(row.get("theme")),
            "summary": safe_str(row.get("summary")),
            "recommended_duration_min": to_int(row.get("recommended_duration_min"), 15),
            "sort_order": to_int(row.get("sort_order"), 999),
        }

        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            updated += 1
            print(f"更新展区: {existing.name}")
        else:
            db.add(models.MuseumHall(**payload))
            created += 1
            print(f"新增展区: {payload['name']}")

    db.commit()
    print(f"[halls] 新增 {created}，更新 {updated}")
    return csv_codes


def import_exhibits(db) -> set[str]:
    rows, exists = load_csv_rows("exhibits.csv")
    if not exists:
        return set()

    hall_map = {hall.code: hall.id for hall in db.query(models.MuseumHall).all()}

    created = 0
    updated = 0
    skipped = 0
    csv_codes: set[str] = set()

    for row in rows:
        hall_code = row["hall_code"].strip()
        hall_id = hall_map.get(hall_code)
        code = row["code"].strip()

        if hall_id is None:
            print(f"跳过展品 {row.get('name', code)}：找不到 hall_code={hall_code}")
            skipped += 1
            continue

        csv_codes.add(code)
        existing = db.query(models.Exhibit).filter(models.Exhibit.code == code).first()

        payload = {
            "hall_id": hall_id,
            "name": row["name"].strip(),
            "code": code,
            "era": safe_str(row.get("era")),
            "dynasty": safe_str(row.get("dynasty")),
            "category": safe_str(row.get("category")),
            "sub_category": safe_str(row.get("sub_category")),
            "material": safe_str(row.get("material")),
            "craft": safe_str(row.get("craft")),
            "usage_desc": safe_str(row.get("usage_desc")),
            "short_intro": safe_str(row.get("short_intro")),
            "deep_intro": safe_str(row.get("deep_intro")),
            "core_value": safe_str(row.get("core_value")),
            "watch_points": safe_str(row.get("watch_points")),
            "story_points": safe_str(row.get("story_points")),
            "detail_points": safe_str(row.get("detail_points")),
            "kid_points": safe_str(row.get("kid_points")),
            "deep_points": safe_str(row.get("deep_points")),
            "historical_value": safe_str(row.get("historical_value")),
            "art_value": safe_str(row.get("art_value")),
            "cultural_value": safe_str(row.get("cultural_value")),
            "shape_desc": safe_str(row.get("shape_desc")),
            "pattern_elements": safe_str(row.get("pattern_elements")),
            "symbolism": safe_str(row.get("symbolism")),
            "style_tags": safe_str(row.get("style_tags")),
            "color_palette": safe_str(row.get("color_palette")),
            "interesting_points": safe_str(row.get("interesting_points")),
            "related_people": safe_str(row.get("related_people")),
            "related_events": safe_str(row.get("related_events")),
            "related_exhibits_hint": safe_str(row.get("related_exhibits_hint")),
            "creative_keywords": safe_str(row.get("creative_keywords")),
            "poster_copy_seed": safe_str(row.get("poster_copy_seed")),
            "image_prompt_seed": safe_str(row.get("image_prompt_seed")),
            "keywords": safe_str(row.get("keywords")),
            "is_featured": to_bool_int(row.get("is_featured"), 0),
            "recommended_priority": to_int(row.get("recommended_priority"), 0),
            "recommended_duration_min": to_int(row.get("recommended_duration_min"), 5),
            "image_url": safe_str(row.get("image_url")),
        }

        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            updated += 1
            print(f"更新展品: {existing.name}")
        else:
            db.add(models.Exhibit(**payload))
            created += 1
            print(f"新增展品: {payload['name']}")

    db.commit()
    print(f"[exhibits] 新增 {created}，更新 {updated}，跳过 {skipped}")
    return csv_codes


def import_exhibit_assets(db) -> set[str] | None:
    rows, exists = load_csv_rows("exhibit_assets.csv")
    if not exists:
        return None

    exhibit_map = {
        exhibit.code: exhibit for exhibit in db.query(models.Exhibit).all()
    }

    created = 0
    updated = 0
    skipped = 0
    csv_codes: set[str] = set()

    for row in rows:
        exhibit_code = safe_str(row.get("exhibit_code"))
        if not exhibit_code:
            skipped += 1
            print("跳过 exhibit_asset：缺少 exhibit_code")
            continue

        exhibit = exhibit_map.get(exhibit_code)
        if not exhibit:
            skipped += 1
            print(f"跳过 exhibit_asset：找不到 exhibit_code={exhibit_code}")
            continue

        csv_codes.add(exhibit_code)
        existing = (
            db.query(models.ExhibitAsset)
            .filter(models.ExhibitAsset.exhibit_id == exhibit.id)
            .first()
        )

        payload = {
            "exhibit_id": exhibit.id,
            "cover_image_url": safe_str(row.get("cover_image_url")),
            "detail_image_url_1": safe_str(row.get("detail_image_url_1")),
            "detail_image_url_2": safe_str(row.get("detail_image_url_2")),
            "image_caption": safe_str(row.get("image_caption")),
            "source_name": safe_str(row.get("source_name")),
            "source_url": safe_str(row.get("source_url")),
            "copyright_note": safe_str(row.get("copyright_note")),
            "audio_script": safe_str(row.get("audio_script")),
            "graph_summary": safe_str(row.get("graph_summary")),
        }

        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            updated += 1
            print(f"更新展品资产: {exhibit.name}")
        else:
            db.add(models.ExhibitAsset(**payload))
            created += 1
            print(f"新增展品资产: {exhibit.name}")

        # 顺手把主图回填到 exhibits.image_url，兼容你现有前端
        if payload["cover_image_url"] and not safe_str(exhibit.image_url):
            exhibit.image_url = payload["cover_image_url"]

    db.commit()
    print(f"[exhibit_assets] 新增 {created}，更新 {updated}，跳过 {skipped}")
    return csv_codes


def import_hall_edges(db) -> set[tuple[str, str]] | None:
    rows, exists = load_csv_rows("hall_edges.csv")
    if not exists:
        return None

    hall_map = {hall.code: hall.id for hall in db.query(models.MuseumHall).all()}

    created = 0
    updated = 0
    skipped = 0
    csv_keys: set[tuple[str, str]] = set()

    for row in rows:
        from_code = row["from_hall_code"].strip()
        to_code = row["to_hall_code"].strip()

        from_hall_id = hall_map.get(from_code)
        to_hall_id = hall_map.get(to_code)

        if from_hall_id is None or to_hall_id is None:
            print(f"跳过 hall_edge：找不到展区 code {from_code} -> {to_code}")
            skipped += 1
            continue

        csv_keys.add((from_code, to_code))

        existing = (
            db.query(models.HallEdge)
            .filter(
                models.HallEdge.from_hall_id == from_hall_id,
                models.HallEdge.to_hall_id == to_hall_id,
            )
            .first()
        )

        payload = {
            "from_hall_id": from_hall_id,
            "to_hall_id": to_hall_id,
            "walk_minutes": to_int(row.get("walk_minutes"), 0),
            "is_direct": to_bool_int(row.get("is_direct"), 0),
            "is_recommended": to_bool_int(row.get("is_recommended"), 0),
            "is_backtrack_heavy": to_bool_int(row.get("is_backtrack_heavy"), 0),
            "remark": safe_str(row.get("remark")),
        }

        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            updated += 1
            print(f"更新展区连接: {from_code} -> {to_code}")
        else:
            db.add(models.HallEdge(**payload))
            created += 1
            print(f"新增展区连接: {from_code} -> {to_code}")

    db.commit()
    print(f"[hall_edges] 新增 {created}，更新 {updated}，跳过 {skipped}")
    return csv_keys


def import_narrative_relations(db) -> set[tuple[str, str, str, str]] | None:
    rows, exists = load_csv_rows("narrative_relations.csv")
    if not exists:
        return None

    hall_map = {hall.code: hall.id for hall in db.query(models.MuseumHall).all()}
    exhibit_map = {exhibit.code: exhibit.id for exhibit in db.query(models.Exhibit).all()}

    def resolve_id(item_type: str, item_code: str):
        if item_type == "hall":
            return hall_map.get(item_code)
        if item_type == "exhibit":
            return exhibit_map.get(item_code)
        return None

    created = 0
    updated = 0
    skipped = 0
    csv_keys: set[tuple[str, str, str, str]] = set()

    for row in rows:
        source_type = row["source_type"].strip()
        source_code = row["source_code"].strip()
        target_type = row["target_type"].strip()
        target_code = row["target_code"].strip()

        source_id = resolve_id(source_type, source_code)
        target_id = resolve_id(target_type, target_code)

        if source_id is None or target_id is None:
            print(f"跳过 narrative_relation：无法解析 {source_type}:{source_code} -> {target_type}:{target_code}")
            skipped += 1
            continue

        csv_keys.add((source_type, source_code, target_type, target_code))

        existing = (
            db.query(models.NarrativeRelation)
            .filter(
                models.NarrativeRelation.source_type == source_type,
                models.NarrativeRelation.source_id == source_id,
                models.NarrativeRelation.target_type == target_type,
                models.NarrativeRelation.target_id == target_id,
            )
            .first()
        )

        payload = {
            "source_type": source_type,
            "source_id": source_id,
            "target_type": target_type,
            "target_id": target_id,
            "relation_type": safe_str(row.get("relation_type")),
            "relation_summary": safe_str(row.get("relation_summary")),
            "strength_score": to_float(row.get("strength_score"), 0.0),
        }

        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            updated += 1
            print(f"更新叙事关系: {source_type}:{source_code} -> {target_type}:{target_code}")
        else:
            db.add(models.NarrativeRelation(**payload))
            created += 1
            print(f"新增叙事关系: {source_type}:{source_code} -> {target_type}:{target_code}")

    db.commit()
    print(f"[narrative_relations] 新增 {created}，更新 {updated}，跳过 {skipped}")
    return csv_keys


def cleanup_missing_exhibit_assets(db, csv_asset_codes: set[str] | None):
    if not DELETE_MISSING or csv_asset_codes is None:
        return

    exhibit_map = {exhibit.id: exhibit.code for exhibit in db.query(models.Exhibit).all()}
    deleted = 0

    for asset in db.query(models.ExhibitAsset).all():
        exhibit_code = exhibit_map.get(asset.exhibit_id)
        if exhibit_code is None or exhibit_code not in csv_asset_codes:
            print(f"删除旧展品资产: {exhibit_code}")
            db.delete(asset)
            deleted += 1

    db.commit()
    print(f"[cleanup exhibit_assets] 删除 {deleted}")


def cleanup_missing_hall_edges(db, csv_edge_keys: set[tuple[str, str]] | None):
    if not DELETE_MISSING or csv_edge_keys is None:
        return

    hall_map = {hall.id: hall.code for hall in db.query(models.MuseumHall).all()}
    deleted = 0

    for edge in db.query(models.HallEdge).all():
        from_code = hall_map.get(edge.from_hall_id)
        to_code = hall_map.get(edge.to_hall_id)
        key = (from_code, to_code)

        if from_code is None or to_code is None or key not in csv_edge_keys:
            print(f"删除旧展区连接: {from_code} -> {to_code}")
            db.delete(edge)
            deleted += 1

    db.commit()
    print(f"[cleanup hall_edges] 删除 {deleted}")


def cleanup_missing_narrative_relations(db, csv_relation_keys: set[tuple[str, str, str, str]] | None):
    if not DELETE_MISSING or csv_relation_keys is None:
        return

    hall_map = {hall.id: hall.code for hall in db.query(models.MuseumHall).all()}
    exhibit_map = {exhibit.id: exhibit.code for exhibit in db.query(models.Exhibit).all()}
    deleted = 0

    for rel in db.query(models.NarrativeRelation).all():
        if rel.source_type == "hall":
            source_code = hall_map.get(rel.source_id)
        elif rel.source_type == "exhibit":
            source_code = exhibit_map.get(rel.source_id)
        else:
            source_code = None

        if rel.target_type == "hall":
            target_code = hall_map.get(rel.target_id)
        elif rel.target_type == "exhibit":
            target_code = exhibit_map.get(rel.target_id)
        else:
            target_code = None

        key = (rel.source_type, source_code, rel.target_type, target_code)

        if source_code is None or target_code is None or key not in csv_relation_keys:
            print(f"删除旧叙事关系: {rel.source_type}:{source_code} -> {rel.target_type}:{target_code}")
            db.delete(rel)
            deleted += 1

    db.commit()
    print(f"[cleanup narrative_relations] 删除 {deleted}")


def cleanup_missing_exhibits(db, csv_exhibit_codes: set[str]):
    if not DELETE_MISSING:
        return

    deleted = 0
    for exhibit in db.query(models.Exhibit).all():
        if exhibit.code not in csv_exhibit_codes:
            print(f"删除旧展品: {exhibit.name} ({exhibit.code})")
            db.delete(exhibit)
            deleted += 1

    db.commit()
    print(f"[cleanup exhibits] 删除 {deleted}")


def cleanup_missing_halls(db, csv_hall_codes: set[str]):
    if not DELETE_MISSING:
        return

    deleted = 0
    for hall in db.query(models.MuseumHall).all():
        if hall.code not in csv_hall_codes:
            print(f"删除旧展区: {hall.name} ({hall.code})")
            db.delete(hall)
            deleted += 1

    db.commit()
    print(f"[cleanup halls] 删除 {deleted}")


def main():
    db = SessionLocal()
    try:
        csv_hall_codes = import_halls(db)
        csv_exhibit_codes = import_exhibits(db)
        csv_asset_codes = import_exhibit_assets(db)
        csv_edge_keys = import_hall_edges(db)
        csv_relation_keys = import_narrative_relations(db)

        cleanup_missing_narrative_relations(db, csv_relation_keys)
        cleanup_missing_hall_edges(db, csv_edge_keys)
        cleanup_missing_exhibit_assets(db, csv_asset_codes)
        cleanup_missing_exhibits(db, csv_exhibit_codes)
        cleanup_missing_halls(db, csv_hall_codes)

        print("数据导入完成。")
        if DELETE_MISSING:
            print("本次已启用 DELETE_MISSING，会把数据库清理到与当前 CSV 基本一致。")
        else:
            print("本次未启用 DELETE_MISSING，只会新增和更新，不会删除旧数据。")
    finally:
        db.close()


if __name__ == "__main__":
    main()