"""Repository layer for Item persistence."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.item import Item


class ItemRepository:
    """CRUD operations for Item."""

    def list_items(self, session: Session) -> Sequence[Item]:
        stmt = select(Item).order_by(Item.id.asc())
        return list(session.scalars(stmt).all())

    def get_by_id(self, session: Session, item_id: int) -> Item | None:
        return session.get(Item, item_id)

    def create(self, session: Session, name: str) -> Item:
        item = Item(name=name)
        session.add(item)
        session.flush()  # assign PK
        return item
