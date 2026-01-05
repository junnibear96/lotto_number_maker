"""Analysis routes (controllers). No business logic here."""

from __future__ import annotations

from flask import Blueprint

from app.db import get_session
from app.services.first_place_overlap_service import FirstPlaceOverlapService
from app.services.overlap_analysis_service import OverlapAnalysisService
from app.utils.responses import ok

analysis_bp = Blueprint("analysis", __name__)
_service = OverlapAnalysisService()
_first_place_service = FirstPlaceOverlapService()


@analysis_bp.get("/analysis/overlap")
def get_overlap_analysis():
    session = get_session()
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
    session = get_session()
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
