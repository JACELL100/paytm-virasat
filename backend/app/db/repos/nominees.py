from __future__ import annotations

from typing import Any, Optional

from app.db.repos.base import require_client

TABLE = "nominees"


def list_nominees(vault_id: str) -> list[dict]:
    client = require_client()
    res = client.table(TABLE).select("*").eq("vault_id", vault_id).execute()
    return res.data or []


def get_nominee(nominee_id: str) -> Optional[dict]:
    client = require_client()
    res = client.table(TABLE).select("*").eq("id", nominee_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def get_nominee_by_token_hash(token_hash: str) -> Optional[dict]:
    client = require_client()
    res = client.table(TABLE).select("*").eq("invite_token_hash", token_hash).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def create_nominee(vault_id: str, data: dict[str, Any]) -> dict:
    client = require_client()
    res = client.table(TABLE).insert({**data, "vault_id": vault_id}).execute()
    return (res.data or [{}])[0]


def update_nominee(nominee_id: str, patch: dict[str, Any]) -> Optional[dict]:
    client = require_client()
    patch = {k: v for k, v in patch.items() if v is not None}
    res = client.table(TABLE).update(patch).eq("id", nominee_id).execute()
    rows = res.data or []
    return rows[0] if rows else get_nominee(nominee_id)


def list_vaults_for_nominee_user(user_id: str) -> list[dict]:
    client = require_client()
    res = client.table(TABLE).select("*, vaults(*)").eq("user_id", user_id).execute()
    return res.data or []
