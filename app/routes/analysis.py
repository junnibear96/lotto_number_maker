"""Analysis routes (controllers). No business logic here."""

from __future__ import annotations

from flask import Blueprint, request

from app.db import get_optional_session
from app.errors import ValidationError
from app.services.frequency_analysis_service import FrequencyAnalysisService
from app.services.first_place_overlap_service import FirstPlaceOverlapService
from app.services.overlap_analysis_service import OverlapAnalysisService
from app.utils.responses import ok

analysis_bp = Blueprint("analysis", __name__)
_service = OverlapAnalysisService()
_first_place_service = FirstPlaceOverlapService()
_frequency_service = FrequencyAnalysisService()


@analysis_bp.get("/analysis/overlap")
def get_overlap_analysis():
    session = get_optional_session()
    result = _service.analyze(session)

    return ok(
        {
            "total_draws": result.total_draws,
            "overlapping_1st_prize_combinations": result.first_prize_overlaps,
            "overlapping_2nd_prize_combinations": result.second_prize_overlaps,
            "overlapping_3rd_prize_combinations": result.third_prize_overlaps,
            "cross_overlaps_2nd_vs_3rd": result.cross_overlaps,
            "overlap_percentages": result.overlap_percentages,
        }
    )


@analysis_bp.get("/analysis/first-place-overlap")
def get_first_place_overlap():
    session = get_optional_session()
    result = _first_place_service.analyze(session)

    return ok(
        {
            "total_draws": result.total_draws,
            "overlaps": [
                {
                    "source_draw": o.source_draw,
                    "target_draw": o.target_draw,
                    "overlap_type": o.overlap_type,
                    "matching_numbers": o.matching_numbers,
                }
                for o in result.overlaps
            ],
        }
    )


@analysis_bp.get("/analysis/frequency")
def get_frequency_analysis():
    """Return number frequency counts for 1..45.

    Query params:
    - n: optional recent N draws (e.g., 10/30/50/100)
    - percent: optional percentile for hot/cold buckets (default 0.2)
    """

    raw_n = (request.args.get("n") or request.args.get("recent") or "").strip()
    raw_percent = (request.args.get("percent") or "").strip()

    recent_n: int | None = None
    if raw_n:
        try:
            recent_n = int(raw_n)
        except ValueError as e:
            raise ValidationError("n must be an integer") from e
        if recent_n <= 0:
            raise ValidationError("n must be positive")

    percent = 0.2
    if raw_percent:
        try:
            percent = float(raw_percent)
        except ValueError as e:
            raise ValidationError("percent must be a float") from e
        if not (0.0 < percent < 1.0):
            raise ValidationError("percent must be between 0 and 1")

    session = get_optional_session()
    result = _frequency_service.analyze(session, recent_n=recent_n, percent=percent)

    return ok(
        {
            "total_draws_in_db": result.total_draws_in_db,
            "draws_used": result.draws_used,
            "recent_n": result.recent_n,
            "percent": result.percent,
            "counts": result.counts,
            "min_count": result.min_count,
            "max_count": result.max_count,
            "cold_numbers": result.cold_numbers,
            "hot_numbers": result.hot_numbers,
            "exclude_numbers_for_only_cold": result.exclude_numbers_for_only_cold,
        }
    )
