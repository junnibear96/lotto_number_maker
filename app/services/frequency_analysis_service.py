"""Business logic for lotto number frequency analysis (heatmap data)."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.lotto_result import LottoResult


@dataclass(frozen=True)
class FrequencyAnalysisResult:
    total_draws_in_db: int
    draws_used: int
    recent_n: int | None
    percent: float
    counts: dict[int, int]
    min_count: int
    max_count: int
    cold_numbers: list[int]
    hot_numbers: list[int]
    exclude_numbers_for_only_cold: list[int]


class FrequencyAnalysisService:
    """Compute number frequency across all or recent draws."""

    def analyze(self, session: Session, *, recent_n: int | None = None, percent: float = 0.2) -> FrequencyAnalysisResult:
        if recent_n is not None and recent_n <= 0:
            raise ValueError("recent_n must be positive")
        if not (0.0 < float(percent) < 1.0):
            raise ValueError("percent must be between 0 and 1")

        total_draws_in_db = int(
            session.scalar(select(func.count()).select_from(LottoResult)) or 0
        )

        stmt = select(LottoResult)
        if recent_n is not None:
            stmt = stmt.order_by(desc(LottoResult.draw_no)).limit(int(recent_n))
        else:
            stmt = stmt.order_by(LottoResult.draw_no.asc())

        draws = list(session.scalars(stmt).all())

        counts: dict[int, int] = {n: 0 for n in range(1, 46)}
        for d in draws:
            nums = [
                int(d.number1),
                int(d.number2),
                int(d.number3),
                int(d.number4),
                int(d.number5),
                int(d.number6),
            ]
            for n in nums:
                if 1 <= n <= 45:
                    counts[n] += 1

        values = list(counts.values())
        min_count = min(values) if values else 0
        max_count = max(values) if values else 0

        k = max(1, int(ceil(45 * float(percent))))
        ordered = sorted(counts.items(), key=lambda kv: (kv[1], kv[0]))
        cold_numbers = [n for n, _ in ordered[:k]]
        hot_numbers = [n for n, _ in ordered[-k:]][::-1]

        exclude_numbers_for_only_cold = [n for n in range(1, 46) if n not in set(cold_numbers)]

        return FrequencyAnalysisResult(
            total_draws_in_db=total_draws_in_db,
            draws_used=len(draws),
            recent_n=int(recent_n) if recent_n is not None else None,
            percent=float(percent),
            counts=counts,
            min_count=int(min_count),
            max_count=int(max_count),
            cold_numbers=cold_numbers,
            hot_numbers=hot_numbers,
            exclude_numbers_for_only_cold=exclude_numbers_for_only_cold,
        )
