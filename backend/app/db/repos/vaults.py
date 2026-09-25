from __future__ import annotations

from typing import Any, Optional

from app.db.repos.base import require_client

TABLE = "vaults"


def get_vault_by_owner(owner_id: str) -> Optional[dict]:
    client = require_client()
    res = client.table(TABLE).select("*").eq("owner_id", owner_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def get_vault(vault_id: str) -> Optional[dict]:
    client = require_client()
    res = client.table(TABLE).select("*").eq("id", vault_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def create_vault(owner_id: str, data: dict[str, Any]) -> dict:
    client = require_client()
    payload = {**data, "owner_id": owner_id}
    res = client.table(TABLE).insert(payload).execute()
    return (res.data or [{}])[0]


def update_vault(vault_id: str, patch: dict[str, Any]) -> Optional[dict]:
    client = require_client()
    patch = {k: v for k, v in patch.items() if v is not None}
    if not patch:
        return get_vault(vault_id)
    res = client.table(TABLE).update(patch).eq("id", vault_id).execute()
    rows = res.data or []
    return rows[0] if rows else get_vault(vault_id)


def list_vaults_for_state(state: str) -> list[dict]:
    client = require_client()
    res = client.table(TABLE).select("*").eq("state", state).execute()
    return res.data or []


def list_all_active_vaults() -> list[dict]:
    client = require_client()
    res = client.table(TABLE).select("*").in_("state", ["active", "challenge"]).execute()
    return res.data or []
