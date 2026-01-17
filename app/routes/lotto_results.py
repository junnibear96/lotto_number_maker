"""Lotto results API."""

from __future__ import annotations

from flask import Blueprint

from app.db import get_session
from app.repositories.lotto_result_repository import LottoResultRepository
from app.schemas.lotto_result import LottoResultSchema
from app.utils.responses import ok


lotto_results_bp = Blueprint("lotto_results", __name__)

_repo = LottoResultRepository()
_schema = LottoResultSchema(many=True)


@lotto_results_bp.get("/lotto-results")
def list_results():
    session = get_session()
    results = _repo.list_all(session)
    
    # Transform to friendly format if needed, or rely on schema
    # The simple schema expects fields matching model attributes.
    # Model has number1..6, but schema has 'numbers' list.
    # We need a transformation step or smarter schema. 
    # Let's do a quick transformation here for simplicity.
    
    data = []
    for r in results:
        data.append({
            "draw_no": r.draw_no,
            "numbers": [r.number1, r.number2, r.number3, r.number4, r.number5, r.number6],
            "bonus_number": r.bonus_number
        })

    return ok(_schema.dump(data))
