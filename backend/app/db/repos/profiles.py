from __future__ import annotations

from typing import Any, Optional

from app.db.repos.base import require_client


def get_profile(user_id: str) -> Optional[dict]:
    client = require_client()
    res = client.table("profiles").select("*").eq("id", user_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def update_profile(user_id: str, patch: dict[str, Any]) -> dict:
    client = require_client()
    patch = {k: v for k, v in patch.items() if v is not None}
    if not patch:
        return get_profile(user_id) or {"id": user_id}
    res = client.table("profiles").update(patch).eq("id", user_id).execute()
    rows = res.data or []
    return rows[0] if rows else (get_profile(user_id) or {"id": user_id})


def add_consent(user_id: str, purpose: str, version: str) -> dict:
    client = require_client()
    res = (
        client.table("consents")
        .insert({"user_id": user_id, "purpose": purpose, "version": version})
        .execute()
    )
    return (res.data or [{}])[0]
