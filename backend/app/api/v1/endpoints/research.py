# Status: mock

from typing import Literal

from fastapi import APIRouter, Path

from app.schemas.research import (
    CompareItem,
    DetailResponse,
    FundItem,
    InnovationItem,
    LabItem,
    NewsItem,
    PaperItem,
    PatentItem,
    ToggleRequest,
    ToggleResponse,
)
from app.services.research_service import research_service

router = APIRouter()


SortKey = Literal["match", "deadline", "updated", "citation", "hot"]


@router.get("/funds", response_model=list[FundItem])
def list_funds(
    query: str = "",
    direction: str = "全部方向",
    level: str | None = None,
    deadline: str = "all",
    sort: SortKey = "match",
) -> list[FundItem]:
    return research_service.list_items("fund", locals())


@router.get("/news", response_model=list[NewsItem])
def list_news(
    query: str = "",
    direction: str = "全部方向",
    source: str | None = None,
    sort: SortKey = "updated",
) -> list[NewsItem]:
    return research_service.list_items("news", locals())


@router.get("/innovations", response_model=list[InnovationItem])
def list_innovations(
    query: str = "",
    direction: str = "全部方向",
    sort: SortKey = "hot",
) -> list[InnovationItem]:
    return research_service.list_items("innovation", locals())


@router.get("/papers", response_model=list[PaperItem])
def list_papers(
    query: str = "",
    direction: str = "全部方向",
    conference: str | None = None,
    sort: SortKey = "citation",
) -> list[PaperItem]:
    return research_service.list_items("paper", locals())


@router.get("/patents", response_model=list[PatentItem])
def list_patents(
    query: str = "",
    direction: str = "全部方向",
    sort: SortKey = "updated",
) -> list[PatentItem]:
    return research_service.list_items("patent", locals())


@router.get("/labs", response_model=list[LabItem])
def list_labs(
    query: str = "",
    direction: str = "全部方向",
    deadline: str = "all",
    sort: SortKey = "deadline",
) -> list[LabItem]:
    return research_service.list_items("lab", locals())


@router.post("/favorites/toggle", response_model=ToggleResponse)
def toggle_favorite(payload: ToggleRequest) -> ToggleResponse:
    favorited = research_service.toggle_favorite(payload.item_type, payload.item_id)
    return ToggleResponse(item_id=payload.item_id, favorited=favorited)


@router.post("/subscriptions/toggle", response_model=ToggleResponse)
def toggle_subscription(payload: ToggleRequest) -> ToggleResponse:
    subscribed = research_service.toggle_subscription(payload.item_type, payload.item_id)
    return ToggleResponse(item_id=payload.item_id, subscribed=subscribed)


@router.post("/compare/toggle", response_model=ToggleResponse)
def toggle_compare(payload: ToggleRequest) -> ToggleResponse:
    compared = research_service.toggle_compare(payload.item_type, payload.item_id)
    return ToggleResponse(item_id=payload.item_id, compared=compared)


@router.post("/read/toggle", response_model=ToggleResponse)
def toggle_read(payload: ToggleRequest) -> ToggleResponse:
    read = research_service.toggle_read(payload.item_type, payload.item_id)
    return ToggleResponse(item_id=payload.item_id, read=read)


@router.post("/reading-list/toggle", response_model=ToggleResponse)
def toggle_reading_list(payload: ToggleRequest) -> ToggleResponse:
    in_reading_list = research_service.toggle_reading_list(payload.item_type, payload.item_id)
    return ToggleResponse(item_id=payload.item_id, in_reading_list=in_reading_list)


@router.get("/compare", response_model=list[CompareItem])
def get_compare_items() -> list[CompareItem]:
    return research_service.compared_items()


@router.get("/items/{item_type}/{item_id}", response_model=DetailResponse)
def get_research_item(
    item_type: Literal["fund", "news", "innovation", "paper", "patent", "lab"],
    item_id: str = Path(min_length=1),
) -> DetailResponse:
    item = research_service.get_detail(item_type, item_id)
    return DetailResponse(item_type=item_type, item=item)
