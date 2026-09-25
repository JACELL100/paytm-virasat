from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from app.schemas.common import ORMBase

AssetType = Literal[
    "term_life",
    "life_endowment",
    "ulip",
    "health",
    "motor",
    "fd",
    "savings",
    "mutual_fund",
    "stocks",
    "ppf",
    "epf",
    "nps",
    "gold",
    "loan",
    "credit_card",
    "other",
]

NomineeStatus = Literal["ok", "missing", "outdated", "unknown"]


class AssetCreate(ORMBase):
    type: AssetType
    institution_id: Optional[str] = None
    label: str
    account_ref_masked: Optional[str] = None
    account_ref_full: Optional[str] = Field(default=None, description="Plaintext; encrypted at rest, never returned.")
    value_estimate: Optional[float] = None
    premium_amount: Optional[float] = None
    frequency: Optional[str] = None
    nominee_status: NomineeStatus = "unknown"
    nominee_names: list[str] = Field(default_factory=list)
    source: str = "manual"
    confidence: Optional[float] = None
    meta: dict = Field(default_factory=dict)


class AssetUpdate(ORMBase):
    type: Optional[AssetType] = None
    institution_id: Optional[str] = None
    label: Optional[str] = None
    account_ref_masked: Optional[str] = None
    account_ref_full: Optional[str] = None
    value_estimate: Optional[float] = None
    premium_amount: Optional[float] = None
    frequency: Optional[str] = None
    nominee_status: Optional[NomineeStatus] = None
    nominee_names: Optional[list[str]] = None
    meta: Optional[dict] = None


class AssetOut(ORMBase):
    id: str
    owner_id: str
    type: AssetType
    institution_id: Optional[str] = None
    label: str
    account_ref_masked: Optional[str] = None
    value_estimate: Optional[float] = None
    premium_amount: Optional[float] = None
    frequency: Optional[str] = None
    nominee_status: NomineeStatus = "unknown"
    nominee_names: list[str] = Field(default_factory=list)
    source: str = "manual"
    confidence: Optional[float] = None
    meta: dict = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AssetAskIn(ORMBase):
    question: str


class AssetAskOut(ORMBase):
    answer: str
    citations: list[str] = Field(default_factory=list)
