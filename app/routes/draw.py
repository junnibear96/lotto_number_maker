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
    numbers = _service.draw(
        session,
        exclude_mode=str(data["exclude_mode"]),
        exclude_numbers=data.get("exclude_numbers"),
    )

    return ok(_response_schema.dump({"numbers": numbers}))
