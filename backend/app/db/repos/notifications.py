from __future__ import annotations

from typing import Any, Optional

from app.db.repos.base import require_client

TABLE = "notifications"


def record_notification(user_id: str, kind: str, payload: dict, error: Optional[str] = None) -> dict:
    client = require_client()
    res = client.table(TABLE).insert(
        {"user_id": user_id, "kind": kind, "payload": payload, "error": error}
    ).execute()
    return (res.data or [{}])[0]
