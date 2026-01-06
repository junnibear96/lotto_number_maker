"""Draw routes (controllers). No business logic here."""

from __future__ import annotations

from flask import Blueprint, request

from app.db import get_session
from app.schemas.draw import DrawRequestSchema, DrawResponseSchema
from app.services.draw_service import DrawService
from app.utils.responses import ok


draw_bp = Blueprint("draw", __name__)

_request_schema = DrawRequestSchema()
_response_schema = DrawResponseSchema()
_service = DrawService()


@draw_bp.post("/draw")
def draw_numbers():
    payload = request.get_json(silent=True) or {}
    data = _request_schema.load(payload)

    session = get_session()

    count = int(data.get("count") or 1)
    if count <= 1:
        numbers = _service.draw(
            session,
            exclude_mode=str(data["exclude_mode"]),
            exclude_numbers=data.get("exclude_numbers"),
        )
        return ok(_response_schema.dump({"numbers": numbers, "count": 1}))

    draws = _service.draw_many(
        session,
        exclude_mode=str(data["exclude_mode"]),
        exclude_numbers=data.get("exclude_numbers"),
        count=count,
    )
    first = draws[0] if draws else []
    return ok(_response_schema.dump({"numbers": first, "draws": draws, "count": count}))
