from typing import List

from pydantic import BaseModel, ConfigDict, Field


class MuseumHallBase(BaseModel):
    id: int
    name: str
    code: str
    floor: str | None = None
    zone: str | None = None
    theme: str | None = None
    summary: str | None = None
    recommended_duration_min: int | None = None
    sort_order: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ExhibitBase(BaseModel):
    id: int
    hall_id: int
    name: str
    code: str
    era: str | None = None
    dynasty: str | None = None
    category: str | None = None
    sub_category: str | None = None

    material: str | None = None
    craft: str | None = None
    usage_desc: str | None = None

    short_intro: str | None = None
    deep_intro: str | None = None
    core_value: str | None = None

    watch_points: str | None = None
    story_points: str | None = None
    detail_points: str | None = None
    kid_points: str | None = None
    deep_points: str | None = None

    historical_value: str | None = None
    art_value: str | None = None
    cultural_value: str | None = None

    shape_desc: str | None = None
    pattern_elements: str | None = None
    symbolism: str | None = None
    style_tags: str | None = None
    color_palette: str | None = None
    interesting_points: str | None = None

    related_people: str | None = None
    related_events: str | None = None
    related_exhibits_hint: str | None = None

    creative_keywords: str | None = None
    poster_copy_seed: str | None = None
    image_prompt_seed: str | None = None

    keywords: str | None = None

    is_featured: int | None = None
    recommended_priority: int | None = None
    recommended_duration_min: int | None = None
    image_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RouteGenerateRequest(BaseModel):
    available_minutes: int
    interest: str
    first_visit: bool
    visit_goal: str


class RouteHallItem(BaseModel):
    id: int
    name: str
    recommended_duration_min: int | None = None


class RouteExhibitItem(BaseModel):
    id: int
    name: str
    hall_id: int
    era: str | None = None
    dynasty: str | None = None
    category: str | None = None
    sub_category: str | None = None
    material: str | None = None
    craft: str | None = None
    usage_desc: str | None = None
    symbolism: str | None = None
    style_tags: str | None = None
    short_intro: str | None = None
    image_url: str | None = None


class RouteStopGuideItem(BaseModel):
    hall_id: int
    hall_name: str
    hall_theme: str | None = None
    focus: str
    why_here: str
    key_exhibits: List[str] = Field(default_factory=list)
    transition_to_next: str
    time_budget_min: int | None = None


class RouteGenerateResponse(BaseModel):
    route_title: str
    route_theme: str
    target_fit_reason: str
    order_logic: str
    route_summary: str
    selected_halls: List[RouteHallItem]
    featured_exhibits: List[RouteExhibitItem]
    stop_guides: List[RouteStopGuideItem]
    skip_strategy: str
    route_closing: str
    source: str


class RouteReplanRequest(BaseModel):
    current_hall_id: int
    visited_hall_ids: List[int] = Field(default_factory=list)
    remaining_minutes: int
    updated_goal: str


class RouteReplanResponse(BaseModel):
    route_title: str
    route_theme: str
    target_fit_reason: str
    order_logic: str
    route_summary: str
    selected_halls: List[RouteHallItem]
    featured_exhibits: List[RouteExhibitItem]
    stop_guides: List[RouteStopGuideItem]
    skip_strategy: str
    route_closing: str
    replan_reason: str
    source: str


class RelatedExhibitCard(BaseModel):
    id: int
    name: str
    hall_id: int | None = None
    era: str | None = None
    dynasty: str | None = None
    category: str | None = None
    sub_category: str | None = None
    short_intro: str | None = None
    usage_desc: str | None = None
    symbolism: str | None = None
    style_tags: str | None = None
    image_url: str | None = None
    relation_type: str | None = None
    relation_summary: str | None = None
    strength_score: float | None = None


class ExhibitHallInfo(BaseModel):
    id: int
    name: str
    theme: str | None = None
    summary: str | None = None


class ExhibitAssetResponse(BaseModel):
    exhibit_id: int
    exhibit_name: str
    has_assets: bool = False
    cover_image_url: str | None = None
    detail_image_url_1: str | None = None
    detail_image_url_2: str | None = None
    detail_image_urls: List[str] = Field(default_factory=list)
    image_caption: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    copyright_note: str | None = None
    audio_script: str | None = None
    audio_url: str | None = None
    graph_summary: str | None = None


class ExhibitGraphNode(BaseModel):
    id: int
    name: str
    hall_id: int | None = None
    hall_name: str | None = None
    era: str | None = None
    dynasty: str | None = None
    category: str | None = None
    sub_category: str | None = None
    material: str | None = None
    craft: str | None = None
    usage_desc: str | None = None
    shape_desc: str | None = None
    pattern_elements: str | None = None
    symbolism: str | None = None
    style_tags: str | None = None
    color_palette: str | None = None
    creative_keywords: str | None = None
    core_value: str | None = None
    short_intro: str | None = None
    image_url: str | None = None
    relation_type: str | None = None
    relation_summary: str | None = None
    strength_score: float | None = None
    is_center: bool = False


class ExhibitGraphEdge(BaseModel):
    source_id: int
    source_name: str
    target_id: int
    target_name: str
    relation_type: str | None = None
    relation_summary: str | None = None
    strength_score: float | None = None


class ExhibitGraphRelationStat(BaseModel):
    type: str | None = None
    label: str
    count: int


class ExhibitGraphTimelineItem(BaseModel):
    id: int | None = None
    name: str
    time_label: str | None = None
    subtitle: str | None = None
    summary: str | None = None
    relation_type: str | None = None
    relation_label: str | None = None
    is_center: bool = False


class ExhibitGraphCraftSection(BaseModel):
    key: str
    title: str
    subtitle: str | None = None
    description: str | None = None
    tags: List[str] = Field(default_factory=list)
    related_nodes: List[ExhibitGraphNode] = Field(default_factory=list)


class ExhibitGraphCreativeGroup(BaseModel):
    key: str
    title: str
    description: str | None = None
    values: List[str] = Field(default_factory=list)


class ExhibitHallChainCurrent(BaseModel):
    id: int
    name: str
    code: str | None = None
    floor: str | None = None
    zone: str | None = None
    theme: str | None = None
    summary: str | None = None
    recommended_duration_min: int | None = None


class ExhibitHallChainHall(BaseModel):
    hall_id: int
    name: str
    theme: str | None = None
    summary: str | None = None
    walk_minutes: int | None = None
    relation_type: str | None = None
    relation_label: str | None = None
    relation_summary: str | None = None
    key_exhibits: List[str] = Field(default_factory=list)


class ExhibitHallChain(BaseModel):
    current_hall: ExhibitHallChainCurrent | None = None
    same_hall_exhibits: List[ExhibitGraphNode] = Field(default_factory=list)
    next_halls: List[ExhibitHallChainHall] = Field(default_factory=list)


class ExhibitGraphResponse(BaseModel):
    exhibit_id: int
    exhibit_name: str
    graph_summary: str | None = None
    center_node: ExhibitGraphNode
    related_nodes: List[ExhibitGraphNode] = Field(default_factory=list)
    edges: List[ExhibitGraphEdge] = Field(default_factory=list)
    relation_type_stats: List[ExhibitGraphRelationStat] = Field(default_factory=list)
    timeline_nodes: List[ExhibitGraphTimelineItem] = Field(default_factory=list)
    craft_sections: List[ExhibitGraphCraftSection] = Field(default_factory=list)
    creative_groups: List[ExhibitGraphCreativeGroup] = Field(default_factory=list)
    hall_chain: ExhibitHallChain | None = None


class ExhibitDetailResponse(BaseModel):
    id: int
    hall_id: int
    name: str
    code: str
    era: str | None = None
    dynasty: str | None = None
    category: str | None = None
    sub_category: str | None = None

    material: str | None = None
    craft: str | None = None
    usage_desc: str | None = None

    short_intro: str | None = None
    deep_intro: str | None = None
    core_value: str | None = None

    watch_points: str | None = None
    story_points: str | None = None
    detail_points: str | None = None
    kid_points: str | None = None
    deep_points: str | None = None

    historical_value: str | None = None
    art_value: str | None = None
    cultural_value: str | None = None

    shape_desc: str | None = None
    pattern_elements: str | None = None
    symbolism: str | None = None
    style_tags: str | None = None
    color_palette: str | None = None
    interesting_points: str | None = None

    related_people: str | None = None
    related_events: str | None = None
    related_exhibits_hint: str | None = None

    creative_keywords: str | None = None
    poster_copy_seed: str | None = None
    image_prompt_seed: str | None = None

    keywords: str | None = None

    is_featured: int | None = None
    recommended_priority: int | None = None
    recommended_duration_min: int | None = None
    image_url: str | None = None

    hall: ExhibitHallInfo | None = None
    related_exhibits: List[RelatedExhibitCard] = Field(default_factory=list)


class CreativeSourceExhibit(BaseModel):
    exhibit_id: int | None = None
    exhibit_name: str
    hall_name: str | None = None
    image_url: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    pattern_elements: List[str] = Field(default_factory=list)
    style_tags: List[str] = Field(default_factory=list)
    color_palette: List[str] = Field(default_factory=list)
    symbolism: List[str] = Field(default_factory=list)
    creative_keywords: List[str] = Field(default_factory=list)


class CreativePosterRequest(BaseModel):
    route_title: str | None = None
    route_theme: str | None = None
    route_summary: str | None = None
    exhibit_id: int | None = None
    exhibit_ids: List[int] = Field(default_factory=list)
    visitor_name: str | None = None
    visit_date: str | None = None
    message: str | None = None
    style_mode: str = "楚风雅韵"


class CreativePosterResponse(BaseModel):
    title: str
    subtitle: str
    poster_copy: str
    commemorative_text: str
    image_prompt: str
    style_mode: str
    route_title: str | None = None
    route_theme: str | None = None
    route_summary: str | None = None
    visitor_name: str | None = None
    visit_date: str | None = None
    poster_image_url: str | None = None
    fallback_cover_image_url: str | None = None
    visual_keywords: List[str] = Field(default_factory=list)
    color_palette: List[str] = Field(default_factory=list)
    source: str
    image_source: str = "fallback"
    image_seed: int | None = None
    source_exhibits: List[CreativeSourceExhibit] = Field(default_factory=list)


class ExplainRequest(BaseModel):
    mode: str = "normal"
    current_context_exhibit_id: int | None = None


class ExhibitExplainResponse(BaseModel):
    exhibit_id: int
    exhibit_name: str
    mode: str

    intro: str
    first_impression: str
    core_watch_points: List[str] = Field(default_factory=list)
    historical_role: str
    craft_value: str
    relation_to_route: str
    compare_hint: str
    one_sentence_takeaway: str

    explanation: str
    why_now: str
    relation_hint: str | None = None

    source: str
    related_exhibits: List[RelatedExhibitCard] = Field(default_factory=list)
