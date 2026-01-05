"""Service layer for item business logic."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models.item import Item
from app.repositories.item_repository import ItemRepository


class ItemService:
    """Item use-cases."""

    def __init__(self, repository: ItemRepository | None = None) -> None:
        self._repo = repository or ItemRepository()

    def list_items(self, session: Session) -> Sequence[Item]:
        return self._repo.list_items(session)

    def get_item(self, session: Session, item_id: int) -> Item:
        item = self._repo.get_by_id(session, item_id)
        if item is None:
            raise NotFoundError(message=f"Item {item_id} not found")
        return item

    def create_item(self, session: Session, name: str) -> Item:
        return self._repo.create(session, name=name)
