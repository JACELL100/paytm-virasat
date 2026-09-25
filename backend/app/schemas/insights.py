from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from app.schemas.common import ORMBase


class LegacyScoreBreakdown(ORMBase):
    nominee_coverage: float = 0
    guardians: float = 0
    documents: float = 0
    protection_adequacy: float = 0
    contact_freshness: float = 0


class GapCard(ORMBase):
    kind: Literal["nominee_missing", "nominee_outdated", "share_mismatch", "minor_no_appointee", "coverage_gap"]
    asset_id: Optional[str] = None
    title: str
    detail: str
    severity: Literal["low", "medium", "high"] = "medium"


class InsightsOut(ORMBase):
    legacy_score: int = Field(ge=0, le=100)
    breakdown: LegacyScoreBreakdown
    nominee_gaps: list[GapCard] = Field(default_factory=list)
    coverage_gap: Optional[GapCard] = None
    explanation: Optional[str] = None
