from __future__ import annotations

from typing import Any, Optional

from app.db.repos.base import require_client

TABLE = "attestations"


def create_attestation(vault_id: str, guardian_id: str, data: dict[str, Any]) -> dict:
    client = require_client()
    res = client.table(TABLE).insert({**data, "vault_id": vault_id, "guardian_id": guardian_id}).execute()
    return (res.data or [{}])[0]


def list_attestations(vault_id: str) -> list[dict]:
    client = require_client()
    res = client.table(TABLE).select("*").eq("vault_id", vault_id).execute()
    return res.data or []
