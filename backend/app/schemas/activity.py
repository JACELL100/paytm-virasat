from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from app.schemas.common import ORMBase

ActivityKind = Literal["login", "upi_payment", "app_open", "other"]


class ActivityIn(ORMBase):
    kind: ActivityKind
    source: str = "app"
    meta: Optional[dict] = Field(default=None)


class ActivityOut(ORMBase):
    id: str
    user_id: str
    kind: str
    occurred_at: str
    source: str
