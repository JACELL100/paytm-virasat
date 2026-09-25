from __future__ import annotations

from typing import Any, Optional

from app.db.repos.base import require_client

TABLE = "guardians"


def list_guardians(vault_id: str) -> list[dict]:
    client = require_client()
    res = client.table(TABLE).select("*").eq("vault_id", vault_id).execute()
    return res.data or []


def get_guardian(guardian_id: str) -> Optional[dict]:
    client = require_client()
    res = client.table(TABLE).select("*").eq("id", guardian_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def get_guardian_by_token_hash(token_hash: str) -> Optional[dict]:
    client = require_client()
    res = client.table(TABLE).select("*").eq("invite_token_hash", token_hash).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def create_guardian(vault_id: str, data: dict[str, Any]) -> dict:
    client = require_client()
    res = client.table(TABLE).insert({**data, "vault_id": vault_id}).execute()
    return (res.data or [{}])[0]


def update_guardian(guardian_id: str, patch: dict[str, Any]) -> Optional[dict]:
    client = require_client()
    patch = {k: v for k, v in patch.items() if v is not None}
    res = client.table(TABLE).update(patch).eq("id", guardian_id).execute()
    rows = res.data or []
    return rows[0] if rows else get_guardian(guardian_id)


def list_vaults_for_guardian_user(user_id: str) -> list[dict]:
    client = require_client()
    res = client.table(TABLE).select("*, vaults(*)").eq("user_id", user_id).execute()
    return res.data or []
