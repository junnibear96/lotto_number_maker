"""Repository layer for lotto draw persistence."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.db import get_db_backend, get_mongo_db

try:  # SQL backend optional when using Mongo
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.models.lotto_result import LottoResult
except Exception:  # pragma: no cover
    Session = object  # type: ignore[assignment]
    LottoResult = object  # type: ignore[assignment]


@dataclass(frozen=True)
class LottoResultRecord:
    draw_no: int
    number1: int
    number2: int
    number3: int
    number4: int
    number5: int
    number6: int
    bonus_number: int


class LottoResultRepository:
    """Read operations for lotto draw results."""

    def list_all(self, session: object | None = None) -> Sequence[object]:
        backend = get_db_backend()
        if backend == "mongo":
            db = get_mongo_db()
            cur = db["lotto_numbers"].find({}, {"_id": 0}).sort("draw_no", 1)
            out: list[LottoResultRecord] = []
            for doc in cur:
                out.append(
                    LottoResultRecord(
                        draw_no=int(doc.get("draw_no")),
                        number1=int(doc.get("number1")),
                        number2=int(doc.get("number2")),
                        number3=int(doc.get("number3")),
                        number4=int(doc.get("number4")),
                        number5=int(doc.get("number5")),
                        number6=int(doc.get("number6")),
                        bonus_number=int(doc.get("bonus_number")),
                    )
                )
            return out

        # SQL fallback
        if session is None:
            raise RuntimeError("SQLAlchemy session required for sql backend")
        stmt = select(LottoResult).order_by(LottoResult.draw_no.asc())
        return list(session.scalars(stmt).all())
