"""Repository layer for Item persistence."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.db import get_db_backend, get_mongo_db

try:  # SQL backend optional when using Mongo
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.models.item import Item
except Exception:  # pragma: no cover
    Session = object  # type: ignore[assignment]
    Item = object  # type: ignore[assignment]


@dataclass(frozen=True)
class ItemRecord:
    id: int
    name: str


class ItemRepository:
    """CRUD operations for Item."""

    def _next_id(self) -> int:
        db = get_mongo_db()
        from pymongo import ReturnDocument
        doc = db["counters"].find_one_and_update(
            {"_id": "items"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        # pymongo returns a dict with updated fields
        return int((doc or {}).get("seq") or 1)

    def list_items(self, session: object | None = None) -> Sequence[object]:
        backend = get_db_backend()
        if backend == "mongo":
            db = get_mongo_db()
            cur = db["items"].find({}, {"_id": 0}).sort("id", 1)
            return [ItemRecord(id=int(d.get("id")), name=str(d.get("name"))) for d in cur]

        if session is None:
            raise RuntimeError("SQLAlchemy session required for sql backend")
        stmt = select(Item).order_by(Item.id.asc())
        return list(session.scalars(stmt).all())

    def get_by_id(self, session: object | None, item_id: int) -> object | None:
        backend = get_db_backend()
        if backend == "mongo":
            db = get_mongo_db()
            d = db["items"].find_one({"id": int(item_id)}, {"_id": 0})
            if not d:
                return None
            return ItemRecord(id=int(d.get("id")), name=str(d.get("name")))

        if session is None:
            raise RuntimeError("SQLAlchemy session required for sql backend")
        return session.get(Item, item_id)

    def create(self, session: object | None, name: str) -> object:
        backend = get_db_backend()
        if backend == "mongo":
            db = get_mongo_db()
            new_id = self._next_id()
            doc = {"id": int(new_id), "name": str(name)}
            db["items"].insert_one(doc)
            return ItemRecord(id=int(new_id), name=str(name))

        if session is None:
            raise RuntimeError("SQLAlchemy session required for sql backend")
        item = Item(name=name)
        session.add(item)
        session.flush()  # assign PK
        return item
