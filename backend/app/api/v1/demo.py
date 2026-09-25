from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import settings
from app.core.errors import ApiError
from app.core.logging import get_logger
from app.core.security import CurrentUser, get_current_user
from app.db.repos import guardians as guardians_repo
from app.db.repos import nominees as nominees_repo
from app.db.repos import profiles as profiles_repo
from app.db.repos import vaults as vaults_repo
from app.schemas.common import OkResponse

logger = get_logger(__name__)
router = APIRouter(tags=["demo"])

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _require_demo_mode() -> None:
    if not settings.DEMO_MODE:
        raise ApiError("demo_mode_disabled", "Not found", "Demo endpoints are disabled (DEMO_MODE=false).", 404)


class TimeWarpIn(BaseModel):
    vault_id: str
    skip_to: str  # "inactivity_end" | "challenge_end"


@router.post("/demo/time-warp", response_model=OkResponse)
async def time_warp(body: TimeWarpIn, user: CurrentUser = Depends(get_current_user)) -> OkResponse:
    """Shrinks periods to seconds for the demo (section 2/19): rather than
    actually waiting out `inactivity_secs`/`challenge_secs`, this directly
    rewinds `last_activity_at` / `challenge_ends_at` so the real jobs
    (heartbeat/auto_finalize) and on-chain gating still run for real, just
    against warped clocks."""
    _require_demo_mode()
    vault = vaults_repo.get_vault(body.vault_id)
    if not vault:
        raise ApiError("vault_not_found", "Not found", "Vault not found.", 404)

    now = datetime.now(timezone.utc)
    if body.skip_to == "inactivity_end":
        warped = now - timedelta(seconds=vault.get("inactivity_secs", 60) + 5)
        vaults_repo.update_vault(body.vault_id, {"last_activity_at": warped.isoformat()})
    elif body.skip_to == "challenge_end":
        vaults_repo.update_vault(body.vault_id, {"challenge_ends_at": now.isoformat()})
    else:
        raise ApiError("invalid_skip_to", "Bad request", "skip_to must be 'inactivity_end' or 'challenge_end'.", 400)

    return OkResponse(ok=True, detail=f"Time-warped vault {body.vault_id} to {body.skip_to}")


@router.post("/demo/force-heartbeat-batch", response_model=OkResponse)
async def force_heartbeat_batch(user: CurrentUser = Depends(get_current_user)) -> OkResponse:
    _require_demo_mode()
    from app.jobs.heartbeat import run_heartbeat_batch

    result = await run_heartbeat_batch()
    return OkResponse(ok=True, detail=str(result))


@router.post("/demo/force-sync-events", response_model=OkResponse)
async def force_sync_events(user: CurrentUser = Depends(get_current_user)) -> OkResponse:
    _require_demo_mode()
    from app.services.chain.event_sync import sync_all

    result = sync_all()
    return OkResponse(ok=True, detail=str(result))


@router.post("/demo/reset", response_model=OkResponse)
async def reset_demo_persona(user: CurrentUser = Depends(get_current_user)) -> OkResponse:
    """Seeds + links the demo persona (section 19: Rajesh Patil) to the
    currently authenticated user, so a judge/teammate can log in as
    themselves and instantly get the demo owner's data."""
    _require_demo_mode()

    seed_path = DATA_DIR / "seed_demo.json"
    if not seed_path.exists():
        raise ApiError("seed_data_missing", "Internal server error", "app/data/seed_demo.json not found.", 500)
    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    persona = seed.get("persona", {})

    owner = persona.get("owner", {})
    profiles_repo.update_profile(
        user.id,
        {"full_name": owner.get("full_name"), "phone": owner.get("phone"), "annual_income": owner.get("annual_income"), "language": owner.get("language", "en")},
    )

    from app.db.repos import assets as assets_repo

    for txn in seed.get("paytm_feed", []):
        meta = txn.get("meta", {})
        assets_repo.create_asset(
            user.id,
            {
                "type": meta.get("suggested_type", "other"),
                "institution_id": meta.get("institution_slug"),
                "label": txn["narration"].title(),
                "value_estimate": meta.get("value_estimate"),
                "premium_amount": txn.get("debit") or txn.get("credit"),
                "nominee_status": meta.get("nominee_status", "unknown"),
                "source": "demo_seed",
                "confidence": 1.0,
                "meta": meta,
            },
        )

    return OkResponse(ok=True, detail=f"Seeded demo persona '{owner.get('full_name', 'Rajesh Patil')}' for user {user.id}")
