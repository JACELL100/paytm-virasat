from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from app.schemas.common import ORMBase


class SmsIn(ORMBase):
    text: str


class SuggestionOut(ORMBase):
    id: str
    owner_id: str
    source: Literal["statement", "sms", "paytm_feed"]
    payload: dict
    status: Literal["pending", "accepted", "rejected"] = "pending"
    created_at: Optional[str] = None


class DiscoveryResult(ORMBase):
    suggestions: list[SuggestionOut] = Field(default_factory=list)
    count: int = 0
