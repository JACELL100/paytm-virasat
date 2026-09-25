from __future__ import annotations

from typing import Any, Optional

from app.db.repos.base import require_client

TABLE = "documents"


def create_document(owner_id: str, data: dict[str, Any]) -> dict:
    client = require_client()
    res = client.table(TABLE).insert({**data, "owner_id": owner_id}).execute()
    return (res.data or [{}])[0]


def get_document(owner_id: str, document_id: str) -> Optional[dict]:
    client = require_client()
    res = client.table(TABLE).select("*").eq("owner_id", owner_id).eq("id", document_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def update_document(document_id: str, patch: dict[str, Any]) -> Optional[dict]:
    client = require_client()
    patch = {k: v for k, v in patch.items() if v is not None}
    res = client.table(TABLE).update(patch).eq("id", document_id).execute()
    rows = res.data or []
    return rows[0] if rows else None


def list_documents(owner_id: str, asset_id: Optional[str] = None) -> list[dict]:
    client = require_client()
    q = client.table(TABLE).select("*").eq("owner_id", owner_id)
    if asset_id:
        q = q.eq("asset_id", asset_id)
    res = q.execute()
    return res.data or []
