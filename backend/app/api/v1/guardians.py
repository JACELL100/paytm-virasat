
import hashlib
import time
from typing import Optional

from fastapi import APIRouter, Depends, Request, UploadFile
from pydantic import BaseModel

from app.core.errors import ApiError
from app.core.logging import get_logger
from app.core.ratelimit import UPLOAD_RATE_LIMIT, limiter
from app.core.security import CurrentUser, get_current_user
from app.db.repos import attestations as attestations_repo
from app.db.repos import guardians as guardians_repo
from app.db.repos import profiles as profiles_repo
from app.db.repos import vaults as vaults_repo
from app.schemas.vault import VaultOut

logger = get_logger(__name__)
router = APIRouter(tags=["guardian"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class DeathCertificateOut(BaseModel):
    document_id: Optional[str] = None
    death_cert_hash: str
    extracted: dict
    name_match_score: float
    qr_decoded_url: Optional[str] = None


class AttestIn(BaseModel):
    death_cert_hash: str
    reason_if_low_match: Optional[str] = None


class AttestOut(BaseModel):
    status: str
    tx_hash: Optional[str] = None
    attest_count: Optional[int] = None
    threshold: Optional[int] = None


@router.get("/guardian/vaults", response_model=list[VaultOut])
async def my_guardian_vaults(user: CurrentUser = Depends(get_current_user)) -> list[VaultOut]:
    rows = guardians_repo.list_vaults_for_guardian_user(user.id)
    out = []
    for r in rows:
        vault = r.get("vaults") or vaults_repo.get_vault(r["vault_id"])
        if vault:
            out.append(VaultOut.model_validate({**vault, "nominees": [], "guardians": [], "timeline": []}))
    return out


def _guardian_for_user(user_id: str, vault_id: str) -> Optional[dict]:
    for r in guardians_repo.list_vaults_for_guardian_user(user_id):
        if r["vault_id"] == vault_id:
            return r
    return None


@router.post("/guardian/vaults/{vault_id}/death-certificate", response_model=DeathCertificateOut)
@limiter.limit(UPLOAD_RATE_LIMIT)
async def upload_death_certificate(request: Request, vault_id: str, file: UploadFile, user: CurrentUser = Depends(get_current_user)) -> DeathCertificateOut:
    guardian = _guardian_for_user(user.id, vault_id)
    if not guardian:
        raise ApiError("not_a_guardian", "Forbidden", "You are not a guardian of this vault.", 403)

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise ApiError("file_too_large", "Bad request", "File exceeds 10 MB limit.", 400)

    death_cert_hash = "0x" + hashlib.sha256(content).hexdigest()  # keccak256 used on-chain; sha256 shown for dedup/display here
    try:
        from eth_utils import keccak

        death_cert_hash = "0x" + keccak(content).hex()
    except Exception:
        pass

    from app.db.client import get_supabase

    client = get_supabase()
    document_id = None
    if client is not None:
        try:
            path = f"{vault_id}/{user.id}/{death_cert_hash}.bin"
            client.storage.from_("death-certificates").upload(path, content, {"content-type": "application/octet-stream", "upsert": "true"})
            from app.db.repos import documents as documents_repo

            owner_row = vaults_repo.get_vault(vault_id)
            owner_id = (owner_row or {}).get("owner_id", user.id)
            doc = documents_repo.create_document(
                owner_id, {"kind": "death_certificate", "storage_path": path, "sha256": hashlib.sha256(content).hexdigest(), "status": "processing"}
            )
            document_id = doc.get("id")
        except Exception:
            logger.warning("death_cert_upload_failed", vault_id=vault_id)

    from app.services.ai.extractor import extract_death_certificate, extract_text_pdf
    from app.services.ai.vision import decode_qr, pdf_to_images, vision_extract_text

    text, _pages = extract_text_pdf(content)
    if not text.strip():
        images = pdf_to_images(content) or [content]
        text = await vision_extract_text(images)
    extraction = await extract_death_certificate(text)

    qr_url = decode_qr(content)

    owner_row = vaults_repo.get_vault(vault_id)
    owner_profile = profiles_repo.get_profile((owner_row or {}).get("owner_id", "")) or {}
    owner_name = owner_profile.get("full_name") or ""

    match_score = 0.0
    if extraction.deceased_name and owner_name:
        try:
            from rapidfuzz import fuzz

            match_score = fuzz.token_sort_ratio(extraction.deceased_name, owner_name)
        except Exception:
            match_score = 0.0

    if document_id:
        from app.db.repos import documents as documents_repo

        documents_repo.update_document(document_id, {"extracted": extraction.model_dump(), "status": "extracted"})

    attestations_repo.create_attestation(
        vault_id,
        guardian["id"],
        {
            "document_id": document_id,
            "death_cert_hash": death_cert_hash,
            "extracted": extraction.model_dump(),
            "name_match_score": match_score,
        },
    )

    return DeathCertificateOut(
        document_id=document_id,
        death_cert_hash=death_cert_hash,
        extracted=extraction.model_dump(),
        name_match_score=match_score,
        qr_decoded_url=qr_url,
    )


@router.post("/guardian/vaults/{vault_id}/attest", response_model=AttestOut)
async def attest_death(vault_id: str, body: AttestIn, user: CurrentUser = Depends(get_current_user)) -> AttestOut:
    guardian = _guardian_for_user(user.id, vault_id)
    if not guardian:
        raise ApiError("not_a_guardian", "Forbidden", "You are not a guardian of this vault.", 403)
    if not guardian.get("wallet_address"):
        raise ApiError("guardian_wallet_missing", "Conflict", "Guardian custodial wallet not provisioned yet.", 409)

    vault = vaults_repo.get_vault(vault_id)
    if not vault:
        raise ApiError("vault_not_found", "Not found", "Vault not found.", 404)
    chain_vault_id = vault.get("chain_vault_id")

    from app.services.crypto import wallets as wallet_service

    profile = profiles_repo.get_profile(user.id) or {}
    if not profile.get("wallet_key_enc"):
        raise ApiError("guardian_wallet_missing", "Conflict", "Guardian custodial wallet not provisioned yet.", 409)

    try:
        from app.services.chain import contracts as contracts_service
        from app.services.chain import eip712
        from app.services.chain.relayer import get_relayer
        from app.services.chain.web3_client import get_contract

        registry = get_contract("registry")
        relayer = get_relayer()
        if registry is None or not relayer.is_configured() or chain_vault_id is None:
            logger.warning("attest_death_chain_skipped", vault_id=vault_id)
            return AttestOut(status="recorded_locally_chain_unavailable")

        deadline = int(time.time()) + 3600
        death_cert_hash_bytes = bytes.fromhex(body.death_cert_hash.removeprefix("0x"))
        full_message = eip712.build_attest_death(
            verifying_contract=registry.address, vault_id=chain_vault_id, death_cert_hash=death_cert_hash_bytes, epoch=vault.get("epoch", 0), deadline=deadline
        )
        guardian_private_key = wallet_service.decrypt_private_key(profile["wallet_key_enc"])
        signature_hex = eip712.sign_typed_data(guardian_private_key, full_message)

        build_fn = contracts_service.build_attest_death(chain_vault_id, death_cert_hash_bytes, profile["wallet_address"], deadline, bytes.fromhex(signature_hex.removeprefix("0x")))
        idempotency_key = f"attest_death:{vault_id}:{vault.get('epoch', 0)}:{guardian['id']}"
        result = await relayer.send(kind="attest_death", vault_id=vault_id, idempotency_key=idempotency_key, build_fn=build_fn)
        return AttestOut(status=result.get("status", "sent"), tx_hash=result.get("tx_hash"))
    except ApiError:
        raise
    except Exception:
        logger.exception("attest_death_failed", vault_id=vault_id)
        raise ApiError("attest_death_failed", "Internal server error", "Could not submit attestation.", 500)


@router.post("/vaults/{vault_id}/finalize", response_model=AttestOut)
async def finalize_release(vault_id: str, user: CurrentUser = Depends(get_current_user)) -> AttestOut:
    """Anyone can call this after the challenge window ends, per section 8.2."""
    vault = vaults_repo.get_vault(vault_id)
    if not vault:
        raise ApiError("vault_not_found", "Not found", "Vault not found.", 404)
    chain_vault_id = vault.get("chain_vault_id")

    try:
        from app.services.chain import contracts as contracts_service
        from app.services.chain.relayer import get_relayer
        from app.services.chain.web3_client import get_contract

        registry = get_contract("registry")
        relayer = get_relayer()
        if registry is None or not relayer.is_configured() or chain_vault_id is None:
            return AttestOut(status="skipped_chain_unavailable")

        build_fn = contracts_service.build_finalize_release(chain_vault_id)
        idempotency_key = f"finalize_release:{vault_id}:{vault.get('epoch', 0)}"
        result = await relayer.send(kind="finalize_release", vault_id=vault_id, idempotency_key=idempotency_key, build_fn=build_fn)
        return AttestOut(status=result.get("status", "sent"), tx_hash=result.get("tx_hash"))
    except ApiError:
        raise
    except Exception:
        logger.exception("finalize_release_failed", vault_id=vault_id)
        raise ApiError("finalize_release_failed", "Internal server error", "Could not finalize release.", 500)
