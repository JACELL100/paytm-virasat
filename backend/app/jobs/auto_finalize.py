"""`auto_finalize` job, section 8.6: relays `finalizeRelease` for vaults past
`challengeEndsAt`, every 60s while awake."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.db.repos import vaults as vaults_repo

logger = get_logger(__name__)


async def run_auto_finalize() -> dict[str, Any]:
    try:
        challenge_vaults = vaults_repo.list_vaults_for_state("challenge")
    except Exception:
        logger.warning("auto_finalize_no_db")
        return {"finalized": 0, "reason": "db_unavailable"}

    now = datetime.now(timezone.utc)
    finalized = 0

    try:
        from app.services.chain import contracts as contracts_service
        from app.services.chain.relayer import get_relayer
        from app.services.chain.web3_client import get_contract

        registry = get_contract("registry")
        relayer = get_relayer()
        if registry is None or not relayer.is_configured():
            return {"finalized": 0, "reason": "chain_unavailable"}

        for v in challenge_vaults:
            ends_at = v.get("challenge_ends_at")
            if not ends_at or v.get("chain_vault_id") is None:
                continue
            try:
                ends_dt = datetime.fromisoformat(ends_at.replace("Z", "+00:00"))
            except Exception:
                continue
            if now < ends_dt:
                continue
            build_fn = contracts_service.build_finalize_release(int(v["chain_vault_id"]))
            idempotency_key = f"finalize_release:{v['id']}:{v.get('epoch', 0)}"
            await relayer.send(kind="finalize_release", vault_id=v["id"], idempotency_key=idempotency_key, build_fn=build_fn)
            finalized += 1
    except Exception:
        logger.exception("auto_finalize_failed")

    return {"finalized": finalized, "checked": len(challenge_vaults)}
