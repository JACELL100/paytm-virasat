"""slowapi rate limiting.

Per Implementation_Plan.md section 8.1: AI endpoints 10/min/user, uploads
20/min/user. We key by the authenticated user id when available (set into
request.state.user_id by get_current_user), falling back to remote IP for
unauthenticated/public routes.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import settings


def _rate_limit_key(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key, default_limits=[])

AI_RATE_LIMIT = settings.RATE_LIMIT_AI
UPLOAD_RATE_LIMIT = settings.RATE_LIMIT_UPLOAD
