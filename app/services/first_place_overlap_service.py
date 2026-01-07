"""Business logic for matching 2nd/3rd prize sets against other draws' 1st-place sets."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from app.repositories.lotto_result_repository import LottoResultRepository


NumberTuple5 = tuple[int, int, int, int, int]
NumberTuple6 = tuple[int, int, int, int, int, int]


@dataclass(frozen=True)
class FirstPlaceOverlap:
    source_draw: int
    target_draw: int
    overlap_type: str  # "SECOND" | "THIRD"
    matching_numbers: list[int]


@dataclass(frozen=True)
class FirstPlaceOverlapResult:
    total_draws: int
    overlaps: list[FirstPlaceOverlap]


class FirstPlaceOverlapService:
    """Detect overlaps where generated sets match other draws' 1st-place numbers.

    Note on schema mapping:
    - In this codebase, the wide table is `lotto_numbers` with columns `number1..number6` and
      `bonus_number`. These correspond to the 1st-place main numbers and bonus number.
    """

    def __init__(self, repository: LottoResultRepository | None = None) -> None:
        self._repo = repository or LottoResultRepository()

    @staticmethod
    def _main_numbers(draw: object) -> NumberTuple6:
        return (
            int(getattr(draw, "number1")),
            int(getattr(draw, "number2")),
            int(getattr(draw, "number3")),
            int(getattr(draw, "number4")),
            int(getattr(draw, "number5")),
            int(getattr(draw, "number6")),
        )

    @staticmethod
    def _normalize(numbers: Iterable[int]) -> tuple[int, ...]:
        return tuple(sorted(int(n) for n in numbers))

    def analyze(self, session: object | None) -> FirstPlaceOverlapResult:
        """Generate 2nd/3rd prize sets for each draw and match against other draws.

        Matching rules (normalized sorted tuples):
        - SECOND: any 6-number set (5-of-6 main + bonus) matches another draw's full 1st-place 6.
        - THIRD: any 5-number set (5-of-6 main) matches any 5-number subset of another draw's
          1st-place 6.

        Constraint:
        - Never match within the same draw (`source_draw != target_draw`).
        """

        draws = self._repo.list_all(session)

        # 1st-place full 6-number sets.
        first6_to_draws: dict[NumberTuple6, set[int]] = {}
        # 5-number subsets derived from 1st-place sets.
        first5_to_draws: dict[NumberTuple5, set[int]] = {}

        for draw in draws:
            draw_no = int(getattr(draw, "draw_no"))
            first6 = self._normalize(self._main_numbers(draw))
            first6_typed: NumberTuple6 = (
                int(first6[0]),
                int(first6[1]),
                int(first6[2]),
                int(first6[3]),
                int(first6[4]),
                int(first6[5]),
            )
            first6_to_draws.setdefault(first6_typed, set()).add(draw_no)

            for sub5 in combinations(first6_typed, 5):
                sub5_typed: NumberTuple5 = (
                    int(sub5[0]),
                    int(sub5[1]),
                    int(sub5[2]),
                    int(sub5[3]),
                    int(sub5[4]),
                )
                first5_to_draws.setdefault(sub5_typed, set()).add(draw_no)

        overlaps_set: set[tuple[int, int, str, tuple[int, ...]]] = set()
        overlaps: list[FirstPlaceOverlap] = []

        for draw in draws:
            source_draw = int(getattr(draw, "draw_no"))
            main = self._normalize(self._main_numbers(draw))
            bonus = int(getattr(draw, "bonus_number"))

            # SECOND: (5 main + bonus) as 6-number set.
            for comb5 in combinations(main, 5):
                second6 = self._normalize((*comb5, bonus))
                second6_typed: NumberTuple6 = (
                    int(second6[0]),
                    int(second6[1]),
                    int(second6[2]),
                    int(second6[3]),
                    int(second6[4]),
                    int(second6[5]),
                )

                target_draws = first6_to_draws.get(second6_typed)
                if not target_draws:
                    continue

                for target_draw in target_draws:
                    if target_draw == source_draw:
                        continue

                    key = (source_draw, target_draw, "SECOND", second6_typed)
                    if key in overlaps_set:
                        continue
                    overlaps_set.add(key)
                    overlaps.append(
                        FirstPlaceOverlap(
                            source_draw=source_draw,
                            target_draw=target_draw,
                            overlap_type="SECOND",
                            matching_numbers=list(second6_typed),
                        )
                    )

            # THIRD: 5-of-6 main numbers.
            for third5 in combinations(main, 5):
                third5_typed: NumberTuple5 = (
                    int(third5[0]),
                    int(third5[1]),
                    int(third5[2]),
                    int(third5[3]),
                    int(third5[4]),
                )

                target_draws = first5_to_draws.get(third5_typed)
                if not target_draws:
                    continue

                for target_draw in target_draws:
                    if target_draw == source_draw:
                        continue

                    key = (source_draw, target_draw, "THIRD", third5_typed)
                    if key in overlaps_set:
                        continue
                    overlaps_set.add(key)
                    overlaps.append(
                        FirstPlaceOverlap(
                            source_draw=source_draw,
                            target_draw=target_draw,
                            overlap_type="THIRD",
                            matching_numbers=list(third5_typed),
                        )
                    )

        overlaps.sort(
            key=lambda o: (
                o.overlap_type,
                o.source_draw,
                o.target_draw,
                o.matching_numbers,
            )
        )

        return FirstPlaceOverlapResult(total_draws=len(draws), overlaps=overlaps)
