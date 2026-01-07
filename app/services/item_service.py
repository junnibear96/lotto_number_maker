"""Service layer for item business logic."""

from __future__ import annotations

from collections.abc import Sequence

from app.errors import NotFoundError
from app.repositories.item_repository import ItemRepository


class ItemService:
    """Item use-cases."""

    def __init__(self, repository: ItemRepository | None = None) -> None:
        self._repo = repository or ItemRepository()

    def list_items(self, session: object | None) -> Sequence[object]:
        return self._repo.list_items(session)

    def get_item(self, session: object | None, item_id: int) -> object:
        item = self._repo.get_by_id(session, item_id)
        if item is None:
            raise NotFoundError(message=f"Item {item_id} not found")
        return item

    def create_item(self, session: object | None, name: str) -> object:
        return self._repo.create(session, name=name)
