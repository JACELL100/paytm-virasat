from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from app.schemas.common import ORMBase


class SessionCreateIn(ORMBase):
    language: Literal["en", "hi", "mr"] = "en"


class SessionOut(ORMBase):
    id: str
    vault_id: str
    user_id: str
    language: str


class MessageIn(ORMBase):
    content: str


class ToolCard(ORMBase):
    tool: str
    data: dict


class MessageOut(ORMBase):
    id: str
    session_id: str
    role: Literal["user", "assistant", "tool"]
    content: str
    tool_calls: list[ToolCard] = Field(default_factory=list)
