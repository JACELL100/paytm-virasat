from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from app.schemas.common import ORMBase

VaultState = Literal["draft", "active", "challenge", "released", "revoked"]


class NomineeIn(ORMBase):
    name: str
    relation: str
    email: str
    phone: Optional[str] = None
    share_bps: int = Field(ge=0, le=10000)


class GuardianIn(ORMBase):
    name: str
    relation: str
    email: str


class VaultCreateIn(ORMBase):
    inactivity_secs: int = Field(gt=0, default=60)
    challenge_secs: int = Field(gt=0, default=60)
    threshold: int = Field(gt=0, default=2)
    nominees: list[NomineeIn] = Field(default_factory=list)
    guardians: list[GuardianIn] = Field(default_factory=list)


class VaultSettingsPatch(ORMBase):
    inactivity_secs: Optional[int] = None
    challenge_secs: Optional[int] = None
    threshold: Optional[int] = None


class NomineeOut(ORMBase):
    id: str
    vault_id: str
    name: str
    relation: str
    email: str
    phone: Optional[str] = None
    share_bps: int
    user_id: Optional[str] = None
    wallet_address: Optional[str] = None
    invite_status: str = "pending"
    legacy_key_issued_at: Optional[str] = None
    credential_token_id: Optional[int] = None


class GuardianOut(ORMBase):
    id: str
    vault_id: str
    name: str
    relation: str
    email: str
    user_id: Optional[str] = None
    wallet_address: Optional[str] = None
    status: str = "pending"
    onchain_added: bool = False


class VaultTimelineEntry(ORMBase):
    event: str
    at: Optional[str] = None
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None


class VaultOut(ORMBase):
    id: str
    owner_id: str
    chain_vault_id: Optional[int] = None
    state: VaultState = "draft"
    inactivity_secs: int
    challenge_secs: int
    threshold: int
    epoch: int = 0
    manifest_hash: Optional[str] = None
    challenge_ends_at: Optional[str] = None
    last_activity_at: Optional[str] = None
    last_heartbeat_onchain_at: Optional[str] = None
    nominees: list[NomineeOut] = Field(default_factory=list)
    guardians: list[GuardianOut] = Field(default_factory=list)
    timeline: list[VaultTimelineEntry] = Field(default_factory=list)


class InviteAcceptOut(ORMBase):
    ok: bool = True
    role: Literal["nominee", "guardian"]
    vault_id: str
    legacy_key_share: Optional[str] = Field(
        default=None, description="Base64 Shamir share 2, shown once to a nominee at accept time."
    )
