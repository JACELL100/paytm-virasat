from __future__ import annotations

from typing import Any, Optional

from app.db.repos.base import require_client

TABLE = "activity_events"


def record_activity(user_id: str, kind: str, source: str = "app", meta: Optional[dict] = None) -> dict:
    client = require_client()
    payload: dict[str, Any] = {"user_id": user_id, "kind": kind, "source": source}
    res = client.table(TABLE).insert(payload).execute()
    return (res.data or [{}])[0]


def last_activity_at(user_id: str) -> Optional[str]:
    client = require_client()
    res = (
        client.table(TABLE)
        .select("occurred_at")
        .eq("user_id", user_id)
        .order("occurred_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0]["occurred_at"] if rows else None
