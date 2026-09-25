from __future__ import annotations

from typing import Any, Optional

from app.db.repos.base import require_client

TABLE = "discovery_suggestions"


def create_suggestion(owner_id: str, source: str, payload: dict) -> dict:
    client = require_client()
    res = client.table(TABLE).insert(
        {"owner_id": owner_id, "source": source, "payload": payload, "status": "pending"}
    ).execute()
    return (res.data or [{}])[0]


def get_suggestion(owner_id: str, suggestion_id: str) -> Optional[dict]:
    client = require_client()
    res = (
        client.table(TABLE)
        .select("*")
        .eq("owner_id", owner_id)
        .eq("id", suggestion_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def set_suggestion_status(suggestion_id: str, status: str) -> Optional[dict]:
    client = require_client()
    res = client.table(TABLE).update({"status": status}).eq("id", suggestion_id).execute()
    rows = res.data or []
    return rows[0] if rows else None


def list_suggestions(owner_id: str, status: Optional[str] = None) -> list[dict]:
    client = require_client()
    q = client.table(TABLE).select("*").eq("owner_id", owner_id)
    if status:
        q = q.eq("status", status)
    res = q.order("created_at", desc=True).execute()
    return res.data or []
