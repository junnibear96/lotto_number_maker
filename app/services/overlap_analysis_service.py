"""Business logic for detecting overlapping lotto prize combinations."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from app.repositories.lotto_result_repository import LottoResultRepository


NumberTuple5 = tuple[int, int, int, int, int]
NumberTuple6 = tuple[int, int, int, int, int, int]


@dataclass(frozen=True)
class OverlapAnalysisResult:
    total_draws: int
    first_prize_overlaps: list[dict[str, object]]
    second_prize_overlaps: list[dict[str, object]]
    third_prize_overlaps: list[dict[str, object]]
    cross_overlaps: list[dict[str, object]]
    overlap_percentages: dict[str, object]


class OverlapAnalysisService:
    """Analyze overlaps between 2nd/3rd prize number combinations across draws."""

    def __init__(self, repository: LottoResultRepository | None = None) -> None:
        self._repo = repository or LottoResultRepository()

    @staticmethod
    def _main_numbers(draw: object) -> tuple[int, int, int, int, int, int]:
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

    def analyze(self, session: object | None) -> OverlapAnalysisResult:
        """Compute overlap sets across all draws.

        Definitions:
        - 2nd prize combinations: for each draw, all 6 variants of (5 main numbers + bonus)
          represented as a normalized 6-number tuple.
        - 3rd prize combinations: for each draw, all 6 variants of (any 5 from 6 main numbers)
          represented as a normalized 5-number tuple.
        - Cross overlap: a 5-number set that appears as a 3rd-prize combination in at least one
          draw AND also appears as a 5-number subset of a 2nd-prize combination from at least one
          *different* draw.
        """

        draws = self._repo.list_all(session)

        # 1st place sets (6 main numbers) and their 5-number subsets.
        first6_to_draws: dict[NumberTuple6, set[int]] = {}
        first_sub5_to_draws: dict[NumberTuple5, set[int]] = {}

        second_to_draws: dict[NumberTuple6, set[int]] = {}
        third_to_draws: dict[NumberTuple5, set[int]] = {}

        # For cross overlap we map 5-number subsets of *any* 2nd-prize combination.
        # This keeps comparison in a single key space (5-number tuples).
        second_sub5_to_draws: dict[NumberTuple5, set[int]] = {}

        for draw in draws:
            draw_no = int(getattr(draw, "draw_no"))
            main = self._normalize(self._main_numbers(draw))
            bonus = int(getattr(draw, "bonus_number"))

            first6 = (
                int(main[0]),
                int(main[1]),
                int(main[2]),
                int(main[3]),
                int(main[4]),
                int(main[5]),
            )
            first6_to_draws.setdefault(first6, set()).add(draw_no)
            for sub5 in combinations(first6, 5):
                first_sub5_to_draws.setdefault(
                    (
                        int(sub5[0]),
                        int(sub5[1]),
                        int(sub5[2]),
                        int(sub5[3]),
                        int(sub5[4]),
                    ),
                    set(),
                ).add(draw_no)

            # 3rd prize: choose 5 out of 6 main numbers.
            for comb5 in combinations(main, 5):
                key5 = tuple(comb5)  # already sorted since main is sorted
                third_to_draws.setdefault(key5, set()).add(draw_no)

            # 2nd prize: choose 5 out of 6 main, then add bonus -> 6-number set.
            for comb5 in combinations(main, 5):
                key6 = self._normalize((*comb5, bonus))
                key6_typed = (  # make mypy happy about tuple length
                    int(key6[0]),
                    int(key6[1]),
                    int(key6[2]),
                    int(key6[3]),
                    int(key6[4]),
                    int(key6[5]),
                )
                second_to_draws.setdefault(key6_typed, set()).add(draw_no)

                # All 5-subsets of this 6-number set contribute to cross overlap space.
                for sub5 in combinations(key6_typed, 5):
                    sub5_typed = (
                        int(sub5[0]),
                        int(sub5[1]),
                        int(sub5[2]),
                        int(sub5[3]),
                        int(sub5[4]),
                    )
                    second_sub5_to_draws.setdefault(sub5_typed, set()).add(draw_no)

        first_overlaps = [
            {
                "numbers": list(combo),
                "draws": sorted(draw_nos),
            }
            for combo, draw_nos in first6_to_draws.items()
            if len(draw_nos) > 1
        ]
        first_overlaps.sort(key=lambda x: (x["numbers"], x["draws"]))

        second_overlaps = [
            {
                "numbers": list(combo),
                "draws": sorted(draw_nos),
            }
            for combo, draw_nos in second_to_draws.items()
            if len(draw_nos) > 1
        ]
        second_overlaps.sort(key=lambda x: (x["numbers"], x["draws"]))

        third_overlaps = [
            {
                "numbers": list(combo),
                "draws": sorted(draw_nos),
            }
            for combo, draw_nos in third_to_draws.items()
            if len(draw_nos) > 1
        ]
        third_overlaps.sort(key=lambda x: (x["numbers"], x["draws"]))

        cross_overlaps: list[dict[str, object]] = []
        for combo5, third_draws in third_to_draws.items():
            second_draws = second_sub5_to_draws.get(combo5)
            if not second_draws:
                continue

            # Keep only if there's at least one pair of different draw numbers.
            if len(second_draws | third_draws) <= 1:
                continue

            cross_overlaps.append(
                {
                    "numbers": list(combo5),
                    "second_draws": sorted(second_draws),
                    "third_draws": sorted(third_draws),
                }
            )

        cross_overlaps.sort(key=lambda x: (x["numbers"], x["second_draws"], x["third_draws"]))

        # --- Percentages requested ---
        # Denominators are UNIQUE combinations across all draws.
        # Each overlap requires at least one match across DIFFERENT draw numbers.
        unique_first = len(first6_to_draws)
        unique_second = len(second_to_draws)
        unique_third = len(third_to_draws)

        second_vs_first_count = 0
        for combo6, second_draws in second_to_draws.items():
            first_draws = first6_to_draws.get(combo6)
            if not first_draws:
                continue
            if len(second_draws | first_draws) <= 1:
                continue
            second_vs_first_count += 1

        third_vs_first_count = 0
        for combo5, third_draws in third_to_draws.items():
            first_draws = first_sub5_to_draws.get(combo5)
            if not first_draws:
                continue
            if len(third_draws | first_draws) <= 1:
                continue
            third_vs_first_count += 1

        third_vs_second_count = 0
        for combo5, third_draws in third_to_draws.items():
            second_draws = second_sub5_to_draws.get(combo5)
            if not second_draws:
                continue
            if len(third_draws | second_draws) <= 1:
                continue
            third_vs_second_count += 1

        def _pct(n: int, d: int) -> float:
            return (n / d * 100.0) if d else 0.0

        first_vs_first_count = len(first_overlaps)
        second_vs_second_count = len(second_overlaps)

        overlap_percentages: dict[str, object] = {
            "denominators": {
                "unique_1st_place_combinations": unique_first,
                "unique_2nd_place_combinations": unique_second,
                "unique_3rd_place_combinations": unique_third,
            },
            "counts": {
                "1st_overlapping_other_1st": first_vs_first_count,
                "2nd_overlapping_other_1st": second_vs_first_count,
                "2nd_overlapping_other_2nd": second_vs_second_count,
                "3rd_overlapping_other_1st": third_vs_first_count,
                "3rd_overlapping_other_2nd": third_vs_second_count,
            },
            "percent": {
                "1st_overlapping_other_1st": _pct(first_vs_first_count, unique_first),
                "2nd_overlapping_other_1st": _pct(second_vs_first_count, unique_second),
                "2nd_overlapping_other_2nd": _pct(second_vs_second_count, unique_second),
                "3rd_overlapping_other_1st": _pct(third_vs_first_count, unique_third),
                "3rd_overlapping_other_2nd": _pct(third_vs_second_count, unique_third),
            },
        }

        return OverlapAnalysisResult(
            total_draws=len(draws),
            first_prize_overlaps=first_overlaps,
            second_prize_overlaps=second_overlaps,
            third_prize_overlaps=third_overlaps,
            cross_overlaps=cross_overlaps,
            overlap_percentages=overlap_percentages,
        )
