from typing import Any

from fastapi import HTTPException, status

from app.repositories.research_repository import research_repository
from app.schemas.research import ResearchItemType


class ResearchService:
    def list_items(self, item_type: ResearchItemType, filters: dict[str, Any]) -> list[dict[str, Any]]:
        return research_repository.list_items(item_type, filters)

    def get_detail(self, item_type: ResearchItemType, item_id: str) -> dict[str, Any]:
        item = research_repository.get_item(item_type, item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research item not found")
        return item

    def toggle_favorite(self, item_type: ResearchItemType, item_id: str) -> bool:
        return self._toggle(item_type, item_id, "favorited")

    def toggle_subscription(self, item_type: ResearchItemType, item_id: str) -> bool:
        return self._toggle(item_type, item_id, "subscribed")

    def toggle_compare(self, item_type: ResearchItemType, item_id: str) -> bool:
        return self._toggle(item_type, item_id, "compared")

    def toggle_read(self, item_type: ResearchItemType, item_id: str) -> bool:
        return self._toggle(item_type, item_id, "read")

    def toggle_reading_list(self, item_type: ResearchItemType, item_id: str) -> bool:
        return self._toggle(item_type, item_id, "in_reading_list")

    def compared_items(self) -> list[dict[str, Any]]:
        return research_repository.compared_items()

    def _toggle(self, item_type: ResearchItemType, item_id: str, field: str) -> bool:
        try:
            return research_repository.toggle_flag(item_type, item_id, field)
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research item not found") from None


research_service = ResearchService()
