from __future__ import annotations

from typing import Optional

from pydantic import Field

from app.schemas.common import ORMBase


class ClaimLedgerEventOut(ORMBase):
    status: int
    doc_hash: Optional[str] = None
    at: int
    tx_hash: Optional[str] = None


class VerifyOut(ORMBase):
    token_id: int
    valid: bool
    locked: bool = True
    vault_id: int
    share_bps: int
    released_at: Optional[int] = None
    claim_events: list[ClaimLedgerEventOut] = Field(default_factory=list)
    explorer_url: Optional[str] = None
