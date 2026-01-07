"""Item routes (controllers). No business logic here."""

from __future__ import annotations

from flask import Blueprint, request

from app.db import get_optional_session
from app.schemas.item import ItemCreateSchema, ItemSchema
from app.services.item_service import ItemService
from app.utils.responses import ok

items_bp = Blueprint("items", __name__)

_item_schema = ItemSchema()
_items_schema = ItemSchema(many=True)
_create_schema = ItemCreateSchema()
_service = ItemService()


@items_bp.get("/items")
def list_items():
    """List all items."""

    session = get_optional_session()
    items = _service.list_items(session)
    return ok(_items_schema.dump(items))


@items_bp.get("/items/<int:item_id>")
def get_item(item_id: int):
    """Get a single item by id."""

    session = get_optional_session()
    item = _service.get_item(session, item_id)
    return ok(_item_schema.dump(item))


@items_bp.post("/items")
def create_item():
    """Create a new item."""

    payload = request.get_json(silent=True) or {}
    data = _create_schema.load(payload)

    session = get_optional_session()
    item = _service.create_item(session, name=str(data["name"]))

    # Commit occurs in teardown if no exception.
    return ok(_item_schema.dump(item), status_code=201)
