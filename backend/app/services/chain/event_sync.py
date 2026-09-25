"""Polls `eth_getLogs` for the registry/credential/ledger contracts from the
last synced block, upserts `chain_events`, and reacts by updating
`vaults`/`claims` state. Used by both APScheduler (fast interval while the
Render instance is awake) and the `/jobs/sync-events` cron endpoint.
"""
from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.db.repos import chain as chain_repo
from app.db.repos import vaults as vaults_repo
from app.services.chain.web3_client import get_contract, get_w3

logger = get_logger(__name__)

MAX_BLOCK_RANGE = 5000


def _sync_contract(name: str) -> int:
    w3 = get_w3()
    contract = get_contract(name)
    if w3 is None or contract is None:
        return 0

    try:
        latest = w3.eth.block_number
    except Exception:
        logger.warning("event_sync_block_number_failed", contract=name)
        return 0

    from_block = chain_repo.get_cursor(name) or settings.REGISTRY_DEPLOY_BLOCK
    if from_block <= 0:
        from_block = max(latest - 1, 0)
    to_block = min(latest, from_block + MAX_BLOCK_RANGE)
    if to_block < from_block:
        return 0

    count = 0
    try:
        logs = w3.eth.get_logs({"address": contract.address, "fromBlock": from_block, "toBlock": to_block})
    except Exception:
        logger.warning("event_sync_get_logs_failed", contract=name, from_block=from_block, to_block=to_block)
        return 0

    for log in logs:
        try:
            event = _decode_log(contract, log)
        except Exception:
            continue
        if event is None:
            continue
        row = {
            "block_number": log["blockNumber"],
            "tx_hash": log["transactionHash"].hex()
            if hasattr(log["transactionHash"], "hex")
            else log["transactionHash"],
            "log_index": log["logIndex"],
            "contract": name,
            "event": event["event"],
            "args": _jsonable(event["args"]),
        }
        if chain_repo.insert_chain_event(row):
            count += 1
            _react_to_event(name, event["event"], event["args"])

    chain_repo.set_cursor(name, to_block + 1)
    return count


def _decode_log(contract, log) -> dict[str, Any] | None:
    for event_abi in [e for e in contract.abi if e.get("type") == "event"]:
        try:
            ev = contract.events[event_abi["name"]]().process_log(log)
            return {"event": ev["event"], "args": dict(ev["args"])}
        except Exception:
            continue
    return None


def _jsonable(args: dict) -> dict:
    out = {}
    for k, v in args.items():
        if isinstance(v, (bytes, bytearray)):
            out[k] = "0x" + v.hex()
        else:
            out[k] = v
    return out


def _react_to_event(contract_name: str, event_name: str, args: dict) -> None:
    """Keeps `vaults.state` etc. in sync with on-chain reality."""
    if contract_name != "registry":
        return
    try:
        vault_chain_id = args.get("vaultId")
        if vault_chain_id is None:
            return
        from app.db.client import get_supabase

        client = get_supabase()
        if client is None:
            return

        if event_name == "VaultCreated":
            # Our local DB row doesn't have `chain_vault_id` set yet (the
            # relayer only gets a tx hash back, not the assigned vaultId) --
            # link it here via the owner's wallet address instead, which is
            # unique per profile and this is the one-time hand-off moment.
            owner_address = args.get("owner")
            if not owner_address:
                return
            prof_res = client.table("profiles").select("id").ilike("wallet_address", owner_address).limit(1).execute()
            prof_rows = prof_res.data or []
            if not prof_rows:
                logger.warning("vault_created_event_no_matching_profile", owner=owner_address)
                return
            vault_res = client.table("vaults").select("id").eq("owner_id", prof_rows[0]["id"]).limit(1).execute()
            vault_rows = vault_res.data or []
            if not vault_rows:
                logger.warning("vault_created_event_no_matching_vault", owner=owner_address)
                return
            vault_id = vault_rows[0]["id"]
            vaults_repo.update_vault(vault_id, {"chain_vault_id": int(vault_chain_id), "state": "active"})
            return

        # Every other event already has our chain_vault_id populated (it can
        # only fire after VaultCreated), so a direct lookup is enough.
        res = client.table("vaults").select("id").eq("chain_vault_id", int(vault_chain_id)).limit(1).execute()
        rows = res.data or []
        if not rows:
            return
        vault_id = rows[0]["id"]

        patch: dict[str, Any] = {}
        if event_name == "Heartbeat":
            from datetime import datetime, timezone

            patch = {"last_heartbeat_onchain_at": datetime.now(timezone.utc).isoformat()}
        elif event_name == "ChallengeStarted":
            patch = {"state": "challenge"}
        elif event_name == "ReleaseCancelled":
            patch = {"state": "active"}
        elif event_name == "Released":
            patch = {"state": "released"}

        if patch:
            vaults_repo.update_vault(vault_id, patch)
    except Exception:
        logger.exception("event_sync_react_failed", event=event_name)


def sync_all() -> dict[str, int]:
    results = {}
    for name in ("registry", "credential", "ledger"):
        results[name] = _sync_contract(name)
    return results
