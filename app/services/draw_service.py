"""Business logic for drawing lotto numbers with optional historical exclusions."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from itertools import combinations
from threading import Lock
from typing import Iterable

from sqlalchemy.orm import Session

from app.errors import AppError, ValidationError
from app.repositories.lotto_result_repository import LottoResultRepository


NumberTuple5 = tuple[int, int, int, int, int]
NumberTuple6 = tuple[int, int, int, int, int, int]


class ExcludeMode(str, Enum):
    NONE = "NONE"
    FIRST = "FIRST"
    SECOND = "SECOND"
    THIRD = "THIRD"
    ALL = "ALL"


@dataclass(frozen=True)
class HistoricalExclusionSets:
    first_place: set[NumberTuple6]
    second_place: set[NumberTuple6]
    third_place: set[NumberTuple5]


class _HistoricalCache:
    def __init__(self) -> None:
        self._lock = Lock()
        self._loaded = False
        self._sets: HistoricalExclusionSets | None = None

    @staticmethod
    def _normalize(numbers: Iterable[int]) -> tuple[int, ...]:
        return tuple(sorted(int(n) for n in numbers))

    def ensure_loaded(self, session: Session) -> HistoricalExclusionSets:
        if self._loaded and self._sets is not None:
            return self._sets

        with self._lock:
            if self._loaded and self._sets is not None:
                return self._sets

            repo = LottoResultRepository()
            draws = repo.list_all(session)

            first_place: set[NumberTuple6] = set()
            second_place: set[NumberTuple6] = set()
            third_place: set[NumberTuple5] = set()

            for draw in draws:
                main6 = self._normalize(
                    (
                        int(draw.number1),
                        int(draw.number2),
                        int(draw.number3),
                        int(draw.number4),
                        int(draw.number5),
                        int(draw.number6),
                    )
                )
                bonus = int(draw.bonus_number)

                first_place.add(
                    (
                        int(main6[0]),
                        int(main6[1]),
                        int(main6[2]),
                        int(main6[3]),
                        int(main6[4]),
                        int(main6[5]),
                    )
                )

                for comb5 in combinations(main6, 5):
                    third_place.add(
                        (
                            int(comb5[0]),
                            int(comb5[1]),
                            int(comb5[2]),
                            int(comb5[3]),
                            int(comb5[4]),
                        )
                    )

                    second6 = self._normalize((*comb5, bonus))
                    second_place.add(
                        (
                            int(second6[0]),
                            int(second6[1]),
                            int(second6[2]),
                            int(second6[3]),
                            int(second6[4]),
                            int(second6[5]),
                        )
                    )

            self._sets = HistoricalExclusionSets(
                first_place=first_place,
                second_place=second_place,
                third_place=third_place,
            )
            self._loaded = True
            return self._sets


_CACHE = _HistoricalCache()


class DrawService:
    """Draw random lotto numbers with optional exclusions."""

    def __init__(self, max_retries: int = 50_000) -> None:
        self._max_retries = max_retries

    @staticmethod
    def _normalize6(numbers: Iterable[int]) -> NumberTuple6:
        t = tuple(sorted(int(n) for n in numbers))
        return (int(t[0]), int(t[1]), int(t[2]), int(t[3]), int(t[4]), int(t[5]))

    @staticmethod
    def _sub5(numbers6: NumberTuple6) -> Iterable[NumberTuple5]:
        for comb5 in combinations(numbers6, 5):
            yield (
                int(comb5[0]),
                int(comb5[1]),
                int(comb5[2]),
                int(comb5[3]),
                int(comb5[4]),
            )

    def draw(self, session: Session, exclude_mode: str, exclude_numbers: Iterable[int] | None = None) -> list[int]:
        """Draw numbers according to the exclude mode.

        Returns a sorted list of 6 unique integers in [1, 45].
        """

        try:
            mode = ExcludeMode(exclude_mode)
        except ValueError as exc:
            raise ValidationError(
                message="Invalid exclude_mode",
                details={"exclude_mode": ["Must be one of NONE|FIRST|SECOND|THIRD|ALL"]},
            ) from exc

        sets = _CACHE.ensure_loaded(session)

        exclude_set = {int(n) for n in exclude_numbers} if exclude_numbers else set()
        if exclude_set:
            if any(n < 1 or n > 45 for n in exclude_set):
                raise ValidationError(
                    message="Invalid exclude_numbers",
                    details={"exclude_numbers": ["All numbers must be within 1..45"]},
                )
            if len(exclude_set) > 39:
                raise ValidationError(
                    message="Invalid exclude_numbers",
                    details={"exclude_numbers": ["Too many excluded numbers (must be <= 39)"]},
                )

        population = [n for n in range(1, 46) if n not in exclude_set]
        if len(population) < 6:
            raise ValidationError(
                message="Invalid exclude_numbers",
                details={"exclude_numbers": ["Not enough numbers left to draw 6"]},
            )

        for _ in range(self._max_retries):
            candidate = self._normalize6(random.sample(population, 6))

            if mode in (ExcludeMode.FIRST, ExcludeMode.ALL) and candidate in sets.first_place:
                continue

            if mode in (ExcludeMode.SECOND, ExcludeMode.ALL) and candidate in sets.second_place:
                continue

            if mode in (ExcludeMode.THIRD, ExcludeMode.ALL):
                if any(sub5 in sets.third_place for sub5 in self._sub5(candidate)):
                    continue

            return list(candidate)

        raise AppError(
            code="draw_failed",
            message=f"Failed to draw numbers within retry limit ({self._max_retries})",
            status_code=503,
        )
