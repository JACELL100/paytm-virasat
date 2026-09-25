
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request, UploadFile

from app.core.errors import ApiError
from app.core.logging import get_logger
from app.core.ratelimit import UPLOAD_RATE_LIMIT, limiter
from app.core.security import CurrentUser, get_current_user
from app.db.repos import assets as assets_repo
from app.db.repos import discovery as discovery_repo
from app.schemas.discovery import DiscoveryResult, SmsIn, SuggestionOut
from app.services.ai.classifier import classify_txn_group
from app.services.discovery.recurring import detect_recurring_groups, match_institution
from app.services.discovery.sms_parser import parse_sms_text
from app.services.discovery.statement_parser import parse_csv_statement, parse_pdf_statement

logger = get_logger(__name__)
router = APIRouter(tags=["discovery"])

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


async def _suggest_from_groups(owner_id: str, source: str, groups: list[dict[str, Any]]) -> DiscoveryResult:
    suggestions = []
    for g in groups:
        institution = match_institution(g["merchant"])
        classification = None
        if not institution:
            # Only ambiguous groups go to the LLM classifier (never raw statements), section 8.3 step 4.
            classification = await classify_txn_group(
                merchant=g["merchant"],
                amount=g["amount"],
                frequency=g.get("periodicity") or "unknown",
                sample_narrations=g.get("sample_narrations", []),
            )
        payload = {
            "merchant": g["merchant"],
            "amount": g["amount"],
            "periodicity": g.get("periodicity"),
            "institution_slug": institution["slug"] if institution else (classification.institution_slug if classification else None),
            "institution_name": institution["name"] if institution else None,
            "product_type": institution.get("kind") if institution else (classification.product_type if classification else "other"),
            "confidence": (institution.get("match_score", 0) / 100) if institution else (classification.confidence if classification else 0.3),
            "rationale": classification.rationale if classification else "Matched against known institution aliases.",
        }
        row = discovery_repo.create_suggestion(owner_id, source, payload)
        suggestions.append(row)
    return DiscoveryResult.model_validate({"suggestions": suggestions, "count": len(suggestions)})


@router.post("/discovery/statement", response_model=DiscoveryResult)
@limiter.limit(UPLOAD_RATE_LIMIT)
async def discover_from_statement(request: Request, file: UploadFile, user: CurrentUser = Depends(get_current_user)) -> DiscoveryResult:
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise ApiError("file_too_large", "Bad request", "File exceeds 10 MB limit.", 400)

    filename = (file.filename or "").lower()
    if filename.endswith(".csv"):
        rows = parse_csv_statement(content)
    else:
        rows = parse_pdf_statement(content)

    groups = detect_recurring_groups(rows)
    return await _suggest_from_groups(user.id, "statement", groups)


@router.post("/discovery/sms", response_model=DiscoveryResult)
@limiter.limit(UPLOAD_RATE_LIMIT)
async def discover_from_sms(request: Request, body: SmsIn, user: CurrentUser = Depends(get_current_user)) -> DiscoveryResult:
    parsed = parse_sms_text(body.text)
    rows = [
        {"date": None, "narration": m["raw"], "debit": m.get("amount"), "credit": None}
        for m in parsed["matched"]
    ]
    groups = detect_recurring_groups(rows) if rows else []
    # Matched single SMS with a strong keyword still becomes a suggestion even without 2 occurrences.
    for m in parsed["matched"]:
        if not any(g["merchant"] == m.get("merchant", "").lower() for g in groups):
            groups.append({"merchant": m.get("merchant", "sms"), "amount": m.get("amount") or 0, "periodicity": "unknown", "sample_narrations": [m["raw"]]})
    return await _suggest_from_groups(user.id, "sms", groups)


@router.post("/discovery/paytm-feed", response_model=DiscoveryResult)
async def discover_from_paytm_feed(user: CurrentUser = Depends(get_current_user)) -> DiscoveryResult:
    seed_path = DATA_DIR / "seed_demo.json"
    if not seed_path.exists():
        return DiscoveryResult(suggestions=[], count=0)
    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    feed = seed.get("paytm_feed", [])

    suggestions = []
    for txn in feed:
        meta = txn.get("meta", {})
        payload = {
            "merchant": txn["narration"],
            "amount": txn.get("debit") or txn.get("credit") or 0,
            "date": txn.get("date"),
            "product_type": meta.get("suggested_type", "other"),
            "institution_slug": meta.get("institution_slug"),
            "value_estimate": meta.get("value_estimate"),
            "nominee_status": meta.get("nominee_status", "unknown"),
            "has_active_loan_protection": meta.get("has_active_loan_protection", False),
            "confidence": 0.95,
            "rationale": "Seeded Paytm transaction feed (demo).",
        }
        row = discovery_repo.create_suggestion(user.id, "paytm_feed", payload)
        suggestions.append(row)
    return DiscoveryResult.model_validate({"suggestions": suggestions, "count": len(suggestions)})


@router.post("/discovery/suggestions/{suggestion_id}/accept", response_model=SuggestionOut)
async def accept_suggestion(suggestion_id: str, user: CurrentUser = Depends(get_current_user)) -> SuggestionOut:
    suggestion = discovery_repo.get_suggestion(user.id, suggestion_id)
    if not suggestion:
        raise ApiError("suggestion_not_found", "Not found", "Suggestion not found.", 404)

    payload = suggestion.get("payload", {})
    assets_repo.create_asset(
        user.id,
        {
            "type": payload.get("product_type", "other"),
            "institution_id": payload.get("institution_slug"),
            "label": payload.get("institution_name") or payload.get("merchant", "Discovered asset"),
            "value_estimate": payload.get("value_estimate"),
            "premium_amount": payload.get("amount"),
            "frequency": payload.get("periodicity"),
            "nominee_status": payload.get("nominee_status", "unknown"),
            "source": suggestion.get("source", "discovery"),
            "confidence": payload.get("confidence"),
            "meta": payload,
        },
    )
    row = discovery_repo.set_suggestion_status(suggestion_id, "accepted")
    return SuggestionOut.model_validate(row)


@router.post("/discovery/suggestions/{suggestion_id}/reject", response_model=SuggestionOut)
async def reject_suggestion(suggestion_id: str, user: CurrentUser = Depends(get_current_user)) -> SuggestionOut:
    suggestion = discovery_repo.get_suggestion(user.id, suggestion_id)
    if not suggestion:
        raise ApiError("suggestion_not_found", "Not found", "Suggestion not found.", 404)
    row = discovery_repo.set_suggestion_status(suggestion_id, "rejected")
    return SuggestionOut.model_validate(row)
