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
    latest_draw_numbers: NumberTuple6 | None = None


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

            latest_draw_numbers: NumberTuple6 | None = None
            if draws:
                last_draw = draws[-1]
                latest_draw_numbers = self._normalize(
                    (
                        int(last_draw.number1),
                        int(last_draw.number2),
                        int(last_draw.number3),
                        int(last_draw.number4),
                        int(last_draw.number5),
                        int(last_draw.number6),
                    )
                )

            self._sets = HistoricalExclusionSets(
                first_place=first_place,
                second_place=second_place,
                third_place=third_place,
                latest_draw_numbers=latest_draw_numbers,
            )
            self._loaded = True
            return self._sets


_CACHE = _HistoricalCache()


class DrawService:
    """Draw random lotto numbers with optional exclusions."""

    def __init__(self, max_retries: int = 50_000) -> None:
        self._max_retries = max_retries

    @staticmethod
    def _has_consecutive_pair(numbers6: NumberTuple6) -> bool:
        for i in range(5):
            if int(numbers6[i + 1]) - int(numbers6[i]) == 1:
                return True
        return False

    @staticmethod
    def _last_digits_unique(numbers6: NumberTuple6) -> bool:
        ds = [int(n) % 10 for n in numbers6]
        return len(set(ds)) == len(ds)

    @staticmethod
    def _bucket_count(numbers6: NumberTuple6, bucket: str) -> int:
        ranges = {
            "1-10": (1, 10),
            "11-20": (11, 20),
            "21-30": (21, 30),
            "31-40": (31, 40),
            "41-45": (41, 45),
        }
        lo, hi = ranges.get(bucket, (1, 10))
        return sum(1 for n in numbers6 if int(n) >= lo and int(n) <= hi)

    def _passes_advanced_options(
        self,
        numbers6: NumberTuple6,
        advanced_options: dict | None,
        latest_draw: NumberTuple6 | None = None,
    ) -> bool:
        opts = advanced_options or {}

        consecutive_mode = str(opts.get("consecutive_mode") or "ALLOW").upper()
        has_consecutive = self._has_consecutive_pair(numbers6)
        if consecutive_mode == "REQUIRE" and not has_consecutive:
            return False
        if consecutive_mode == "FORBID" and has_consecutive:
            return False

        last_digit_mode = str(opts.get("last_digit_mode") or "ALLOW").upper()
        if last_digit_mode == "FORBID" and not self._last_digits_unique(numbers6):
            return False

        rf = opts.get("range_filter") if isinstance(opts.get("range_filter"), dict) else {}
        enabled = bool(rf.get("enabled")) if isinstance(rf, dict) else False
        if enabled:
            bucket = str(rf.get("bucket") or "1-10")
            try:
                mn = int(rf.get("min_count") if rf.get("min_count") is not None else 0)
                mx = int(rf.get("max_count") if rf.get("max_count") is not None else 6)
            except (TypeError, ValueError):
                return False
            if mn > mx:
                return False
            c = self._bucket_count(numbers6, bucket)
            if c < mn or c > mx:
                return False

        max_prev_overlap = opts.get("max_previous_draw_overlap")
        if max_prev_overlap is not None and latest_draw is not None:
            try:
                limit = int(max_prev_overlap)
                # Calculate overlap between candidate (numbers6) and latest_draw
                overlap_count = len(set(numbers6).intersection(set(latest_draw)))
                if overlap_count > limit:
                    return False
            except (ValueError, TypeError):
                pass  # Ignore invalid option

        return True

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

    def draw(
        self,
        session: Session,
        exclude_mode: str,
        exclude_numbers: Iterable[int] | None = None,
        exclude_draws: Iterable[Iterable[int]] | None = None,
        fixed_numbers: Iterable[int] | None = None,
        advanced_options: dict | None = None,
    ) -> list[int]:
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

        fixed_set = {int(n) for n in fixed_numbers} if fixed_numbers else set()
        if fixed_set:
            if any(n < 1 or n > 45 for n in fixed_set):
                raise ValidationError(
                    message="Invalid fixed_numbers",
                    details={"fixed_numbers": ["All numbers must be within 1..45"]},
                )
            if len(fixed_set) > 2:
                raise ValidationError(
                    message="Invalid fixed_numbers",
                    details={"fixed_numbers": ["Too many fixed numbers (must be <= 2)"]},
                )
            if exclude_set.intersection(fixed_set):
                raise ValidationError(
                    message="Invalid fixed_numbers",
                    details={"fixed_numbers": ["Fixed numbers cannot overlap excluded numbers"]},
                )

        remaining_needed = 6 - len(fixed_set)
        population = [n for n in range(1, 46) if n not in exclude_set and n not in fixed_set]
        if remaining_needed < 0:
            raise ValidationError(
                message="Invalid fixed_numbers",
                details={"fixed_numbers": ["Too many fixed numbers"]},
            )
        if len(population) < remaining_needed:
            raise ValidationError(
                message="Invalid exclude_numbers",
                details={"exclude_numbers": ["Not enough numbers left to draw 6 with fixed numbers"]},
            )

        exclude_draws_set: set[NumberTuple6] = set()
        if exclude_draws:
            for d in exclude_draws:
                dd = [int(x) for x in (d or [])]
                if len(dd) != 6 or len(set(dd)) != 6:
                    raise ValidationError(
                        message="Invalid exclude_draws",
                        details={"exclude_draws": ["Each draw must be 6 unique numbers"]},
                    )
                exclude_draws_set.add(self._normalize6(dd))

        for _ in range(self._max_retries):
            picked = random.sample(population, remaining_needed) if remaining_needed else []
            candidate = self._normalize6([*fixed_set, *picked])

            if exclude_draws_set and candidate in exclude_draws_set:
                continue

            if mode in (ExcludeMode.FIRST, ExcludeMode.ALL) and candidate in sets.first_place:
                continue

            if mode in (ExcludeMode.SECOND, ExcludeMode.ALL) and candidate in sets.second_place:
                continue

            if mode in (ExcludeMode.THIRD, ExcludeMode.ALL):
                if any(sub5 in sets.third_place for sub5 in self._sub5(candidate)):
                    continue

            if not self._passes_advanced_options(candidate, advanced_options, latest_draw=sets.latest_draw_numbers):
                continue

            return list(candidate)

        raise AppError(
            code="draw_failed",
            message=f"Failed to draw numbers within retry limit ({self._max_retries})",
            status_code=503,
        )


    def draw_many(
        self,
        session: Session,
        exclude_mode: str,
        exclude_numbers: Iterable[int] | None = None,
        exclude_draws: Iterable[Iterable[int]] | None = None,
        fixed_numbers: Iterable[int] | None = None,
        advanced_options: dict | None = None,
        count: int = 1,
    ) -> list[list[int]]:
        if count < 1:
            raise ValidationError(
                message="Invalid count",
                details={"count": ["Must be >= 1"]},
            )
        if count > 50:
            raise ValidationError(
                message="Invalid count",
                details={"count": ["Must be <= 50"]},
            )

        return [
            self.draw(
                session,
                exclude_mode=exclude_mode,
                exclude_numbers=exclude_numbers,
                exclude_draws=exclude_draws,
                fixed_numbers=fixed_numbers,
                advanced_options=advanced_options,
            )
            for _ in range(int(count))
        ]
