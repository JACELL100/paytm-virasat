from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from app.core.errors import ApiError
from app.core.logging import get_logger
from app.core.security import CurrentUser, get_current_user
from app.core.tokens import hash_token
from app.db.repos import guardians as guardians_repo
from app.db.repos import nominees as nominees_repo
from app.db.repos import vaults as vaults_repo
from app.schemas.vault import InviteAcceptOut
from app.services.crypto import wallets as wallet_service

logger = get_logger(__name__)
router = APIRouter(tags=["invites"])


@router.post("/invites/{token}/accept", response_model=InviteAcceptOut)
async def accept_invite(token: str, user: CurrentUser = Depends(get_current_user)) -> InviteAcceptOut:
    token_hash = hash_token(token)

    nominee = nominees_repo.get_nominee_by_token_hash(token_hash)
    if nominee:
        return await _accept_nominee(nominee, user)

    guardian = guardians_repo.get_guardian_by_token_hash(token_hash)
    if guardian:
        return await _accept_guardian(guardian, user)

    raise ApiError("invite_not_found", "Not found", "This invite link is invalid or has expired.", 404)


async def _ensure_wallet(user_id: str) -> dict:
    from app.db.repos import profiles as profiles_repo

    profile = profiles_repo.get_profile(user_id) or {}
    if profile.get("wallet_address") and profile.get("wallet_key_enc"):
        return profile
    wallet = wallet_service.create_wallet()
    return profiles_repo.update_profile(user_id, {"wallet_address": wallet.address, "wallet_key_enc": wallet.encrypted_private_key})


async def _accept_nominee(nominee: dict, user: CurrentUser) -> InviteAcceptOut:
    if nominee.get("invite_status") == "accepted" and nominee.get("user_id") not in (None, user.id):
        raise ApiError("invite_already_used", "Conflict", "This invite has already been accepted by someone else.", 409)

    profile = await _ensure_wallet(user.id)
    vault = vaults_repo.get_vault(nominee["vault_id"])

    # Issue the Legacy Key (Shamir nominee share, index 1) at accept time.
    # It was generated once at seal/reseal time and packed alongside the
    # escrow share in `vaults.escrow_share_enc` (see
    # manifest.pack_escrow_column for why); every nominee who accepts before
    # the next reseal receives an identical copy of this same share, which
    # is sufficient because unlocking only ever needs escrow + ANY one
    # nominee's share (section 11).
    legacy_key_share = None
    if vault and vault.get("escrow_share_enc"):
        try:
            from app.services.crypto import manifest as manifest_service

            _escrow_token, nominee_pending_b64 = manifest_service.unpack_escrow_column(vault["escrow_share_enc"])
            legacy_key_share = nominee_pending_b64
            if legacy_key_share is None:
                logger.warning(
                    "legacy_key_not_available_yet",
                    vault_id=nominee["vault_id"],
                    hint="Vault may predate the reseal that packs the nominee share, or the vault hasn't been sealed.",
                )
        except Exception:
            logger.exception("legacy_key_issue_failed", vault_id=nominee["vault_id"])

    from datetime import datetime, timezone

    nominees_repo.update_nominee(
        nominee["id"],
        {
            "user_id": user.id,
            "wallet_address": profile["wallet_address"],
            "invite_status": "accepted",
            "legacy_key_issued_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    await _maybe_create_vault_onchain_safe(nominee["vault_id"])
    return InviteAcceptOut(ok=True, role="nominee", vault_id=nominee["vault_id"], legacy_key_share=legacy_key_share)


async def _accept_guardian(guardian: dict, user: CurrentUser) -> InviteAcceptOut:
    if guardian.get("status") == "accepted" and guardian.get("user_id") not in (None, user.id):
        raise ApiError("invite_already_used", "Conflict", "This invite has already been accepted by someone else.", 409)

    profile = await _ensure_wallet(user.id)
    guardians_repo.update_guardian(
        guardian["id"], {"user_id": user.id, "wallet_address": profile["wallet_address"], "status": "accepted"}
    )
    await _maybe_create_vault_onchain_safe(guardian["vault_id"])
    return InviteAcceptOut(ok=True, role="guardian", vault_id=guardian["vault_id"])


async def _maybe_create_vault_onchain_safe(vault_id: str) -> None:
    """Fires the same best-effort on-chain createVault attempt used at vault
    creation time (see vault.py::maybe_create_vault_onchain) -- accepting an
    invite is exactly the event that can newly satisfy its preconditions."""
    try:
        from app.api.v1.vault import maybe_create_vault_onchain

        await maybe_create_vault_onchain(vault_id)
    except Exception:
        logger.exception("invite_accept_create_vault_retry_failed", vault_id=vault_id)
