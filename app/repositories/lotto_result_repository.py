"""Repository layer for lotto draw persistence."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lotto_result import LottoResult


class LottoResultRepository:
    """Read operations for lotto draw results."""

    def list_all(self, session: Session) -> Sequence[LottoResult]:
        stmt = select(LottoResult).order_by(LottoResult.draw_no.asc())
        return list(session.scalars(stmt).all())
