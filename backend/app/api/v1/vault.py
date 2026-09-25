from __future__ import annotations

import time
from typing import Any, Optional

from fastapi import APIRouter, Depends, status

from app.core.errors import ApiError
from app.core.logging import get_logger
from app.core.security import CurrentUser, get_current_user
from app.core.tokens import generate_invite_token
from app.db.repos import assets as assets_repo
from app.db.repos import documents as documents_repo
from app.db.repos import guardians as guardians_repo
from app.db.repos import nominees as nominees_repo
from app.db.repos import profiles as profiles_repo
from app.db.repos import vaults as vaults_repo
from app.schemas.common import TxAck
from app.schemas.vault import (
    GuardianIn,
    GuardianOut,
    NomineeIn,
    NomineeOut,
    VaultCreateIn,
    VaultOut,
    VaultSettingsPatch,
)
from app.services.crypto import manifest as manifest_service
from app.services.crypto import wallets as wallet_service
from app.services.notify.email import invite_email_html, send_email

logger = get_logger(__name__)
router = APIRouter(tags=["vault"])


def _ensure_owner_wallet(user_id: str) -> dict:
    profile = profiles_repo.get_profile(user_id) or {}
    if profile.get("wallet_address") and profile.get("wallet_key_enc"):
        return profile
    wallet = wallet_service.create_wallet()
    return profiles_repo.update_profile(
        user_id, {"wallet_address": wallet.address, "wallet_key_enc": wallet.encrypted_private_key}
    )


def _upload_sealed_manifest(vault_id: str, ciphertext: bytes) -> Optional[str]:
    from app.db.client import get_supabase

    client = get_supabase()
    if client is None:
        logger.warning("sealed_manifest_upload_skipped_no_db", vault_id=vault_id)
        return None
    path = f"{vault_id}/manifest.bin"
    try:
        client.storage.from_("sealed-manifests").upload(
            path, ciphertext, {"content-type": "application/octet-stream", "upsert": "true"}
        )
        return path
    except Exception:
        logger.warning("sealed_manifest_upload_failed", vault_id=vault_id)
        return None


def _build_vault_out(vault: dict) -> VaultOut:
    nominees = [NomineeOut.model_validate(n) for n in nominees_repo.list_nominees(vault["id"])]
    guardians = [GuardianOut.model_validate(g) for g in guardians_repo.list_guardians(vault["id"])]
    return VaultOut.model_validate({**vault, "nominees": nominees, "guardians": guardians, "timeline": []})


@router.post("/vault", response_model=VaultOut, status_code=status.HTTP_202_ACCEPTED)
async def create_vault(body: VaultCreateIn, user: CurrentUser = Depends(get_current_user)) -> VaultOut:
    existing = vaults_repo.get_vault_by_owner(user.id)
    if existing:
        raise ApiError("vault_already_exists", "Conflict", "A vault already exists for this owner.", 409)

    profile = _ensure_owner_wallet(user.id)
    assets = assets_repo.list_assets(user.id)
    documents = documents_repo.list_documents(user.id)

    vault_row = vaults_repo.create_vault(
        user.id,
        {
            "state": "draft",
            "inactivity_secs": body.inactivity_secs,
            "challenge_secs": body.challenge_secs,
            "threshold": body.threshold,
            "epoch": 0,
        },
    )
    vault_id = vault_row["id"]

    manifest = manifest_service.build_manifest(
        owner=profile, assets=assets, documents=documents, nominees=[n.model_dump() for n in body.nominees]
    )
    sealed = manifest_service.seal_manifest(manifest, vault_id=vault_id, epoch=0)
    manifest_path = _upload_sealed_manifest(vault_id, sealed.ciphertext)

    vaults_repo.update_vault(
        vault_id,
        {
            "manifest_hash": sealed.manifest_hash_hex,
            "manifest_path": manifest_path,
            "escrow_share_enc": manifest_service.pack_escrow_column(
                escrow_share_enc=sealed.escrow_share_enc, nominee_pending_share_b64=sealed.nominee_share_b64
            ),
            "recovery_share_enc": sealed.recovery_share_enc,
        },
    )

    for n in body.nominees:
        raw_token, token_hash = generate_invite_token()
        nominees_repo.create_nominee(
            vault_id,
            {
                "name": n.name,
                "relation": n.relation,
                "email": n.email,
                "phone": n.phone,
                "share_bps": n.share_bps,
                "invite_token_hash": token_hash,
                "invite_status": "pending",
            },
        )
        html = invite_email_html(role="nominee", vault_owner_name=profile.get("full_name") or "A Virasat owner", invite_url=f"{_frontend_origin()}/invite/{raw_token}")
        await send_email(to_email=n.email, to_name=n.name, subject="You've been named a nominee on Paytm Virasat", html=html)

    for g in body.guardians:
        raw_token, token_hash = generate_invite_token()
        guardians_repo.create_guardian(
            vault_id,
            {
                "name": g.name,
                "relation": g.relation,
                "email": g.email,
                "invite_token_hash": token_hash,
                "status": "pending",
            },
        )
        html = invite_email_html(role="guardian", vault_owner_name=profile.get("full_name") or "A Virasat owner", invite_url=f"{_frontend_origin()}/invite/{raw_token}")
        await send_email(to_email=g.email, to_name=g.name, subject="You've been asked to be a guardian on Paytm Virasat", html=html)

    # Real on-chain createVault needs the full accepted guardian/nominee
    # address arrays (see maybe_create_vault_onchain's docstring) -- this
    # attempt is a no-op until enough of them have accepted their invites.
    await maybe_create_vault_onchain(vault_id)

    vault_row = vaults_repo.get_vault(vault_id) or vault_row
    return _build_vault_out(vault_row)


async def maybe_create_vault_onchain(vault_id: str) -> Optional[dict]:
    """Best-effort: attempts the on-chain `createVault` call once enough
    participants are ready. The real `CreateVaultReq` (VirasatRegistry.sol)
    needs the FULL guardian/nominee address arrays up front -- it sets up
    on-chain storage for them in the same transaction -- so this can only
    succeed once at least `threshold` guardians and at least 1 nominee have
    accepted their invites (and so have custodial wallets). Per the demo
    script (section 19), guardians/nominees are expected to already be
    accepted before "Seal my Virasat" is pressed; we also retry this from
    invites.py every time a new guardian/nominee accepts, so the vault
    converges to on-chain-created as soon as the real-world precondition is
    met. Any failure (chain not configured, RPC down, still not enough
    accepted participants) is logged and swallowed -- the vault simply stays
    in `draft`/off-chain until retried."""
    vault = vaults_repo.get_vault(vault_id)
    if not vault or vault.get("chain_vault_id") is not None:
        return None  # already on-chain, or doesn't exist

    profile = profiles_repo.get_profile(vault["owner_id"]) or {}
    if not profile.get("wallet_address") or not profile.get("wallet_key_enc"):
        logger.warning("create_vault_chain_skipped_no_owner_wallet", vault_id=vault_id)
        return None

    accepted_guardians = [g for g in guardians_repo.list_guardians(vault_id) if g.get("status") == "accepted" and g.get("wallet_address")]
    accepted_nominees = [n for n in nominees_repo.list_nominees(vault_id) if n.get("invite_status") == "accepted" and n.get("wallet_address")]

    threshold = vault.get("threshold", 2)
    if len(accepted_guardians) < threshold or not accepted_nominees:
        logger.info(
            "create_vault_chain_not_ready",
            vault_id=vault_id,
            accepted_guardians=len(accepted_guardians),
            threshold=threshold,
            accepted_nominees=len(accepted_nominees),
        )
        return None

    total_bps = sum(n.get("share_bps", 0) for n in accepted_nominees)
    if total_bps != 10000:
        logger.warning("create_vault_chain_skipped_bad_shares", vault_id=vault_id, total_bps=total_bps)
        return None

    try:
        from app.services.chain import contracts as contracts_service
        from app.services.chain import eip712
        from app.services.chain.relayer import get_relayer
        from app.services.chain.web3_client import get_contract

        registry = get_contract("registry")
        relayer = get_relayer()
        if registry is None or not relayer.is_configured():
            logger.warning("create_vault_chain_skipped", vault_id=vault_id, reason="registry or relayer not configured")
            return None

        owner_address = profile["wallet_address"]
        guardian_addrs = [g["wallet_address"] for g in accepted_guardians]
        nominee_addrs = [n["wallet_address"] for n in accepted_nominees]
        shares_bps = [n["share_bps"] for n in accepted_nominees]

        deadline = int(time.time()) + 3600
        manifest_hash_bytes = bytes.fromhex(vault["manifest_hash"].removeprefix("0x"))
        guardians_hash = contracts_service.compute_guardians_hash(guardian_addrs)
        nominees_hash = contracts_service.compute_nominees_hash(nominee_addrs, shares_bps)
        nonce = contracts_service.read_nonce(owner_address)

        full_message = eip712.build_create_vault(
            verifying_contract=registry.address,
            owner=owner_address,
            manifest_hash=manifest_hash_bytes,
            inactivity_period=vault["inactivity_secs"],
            challenge_period=vault["challenge_secs"],
            threshold=threshold,
            guardians_hash=guardians_hash,
            nominees_hash=nominees_hash,
            nonce=nonce,
            deadline=deadline,
        )
        owner_private_key = wallet_service.decrypt_private_key(profile["wallet_key_enc"])
        signature_hex = eip712.sign_typed_data(owner_private_key, full_message)

        req_tuple = contracts_service.build_create_vault_req_tuple(
            owner=owner_address,
            manifest_hash=manifest_hash_bytes,
            inactivity_period=vault["inactivity_secs"],
            challenge_period=vault["challenge_secs"],
            threshold=threshold,
            guardians=guardian_addrs,
            nominees=nominee_addrs,
            shares_bps=shares_bps,
            nonce=nonce,
            deadline=deadline,
        )
        build_fn = contracts_service.build_create_vault(req_tuple, bytes.fromhex(signature_hex.removeprefix("0x")))
        idempotency_key = f"create_vault:{vault_id}:{nonce}"
        result = await relayer.send(
            kind="create_vault", vault_id=vault_id, idempotency_key=idempotency_key, build_fn=build_fn, payload={"nonce": nonce}
        )
        return result
    except ApiError:
        logger.warning("create_vault_chain_failed", vault_id=vault_id)
        return None
    except Exception:
        logger.exception("create_vault_chain_unexpected_error", vault_id=vault_id)
        return None


@router.get("/vault", response_model=VaultOut)
async def get_vault(user: CurrentUser = Depends(get_current_user)) -> VaultOut:
    vault = vaults_repo.get_vault_by_owner(user.id)
    if not vault:
        raise ApiError("vault_not_found", "Not found", "No vault exists for this owner yet.", 404)
    return _build_vault_out(vault)


@router.patch("/vault/settings", response_model=VaultOut)
async def patch_vault_settings(body: VaultSettingsPatch, user: CurrentUser = Depends(get_current_user)) -> VaultOut:
    vault = vaults_repo.get_vault_by_owner(user.id)
    if not vault:
        raise ApiError("vault_not_found", "Not found", "No vault exists for this owner yet.", 404)
    # NOTE: the current on-chain VirasatRegistry ABI (section 10.1) has no
    # direct "update periods" entrypoint; inactivity/challenge/threshold
    # changes are applied here in the DB and take full effect on the next
    # reseal (which re-signs a fresh on-chain commitment). TODO: add an
    # on-chain UpdateSettings action if the contracts team exposes one.
    patch = body.model_dump(exclude_unset=True)
    updated = vaults_repo.update_vault(vault["id"], patch)
    return _build_vault_out(updated or vault)


@router.post("/vault/reseal", response_model=TxAck)
async def reseal_vault(user: CurrentUser = Depends(get_current_user)) -> TxAck:
    vault = vaults_repo.get_vault_by_owner(user.id)
    if not vault:
        raise ApiError("vault_not_found", "Not found", "No vault exists for this owner yet.", 404)

    profile = profiles_repo.get_profile(user.id) or {}
    assets = assets_repo.list_assets(user.id)
    documents = documents_repo.list_documents(user.id)
    vault_nominees = nominees_repo.list_nominees(vault["id"])

    new_epoch = (vault.get("epoch") or 0) + 1
    manifest = manifest_service.build_manifest(owner=profile, assets=assets, documents=documents, nominees=vault_nominees)
    sealed = manifest_service.seal_manifest(manifest, vault_id=vault["id"], epoch=new_epoch)
    manifest_path = _upload_sealed_manifest(vault["id"], sealed.ciphertext)

    vaults_repo.update_vault(
        vault["id"],
        {
            "epoch": new_epoch,
            "manifest_hash": sealed.manifest_hash_hex,
            "manifest_path": manifest_path,
            "escrow_share_enc": manifest_service.pack_escrow_column(
                escrow_share_enc=sealed.escrow_share_enc, nominee_pending_share_b64=sealed.nominee_share_b64
            ),
            "recovery_share_enc": sealed.recovery_share_enc,
        },
    )

    tx = await _sign_and_relay_update_manifest(vault_id=vault["id"], chain_vault_id=vault.get("chain_vault_id"), owner_id=user.id, manifest_hash_hex=sealed.manifest_hash_hex)
    return TxAck.model_validate({"status": "queued" if tx is None else tx.get("status", "queued"), "tx_hash": (tx or {}).get("tx_hash"), "idempotency_key": (tx or {}).get("idempotency_key")})


async def _sign_and_relay_update_manifest(*, vault_id: str, chain_vault_id: Optional[int], owner_id: str, manifest_hash_hex: str) -> Optional[dict]:
    if chain_vault_id is None:
        logger.warning("reseal_chain_skipped_no_chain_vault_id", vault_id=vault_id)
        return None
    try:
        from app.services.chain import contracts as contracts_service
        from app.services.chain import eip712
        from app.services.chain.relayer import get_relayer
        from app.services.chain.web3_client import get_contract

        registry = get_contract("registry")
        relayer = get_relayer()
        if registry is None or not relayer.is_configured():
            return None

        profile = profiles_repo.get_profile(owner_id) or {}
        deadline = int(time.time()) + 3600
        manifest_hash_bytes = bytes.fromhex(manifest_hash_hex.removeprefix("0x"))
        nonce = contracts_service.read_nonce(profile["wallet_address"])
        full_message = eip712.build_update_manifest(
            verifying_contract=registry.address, vault_id=chain_vault_id, manifest_hash=manifest_hash_bytes, nonce=nonce, deadline=deadline
        )
        owner_private_key = wallet_service.decrypt_private_key(profile["wallet_key_enc"])
        signature_hex = eip712.sign_typed_data(owner_private_key, full_message)
        build_fn = contracts_service.build_update_manifest(chain_vault_id, manifest_hash_bytes, deadline, bytes.fromhex(signature_hex.removeprefix("0x")))
        idempotency_key = f"update_manifest:{vault_id}:{full_message['message']['nonce']}"
        return await relayer.send(kind="update_manifest", vault_id=vault_id, idempotency_key=idempotency_key, build_fn=build_fn)
    except Exception:
        logger.exception("reseal_chain_failed", vault_id=vault_id)
        return None


@router.post("/vault/cancel", response_model=TxAck)
async def cancel_release(user: CurrentUser = Depends(get_current_user)) -> TxAck:
    vault = vaults_repo.get_vault_by_owner(user.id)
    if not vault:
        raise ApiError("vault_not_found", "Not found", "No vault exists for this owner yet.", 404)
    if vault.get("state") != "challenge":
        raise ApiError("vault_not_in_challenge", "Conflict", "Vault is not currently in a challenge window.", 409)

    profile = profiles_repo.get_profile(user.id) or {}
    try:
        from app.services.chain import contracts as contracts_service
        from app.services.chain import eip712
        from app.services.chain.relayer import get_relayer
        from app.services.chain.web3_client import get_contract

        registry = get_contract("registry")
        relayer = get_relayer()
        chain_vault_id = vault.get("chain_vault_id")
        if registry is None or not relayer.is_configured() or chain_vault_id is None:
            # Degrade gracefully but still reflect the owner's intent locally.
            vaults_repo.update_vault(vault["id"], {"state": "active", "epoch": (vault.get("epoch") or 0) + 1})
            return TxAck(status="queued", tx_hash=None)

        deadline = int(time.time()) + 3600
        nonce = contracts_service.read_nonce(profile["wallet_address"])
        full_message = eip712.build_cancel_release(
            verifying_contract=registry.address, vault_id=chain_vault_id, epoch=vault.get("epoch", 0), nonce=nonce, deadline=deadline
        )
        owner_private_key = wallet_service.decrypt_private_key(profile["wallet_key_enc"])
        signature_hex = eip712.sign_typed_data(owner_private_key, full_message)
        build_fn = contracts_service.build_cancel_release(chain_vault_id, deadline, bytes.fromhex(signature_hex.removeprefix("0x")))
        idempotency_key = f"cancel_release:{vault['id']}:{vault.get('epoch', 0)}:{nonce}"
        result = await relayer.send(kind="cancel_release", vault_id=vault["id"], idempotency_key=idempotency_key, build_fn=build_fn)
        return TxAck.model_validate({"status": result.get("status", "sent"), "tx_hash": result.get("tx_hash"), "idempotency_key": idempotency_key})
    except Exception:
        logger.exception("cancel_release_failed", vault_id=vault["id"])
        raise ApiError("cancel_release_failed", "Internal server error", "Could not cancel release.", 500)


@router.post("/vault/nominees", response_model=list[NomineeOut], status_code=201)
async def add_nominees(body: list[NomineeIn], user: CurrentUser = Depends(get_current_user)) -> list[NomineeOut]:
    vault = vaults_repo.get_vault_by_owner(user.id)
    if not vault:
        raise ApiError("vault_not_found", "Not found", "No vault exists for this owner yet.", 404)
    profile = profiles_repo.get_profile(user.id) or {}
    out = []
    for n in body:
        raw_token, token_hash = generate_invite_token()
        row = nominees_repo.create_nominee(
            vault["id"],
            {"name": n.name, "relation": n.relation, "email": n.email, "phone": n.phone, "share_bps": n.share_bps, "invite_token_hash": token_hash, "invite_status": "pending"},
        )
        html = invite_email_html(role="nominee", vault_owner_name=profile.get("full_name") or "A Virasat owner", invite_url=f"{_frontend_origin()}/invite/{raw_token}")
        await send_email(to_email=n.email, to_name=n.name, subject="You've been named a nominee on Paytm Virasat", html=html)
        out.append(NomineeOut.model_validate(row))
    return out


@router.post("/vault/guardians", response_model=list[GuardianOut], status_code=201)
async def add_guardians(body: list[GuardianIn], user: CurrentUser = Depends(get_current_user)) -> list[GuardianOut]:
    vault = vaults_repo.get_vault_by_owner(user.id)
    if not vault:
        raise ApiError("vault_not_found", "Not found", "No vault exists for this owner yet.", 404)
    profile = profiles_repo.get_profile(user.id) or {}
    out = []
    for g in body:
        raw_token, token_hash = generate_invite_token()
        row = guardians_repo.create_guardian(
            vault["id"], {"name": g.name, "relation": g.relation, "email": g.email, "invite_token_hash": token_hash, "status": "pending"}
        )
        html = invite_email_html(role="guardian", vault_owner_name=profile.get("full_name") or "A Virasat owner", invite_url=f"{_frontend_origin()}/invite/{raw_token}")
        await send_email(to_email=g.email, to_name=g.name, subject="You've been asked to be a guardian on Paytm Virasat", html=html)
        out.append(GuardianOut.model_validate(row))
    return out


def _frontend_origin() -> str:
    from app.core.config import settings

    return settings.FRONTEND_ORIGIN.rstrip("/")
