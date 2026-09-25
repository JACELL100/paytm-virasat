from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    detail: str = ""
    code: str


class Page(ORMBase, Generic[T]):
    items: list[T]
    total: int


class TxAck(ORMBase):
    """Returned by endpoints that queue a relayed on-chain transaction."""

    status: str = "queued"
    tx_hash: Optional[str] = None
    idempotency_key: Optional[str] = None
    chain_tx_id: Optional[str] = None


class OkResponse(ORMBase):
    ok: bool = True
    detail: Optional[str] = None
