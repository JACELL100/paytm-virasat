from __future__ import annotations

from typing import Any, Optional

from app.db.repos.base import require_client

TABLE = "claims"
EVENTS_TABLE = "claim_events"


def create_claim(vault_id: str, nominee_id: str, data: dict[str, Any]) -> dict:
    client = require_client()
    payload = {**data, "vault_id": vault_id, "nominee_id": nominee_id}
    res = client.table(TABLE).insert(payload).execute()
    return (res.data or [{}])[0]


def get_claim(claim_id: str) -> Optional[dict]:
    client = require_client()
    res = client.table(TABLE).select("*").eq("id", claim_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def list_claims(vault_id: Optional[str] = None, nominee_id: Optional[str] = None) -> list[dict]:
    client = require_client()
    q = client.table(TABLE).select("*")
    if vault_id:
        q = q.eq("vault_id", vault_id)
    if nominee_id:
        q = q.eq("nominee_id", nominee_id)
    res = q.execute()
    return res.data or []


def update_claim(claim_id: str, patch: dict[str, Any]) -> Optional[dict]:
    client = require_client()
    patch = {k: v for k, v in patch.items() if v is not None}
    res = client.table(TABLE).update(patch).eq("id", claim_id).execute()
    rows = res.data or []
    return rows[0] if rows else get_claim(claim_id)


def add_claim_event(claim_id: str, status: str, note: Optional[str] = None, doc_hash: Optional[str] = None, tx_id: Optional[str] = None) -> dict:
    client = require_client()
    res = client.table(EVENTS_TABLE).insert(
        {"claim_id": claim_id, "status": status, "note": note, "doc_hash": doc_hash, "tx_id": tx_id}
    ).execute()
    return (res.data or [{}])[0]


def list_claim_events(claim_id: str) -> list[dict]:
    client = require_client()
    res = client.table(EVENTS_TABLE).select("*").eq("claim_id", claim_id).order("created_at").execute()
    return res.data or []
