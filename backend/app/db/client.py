"""Supabase client (service-role key, server-only).

This key must NEVER reach the browser. If SUPABASE_URL /
SUPABASE_SERVICE_ROLE_KEY are missing or placeholders (e.g. a dev sandbox
with no real Supabase project yet), `get_supabase()` returns None and logs a
warning instead of raising, so the app can still boot. Every repo function
must check for None and raise a clear ApiError(503) rather than crash.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache
def get_supabase() -> Optional["Client"]:  # noqa: F821
    if not settings.supabase_configured:
        logger.warning(
            "supabase_not_configured",
            hint="SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing -- DB calls will be stubbed.",
        )
        return None
    try:
        from supabase import Client, create_client

        client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        return client
    except Exception:  # pragma: no cover - defensive
        logger.exception("supabase_client_init_failed")
        return None


def is_db_available() -> bool:
    return get_supabase() is not None
