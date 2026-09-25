from __future__ import annotations

from typing import Optional

from app.db.repos.base import require_client

TABLE = "institutions"


def get_institution(slug: str) -> Optional[dict]:
    client = require_client()
    res = client.table(TABLE).select("*").eq("slug", slug).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def list_institutions() -> list[dict]:
    client = require_client()
    res = client.table(TABLE).select("*").execute()
    return res.data or []
