from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from app.schemas.common import ORMBase

ClaimStatus = Literal[
    "not_started",
    "docs_pending",
    "ready_to_file",
    "filed",
    "under_review",
    "query_raised",
    "settled",
    "rejected",
    "escalated",
]


class ClaimCreate(ORMBase):
    asset_id: str
    institution_id: Optional[str] = None


class ClaimUpdate(ORMBase):
    status: Optional[ClaimStatus] = None
    note: Optional[str] = None


class ClaimOut(ORMBase):
    id: str
    vault_id: str
    nominee_id: str
    asset_id: str
    institution_id: Optional[str] = None
    status: ClaimStatus = "not_started"
    priority_score: Optional[float] = None
    checklist: dict = Field(default_factory=dict)
    pack_path: Optional[str] = None
    filed_at: Optional[str] = None
    sla_due_at: Optional[str] = None
    claim_ref: Optional[str] = None


class ClaimPackOut(ORMBase):
    signed_url: str
    expires_in: int = 600


class EscalationIn(ORMBase):
    level: Literal["gro", "irdai_bima_bharosa", "ombudsman", "rbi_cms", "sebi_scores"] = "gro"


class EscalationOut(ORMBase):
    letter_text: str
    pdf_signed_url: Optional[str] = None
