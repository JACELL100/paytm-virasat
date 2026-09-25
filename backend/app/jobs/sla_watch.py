"""`sla_watch` job, section 8.6: hourly, claims past `sla_due_at` get a
notification and an escalation draft queued."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.db.repos import claims as claims_repo
from app.db.repos import notifications as notifications_repo

logger = get_logger(__name__)

TERMINAL_STATUSES = {"settled", "rejected"}


async def run_sla_watch() -> dict[str, Any]:
    try:
        claims = claims_repo.list_claims()
    except Exception:
        logger.warning("sla_watch_no_db")
        return {"checked": 0, "breached": 0, "reason": "db_unavailable"}

    now = datetime.now(timezone.utc)
    breached = 0
    for claim in claims:
        if claim.get("status") in TERMINAL_STATUSES:
            continue
        due = claim.get("sla_due_at")
        if not due:
            continue
        try:
            due_dt = datetime.fromisoformat(due.replace("Z", "+00:00"))
        except Exception:
            continue
        if now > due_dt:
            breached += 1
            claims_repo.add_claim_event(claim["id"], claim.get("status", "under_review"), note="SLA breached -- escalation recommended.")
            try:
                notifications_repo.record_notification(
                    claim.get("nominee_id", ""), "sla_breach", {"claim_id": claim["id"], "due_at": due}
                )
            except Exception:
                logger.warning("sla_watch_notification_failed", claim_id=claim.get("id"))

    return {"checked": len(claims), "breached": breached}
