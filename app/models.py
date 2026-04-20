from sqlalchemy import Column, Integer, String, Text, DECIMAL

from .database import Base


class MuseumHall(Base):
    __tablename__ = "museum_halls"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    code = Column(String(100), nullable=False, unique=True, index=True)
    floor = Column(String(20))
    zone = Column(String(50))
    theme = Column(String(100))
    summary = Column(Text)
    recommended_duration_min = Column(Integer, default=15)
    sort_order = Column(Integer, default=999)


class Exhibit(Base):
    __tablename__ = "exhibits"

    id = Column(Integer, primary_key=True, index=True)
    hall_id = Column(Integer, nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    code = Column(String(100), nullable=False, index=True, unique=True)

    era = Column(String(100))
    dynasty = Column(String(100))
    category = Column(String(100))
    sub_category = Column(String(100))

    material = Column(String(100))
    craft = Column(String(255))
    usage_desc = Column(String(255))

    short_intro = Column(Text)
    deep_intro = Column(Text)
    core_value = Column(Text)

    watch_points = Column(Text)
    story_points = Column(Text)
    detail_points = Column(Text)
    kid_points = Column(Text)
    deep_points = Column(Text)

    historical_value = Column(Text)
    art_value = Column(Text)
    cultural_value = Column(Text)

    shape_desc = Column(String(255))
    pattern_elements = Column(Text)
    symbolism = Column(Text)
    style_tags = Column(Text)
    color_palette = Column(String(255))
    interesting_points = Column(Text)

    related_people = Column(Text)
    related_events = Column(Text)
    related_exhibits_hint = Column(Text)

    creative_keywords = Column(Text)
    poster_copy_seed = Column(Text)
    image_prompt_seed = Column(Text)

    keywords = Column(Text)

    is_featured = Column(Integer, default=0)
    recommended_priority = Column(Integer, default=0)
    recommended_duration_min = Column(Integer, default=5)

    image_url = Column(String(500))


class ExhibitAsset(Base):
    __tablename__ = "exhibit_assets"

    id = Column(Integer, primary_key=True, index=True)
    exhibit_id = Column(Integer, nullable=False, index=True, unique=True)

    cover_image_url = Column(String(500))
    detail_image_url_1 = Column(String(500))
    detail_image_url_2 = Column(String(500))

    image_caption = Column(Text)
    source_name = Column(String(255))
    source_url = Column(String(500))
    copyright_note = Column(String(255))

    audio_script = Column(Text)
    graph_summary = Column(Text)


class HallEdge(Base):
    __tablename__ = "hall_edges"

    id = Column(Integer, primary_key=True, index=True)
    from_hall_id = Column(Integer, nullable=False, index=True)
    to_hall_id = Column(Integer, nullable=False, index=True)
    walk_minutes = Column(Integer, default=0)
    is_direct = Column(Integer, default=0)
    is_recommended = Column(Integer, default=0)
    is_backtrack_heavy = Column(Integer, default=0)
    remark = Column(String(255))


class NarrativeRelation(Base):
    __tablename__ = "narrative_relations"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(20), nullable=False, index=True)
    source_id = Column(Integer, nullable=False, index=True)
    target_type = Column(String(20), nullable=False, index=True)
    target_id = Column(Integer, nullable=False, index=True)
    relation_type = Column(String(50))
    relation_summary = Column(Text)
    strength_score = Column(DECIMAL(3, 2), default=0.0)