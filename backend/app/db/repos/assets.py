from __future__ import annotations

from typing import Any, Optional

from app.db.repos.base import require_client

TABLE = "assets"


def list_assets(owner_id: str, type_filter: Optional[str] = None) -> list[dict]:
    client = require_client()
    q = client.table(TABLE).select("*").eq("owner_id", owner_id)
    if type_filter:
        q = q.eq("type", type_filter)
    res = q.order("created_at", desc=True).execute()
    return res.data or []


def get_asset(owner_id: str, asset_id: str) -> Optional[dict]:
    client = require_client()
    res = client.table(TABLE).select("*").eq("owner_id", owner_id).eq("id", asset_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def create_asset(owner_id: str, data: dict[str, Any]) -> dict:
    client = require_client()
    payload = {**data, "owner_id": owner_id}
    res = client.table(TABLE).insert(payload).execute()
    return (res.data or [{}])[0]


def update_asset(owner_id: str, asset_id: str, patch: dict[str, Any]) -> Optional[dict]:
    client = require_client()
    patch = {k: v for k, v in patch.items() if v is not None}
    if not patch:
        return get_asset(owner_id, asset_id)
    res = client.table(TABLE).update(patch).eq("owner_id", owner_id).eq("id", asset_id).execute()
    rows = res.data or []
    return rows[0] if rows else get_asset(owner_id, asset_id)


def delete_asset(owner_id: str, asset_id: str) -> bool:
    client = require_client()
    res = client.table(TABLE).delete().eq("owner_id", owner_id).eq("id", asset_id).execute()
    return bool(res.data)
