"""Repos for chain_txs, chain_events, sync_cursors -- the relayer's and the
event-sync job's persistence layer."""
from __future__ import annotations

from typing import Any, Optional

from app.db.repos.base import require_client

TXS_TABLE = "chain_txs"
EVENTS_TABLE = "chain_events"
CURSORS_TABLE = "sync_cursors"


def get_tx_by_idempotency_key(idempotency_key: str) -> Optional[dict]:
    client = require_client()
    res = client.table(TXS_TABLE).select("*").eq("idempotency_key", idempotency_key).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def create_queued_tx(idempotency_key: str, kind: str, vault_id: Optional[str], payload: dict) -> dict:
    client = require_client()
    res = client.table(TXS_TABLE).insert(
        {
            "idempotency_key": idempotency_key,
            "kind": kind,
            "vault_id": vault_id,
            "payload": payload,
            "status": "queued",
            "attempts": 0,
        }
    ).execute()
    return (res.data or [{}])[0]


def update_tx(idempotency_key: str, patch: dict[str, Any]) -> Optional[dict]:
    client = require_client()
    res = client.table(TXS_TABLE).update(patch).eq("idempotency_key", idempotency_key).execute()
    rows = res.data or []
    return rows[0] if rows else None


def list_sent_txs() -> list[dict]:
    client = require_client()
    res = client.table(TXS_TABLE).select("*").eq("status", "sent").execute()
    return res.data or []


def insert_chain_event(event: dict[str, Any]) -> Optional[dict]:
    client = require_client()
    try:
        res = client.table(EVENTS_TABLE).insert(event).execute()
        return (res.data or [{}])[0]
    except Exception:
        # unique (tx_hash, log_index) violation => already synced, ignore
        return None


def get_cursor(contract: str) -> int:
    client = require_client()
    res = client.table(CURSORS_TABLE).select("last_block").eq("contract", contract).limit(1).execute()
    rows = res.data or []
    return rows[0]["last_block"] if rows else 0


def set_cursor(contract: str, last_block: int) -> None:
    client = require_client()
    client.table(CURSORS_TABLE).upsert({"contract": contract, "last_block": last_block}, on_conflict="contract").execute()
