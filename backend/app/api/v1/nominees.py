from __future__ import annotations

from pydantic import BaseModel

from fastapi import APIRouter, Depends

from app.core.errors import ApiError
from app.core.logging import get_logger
from app.db.repos import nominees as nominees_repo
from app.db.repos import vaults as vaults_repo
from app.core.security import CurrentUser, get_current_user
from app.schemas.vault import VaultOut

logger = get_logger(__name__)
router = APIRouter(tags=["nominee"])


class UnlockIn(BaseModel):
    legacy_key_share: str  # base64 Shamir share (the nominee's copy of Share 1)


class UnlockOut(BaseModel):
    manifest: dict


@router.get("/nominee/vaults", response_model=list[VaultOut])
async def my_nominee_vaults(user: CurrentUser = Depends(get_current_user)) -> list[VaultOut]:
    rows = nominees_repo.list_vaults_for_nominee_user(user.id)
    out = []
    for r in rows:
        vault = r.get("vaults") or vaults_repo.get_vault(r["vault_id"])
        if vault:
            out.append(VaultOut.model_validate({**vault, "nominees": [], "guardians": [], "timeline": []}))
    return out


@router.post("/nominee/vaults/{vault_id}/unlock", response_model=UnlockOut)
async def unlock_vault(vault_id: str, body: UnlockIn, user: CurrentUser = Depends(get_current_user)) -> UnlockOut:
    """Section 8.2 / 11: checks on-chain state == Released + caller is a
    nominee, combines escrow + the submitted Legacy Key share to rebuild the
    DEK, decrypts the manifest, and verifies the ciphertext hash against the
    on-chain manifestHash."""
    nominee_rows = [r for r in nominees_repo.list_vaults_for_nominee_user(user.id) if r["vault_id"] == vault_id]
    if not nominee_rows:
        raise ApiError("not_a_nominee", "Forbidden", "You are not a nominee of this vault.", 403)

    vault = vaults_repo.get_vault(vault_id)
    if not vault:
        raise ApiError("vault_not_found", "Not found", "Vault not found.", 404)

    # Prefer live on-chain state; fall back to the DB mirror if chain is unavailable.
    onchain_released = None
    try:
        from app.services.chain.contracts import VAULT_STATE_NAMES, read_vault

        if vault.get("chain_vault_id") is not None:
            v = read_vault(int(vault["chain_vault_id"]))
            if v is not None:
                onchain_released = VAULT_STATE_NAMES[v["state"]] == "released"
    except Exception:
        logger.warning("unlock_onchain_check_failed", vault_id=vault_id)

    is_released = onchain_released if onchain_released is not None else (vault.get("state") == "released")
    if not is_released:
        raise ApiError("vault_not_released", "Forbidden", "This vault has not been released yet.", 403)

    if not vault.get("manifest_path") or not vault.get("escrow_share_enc"):
        raise ApiError("manifest_not_available", "Not found", "No sealed manifest is available for this vault.", 404)

    from app.db.client import get_supabase
    from app.services.crypto import manifest as manifest_service

    client = get_supabase()
    if client is None:
        raise ApiError("db_unavailable", "Service unavailable", "Database not configured.", 503)

    try:
        ciphertext = client.storage.from_("sealed-manifests").download(vault["manifest_path"])
    except Exception as exc:
        raise ApiError("manifest_download_failed", "Internal server error", "Could not download the sealed manifest.", 500) from exc

    escrow_token, _pending = manifest_service.unpack_escrow_column(vault["escrow_share_enc"])

    try:
        manifest = manifest_service.unseal_manifest(
            ciphertext=ciphertext,
            escrow_share_enc=escrow_token,
            nominee_share_b64=body.legacy_key_share,
            vault_id=vault_id,
            epoch=vault.get("epoch", 0),
            expected_manifest_hash_hex=vault.get("manifest_hash"),
        )
    except ApiError:
        raise
    except Exception as exc:
        raise ApiError("unlock_failed", "Bad request", f"Could not unlock the manifest with this Legacy Key: {exc}", 400) from exc

    return UnlockOut(manifest=manifest)
