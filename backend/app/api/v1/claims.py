
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request

from app.core.errors import ApiError
from app.core.logging import get_logger
from app.core.ratelimit import AI_RATE_LIMIT, limiter
from app.core.security import CurrentUser, get_current_user
from app.db.repos import assets as assets_repo
from app.db.repos import claims as claims_repo
from app.db.repos import institutions as institutions_repo
from app.db.repos import nominees as nominees_repo
from app.schemas.claims import ClaimCreate, ClaimOut, ClaimPackOut, ClaimUpdate, EscalationIn, EscalationOut

logger = get_logger(__name__)
router = APIRouter(tags=["claims"])

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _load_claim_requirements() -> dict:
    path = DATA_DIR / "claim_requirements.json"
    if not path.exists():
        return {"generic_templates": {}, "escalation_contacts": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _nominee_for_user_in_vault(user_id: str, vault_id: str) -> Optional[dict]:
    rows = nominees_repo.list_vaults_for_nominee_user(user_id)
    for r in rows:
        if r.get("vault_id") == vault_id:
            return r
    return None


def _required_docs_for_asset(asset_type: str) -> list[str]:
    reqs = _load_claim_requirements()
    for tmpl in reqs.get("generic_templates", {}).values():
        if asset_type in tmpl.get("product_types", []):
            return tmpl.get("base_docs", [])
    return ["Claim form", "Death certificate", "Claimant KYC"]


@router.get("/claims", response_model=list[ClaimOut])
async def list_claims(vault_id: Optional[str] = None, user: CurrentUser = Depends(get_current_user)) -> list[ClaimOut]:
    nominee_rows = nominees_repo.list_vaults_for_nominee_user(user.id)
    nominee_ids = [r["id"] for r in nominee_rows if not vault_id or r.get("vault_id") == vault_id]
    all_claims = []
    for nid in nominee_ids:
        all_claims.extend(claims_repo.list_claims(nominee_id=nid))
    return [ClaimOut.model_validate(c) for c in all_claims]


@router.post("/claims", response_model=ClaimOut, status_code=201)
async def create_claim(body: ClaimCreate, user: CurrentUser = Depends(get_current_user)) -> ClaimOut:
    asset = None
    for owner_scope in (user.id,):
        asset = assets_repo.get_asset(owner_scope, body.asset_id)
        if asset:
            break
    if not asset:
        raise ApiError("asset_not_found", "Not found", "Asset not found (or you don't have access).", 404)

    # The caller must be a nominee on some released vault; find the matching one.
    nominee_rows = nominees_repo.list_vaults_for_nominee_user(user.id)
    if not nominee_rows:
        raise ApiError("not_a_nominee", "Forbidden", "You are not a nominee on any vault.", 403)
    nominee = nominee_rows[0]
    vault_id = nominee["vault_id"]

    required_docs = _required_docs_for_asset(asset.get("type", "other"))
    checklist = {"required": required_docs, "available": []}

    row = claims_repo.create_claim(
        vault_id,
        nominee["id"],
        {"asset_id": body.asset_id, "institution_id": body.institution_id or asset.get("institution_id"), "status": "not_started", "checklist": checklist},
    )
    claims_repo.add_claim_event(row["id"], "not_started", note="Claim created")
    await _log_onchain(vault_id, row["id"], 0)
    return ClaimOut.model_validate(row)


@router.get("/claims/{claim_id}", response_model=ClaimOut)
async def get_claim(claim_id: str, user: CurrentUser = Depends(get_current_user)) -> ClaimOut:
    claim = claims_repo.get_claim(claim_id)
    if not claim or not _nominee_for_user_in_vault(user.id, claim["vault_id"]):
        raise ApiError("claim_not_found", "Not found", "Claim not found.", 404)
    return ClaimOut.model_validate(claim)


STATUS_CODES = {
    "not_started": 0,
    "docs_pending": 1,
    "ready_to_file": 2,
    "filed": 3,
    "under_review": 4,
    "query_raised": 5,
    "settled": 6,
    "rejected": 7,
    "escalated": 8,
}


@router.patch("/claims/{claim_id}", response_model=ClaimOut)
async def patch_claim(claim_id: str, body: ClaimUpdate, user: CurrentUser = Depends(get_current_user)) -> ClaimOut:
    claim = claims_repo.get_claim(claim_id)
    if not claim or not _nominee_for_user_in_vault(user.id, claim["vault_id"]):
        raise ApiError("claim_not_found", "Not found", "Claim not found.", 404)

    patch = body.model_dump(exclude_unset=True)
    updated = claims_repo.update_claim(claim_id, patch) or claim
    if body.status:
        claims_repo.add_claim_event(claim_id, body.status, note=body.note)
        await _log_onchain(claim["vault_id"], claim_id, STATUS_CODES.get(body.status, 0))
    return ClaimOut.model_validate(updated)


async def _log_onchain(vault_id: str, claim_id: str, status_code: int) -> None:
    """Best-effort ClaimLedger.log() -- every claim status change is
    timestamped on-chain per section 10.3. Failures are logged, not fatal."""
    try:
        from eth_utils import keccak

        from app.db.repos import vaults as vaults_repo
        from app.services.chain import contracts as contracts_service
        from app.services.chain.relayer import get_relayer
        from app.services.chain.web3_client import get_contract

        ledger = get_contract("ledger")
        relayer = get_relayer()
        if ledger is None or not relayer.is_configured():
            return
        vault = vaults_repo.get_vault(vault_id)
        chain_vault_id = (vault or {}).get("chain_vault_id")
        if chain_vault_id is None:
            return
        claim_id_hash = keccak(text=claim_id)
        build_fn = contracts_service.build_claim_log(claim_id_hash, chain_vault_id, status_code, b"\x00" * 32)
        idempotency_key = f"claim_log:{claim_id}:{status_code}"
        result = await relayer.send(kind="claim_log", vault_id=vault_id, idempotency_key=idempotency_key, build_fn=build_fn)
        claims_repo.update_claim(claim_id, {})  # no-op; tx recorded in chain_txs already
        if result:
            claims_repo.add_claim_event(claim_id, "chain_logged", note=result.get("tx_hash"), tx_id=result.get("idempotency_key"))
    except Exception:
        logger.warning("claim_log_onchain_failed", claim_id=claim_id)


@router.post("/claims/{claim_id}/pack", response_model=ClaimPackOut)
@limiter.limit(AI_RATE_LIMIT)
async def generate_claim_pack(request: Request, claim_id: str, user: CurrentUser = Depends(get_current_user)) -> ClaimPackOut:
    claim = claims_repo.get_claim(claim_id)
    if not claim or not _nominee_for_user_in_vault(user.id, claim["vault_id"]):
        raise ApiError("claim_not_found", "Not found", "Claim not found.", 404)

    asset = assets_repo.get_asset(claim.get("owner_id", ""), claim["asset_id"]) or {"label": "Asset", "id": claim["asset_id"]}
    institution = institutions_repo.get_institution(claim.get("institution_id")) if claim.get("institution_id") else None
    checklist_data = claim.get("checklist") or {}
    required = checklist_data.get("required", [])
    available = set(checklist_data.get("available", []))
    checklist = [{"name": d, "present": d in available} for d in required]

    from app.services.pdf.claim_pack import build_claim_pack_pdf

    pdf_bytes = build_claim_pack_pdf(claim=claim, asset=asset, institution=institution, checklist=checklist)

    from app.db.client import get_supabase

    client = get_supabase()
    signed_url = None
    if client is not None:
        try:
            path = f"{claim['vault_id']}/{claim_id}.pdf"
            client.storage.from_("claim-packs").upload(path, pdf_bytes, {"content-type": "application/pdf", "upsert": "true"})
            signed = client.storage.from_("claim-packs").create_signed_url(path, 600)
            signed_url = signed.get("signedURL") or signed.get("signed_url")
            claims_repo.update_claim(claim_id, {"pack_path": path})
        except Exception:
            logger.warning("claim_pack_upload_failed", claim_id=claim_id)

    if not signed_url:
        signed_url = f"data:application/pdf;base64,(generated, storage unavailable -- {len(pdf_bytes)} bytes)"

    return ClaimPackOut(signed_url=signed_url, expires_in=600)


@router.post("/claims/{claim_id}/escalation", response_model=EscalationOut)
@limiter.limit(AI_RATE_LIMIT)
async def draft_escalation(request: Request, claim_id: str, body: EscalationIn, user: CurrentUser = Depends(get_current_user)) -> EscalationOut:
    claim = claims_repo.get_claim(claim_id)
    if not claim or not _nominee_for_user_in_vault(user.id, claim["vault_id"]):
        raise ApiError("claim_not_found", "Not found", "Claim not found.", 404)

    events = claims_repo.list_claim_events(claim_id)
    facts = "\n".join(f"- {e.get('created_at', '')}: {e.get('status')} {e.get('note') or ''}" for e in events)

    try:
        from app.services.ai.groq_client import GroqNotConfigured, chat_complete

        messages = [
            {
                "role": "system",
                "content": "Draft a formal, factual English grievance/escalation letter using the claim event history. No exaggeration.",
            },
            {"role": "user", "content": f"Claim ID: {claim_id}\nEscalation level: {body.level}\nEvent history:\n{facts}"},
        ]
        letter = await chat_complete("extract", messages, json_mode=False, temperature=0.2)
    except Exception:
        letter = (
            f"To Whom It May Concern,\n\nThis is a formal escalation regarding claim {claim_id} "
            f"(level: {body.level}). Please see the attached claim history for details.\n\nRegards,\n"
            "Claimant, via Paytm Virasat Claim Co-pilot"
        )

    return EscalationOut(letter_text=letter, pdf_signed_url=None)
