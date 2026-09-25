from __future__ import annotations

from typing import Optional

from pydantic import EmailStr, Field

from app.schemas.common import ORMBase


class ProfileOut(ORMBase):
    id: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    language: str = "en"
    annual_income: Optional[float] = None
    wallet_address: Optional[str] = None
    roles: list[str] = Field(default_factory=list)


class ProfilePatch(ORMBase):
    full_name: Optional[str] = None
    language: Optional[str] = Field(default=None, pattern="^(en|hi|mr)$")
    phone: Optional[str] = None
    annual_income: Optional[float] = Field(default=None, ge=0)


class ConsentIn(ORMBase):
    purpose: str
    version: str = "1.0"


class ConsentOut(ORMBase):
    id: str
    user_id: str
    purpose: str
    version: str
    granted_at: str
