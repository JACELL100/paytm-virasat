"""`heartbeat_batch` job, section 8.6: vaults whose owner had activity since
the last on-chain heartbeat are sent as `heartbeatBatch(ids[])` in chunks of
50. Also auto-cancels a challenge if the owner (or any activity) shows up.
"""
from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.db.repos import activity as activity_repo
from app.db.repos import vaults as vaults_repo

logger = get_logger(__name__)

CHUNK_SIZE = 50


async def run_heartbeat_batch() -> dict[str, Any]:
    try:
        vaults = vaults_repo.list_all_active_vaults()
    except Exception:
        logger.warning("heartbeat_batch_no_db")
        return {"sent": 0, "reason": "db_unavailable"}

    due_chain_ids: list[int] = []
    due_vault_ids: list[str] = []
    for v in vaults:
        if v.get("chain_vault_id") is None:
            continue
        last_activity = activity_repo.last_activity_at(v["owner_id"])
        last_hb = v.get("last_heartbeat_onchain_at")
        if last_activity and (not last_hb or last_activity > last_hb):
            due_chain_ids.append(int(v["chain_vault_id"]))
            due_vault_ids.append(v["id"])

    if not due_chain_ids:
        return {"sent": 0}

    sent = 0
    try:
        from app.services.chain import contracts as contracts_service
        from app.services.chain.relayer import get_relayer
        from app.services.chain.web3_client import get_contract

        registry = get_contract("registry")
        relayer = get_relayer()
        if registry is None or not relayer.is_configured():
            logger.warning("heartbeat_batch_chain_unavailable", due=len(due_chain_ids))
            return {"sent": 0, "due": len(due_chain_ids), "reason": "chain_unavailable"}

        for i in range(0, len(due_chain_ids), CHUNK_SIZE):
            chunk = due_chain_ids[i : i + CHUNK_SIZE]
            build_fn = contracts_service.build_heartbeat_batch(chunk)
            idempotency_key = f"heartbeat_batch:{min(chunk)}:{max(chunk)}:{len(chunk)}"
            await relayer.send(kind="heartbeat_batch", vault_id=None, idempotency_key=idempotency_key, build_fn=build_fn)
            sent += len(chunk)
    except Exception:
        logger.exception("heartbeat_batch_failed")

    return {"sent": sent, "due": len(due_chain_ids)}
