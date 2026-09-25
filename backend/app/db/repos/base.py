"""Shared helpers for repo modules.

Every repo function should call `require_client()` first so a missing/
unconfigured Supabase project surfaces as a clean 503 ApiError instead of an
AttributeError on None.
"""
from __future__ import annotations

from fastapi import status

from app.core.errors import ApiError
from app.db.client import get_supabase


def require_client():
    client = get_supabase()
    if client is None:
        raise ApiError(
            code="db_unavailable",
            title="Service unavailable",
            detail="Supabase is not configured on this server (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY).",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return client
