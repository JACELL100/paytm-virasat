"""Coverage-gap detection: is the owner's term-life cover adequate relative
to income? (Feeds the `coverage_gap` GapCard in /insights, section 8.5.)
"""
from __future__ import annotations

from typing import Any, Optional

RECOMMENDED_MULTIPLE = 10  # 10x annual income, per section 8.5


def compute_coverage_gap(
    *, assets: list[dict[str, Any]], annual_income: Optional[float]
) -> Optional[dict[str, Any]]:
    if not annual_income or annual_income <= 0:
        return None

    term_cover = sum((a.get("value_estimate") or 0) for a in assets if a.get("type") == "term_life")
    target = RECOMMENDED_MULTIPLE * annual_income

    if term_cover >= target:
        return None

    shortfall = target - term_cover
    return {
        "kind": "coverage_gap",
        "asset_id": None,
        "title": "Your family may be under-protected",
        "detail": (
            f"Recommended term cover is about {RECOMMENDED_MULTIPLE}x annual income "
            f"(₹{target:,.0f}). Current term cover is ₹{term_cover:,.0f}, "
            f"a shortfall of ₹{shortfall:,.0f}."
        ),
        "severity": "high" if term_cover == 0 else "medium",
    }
