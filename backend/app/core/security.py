"""Auth: verifies Supabase-issued JWTs against the project's JWKS endpoint,
upserts a `profiles` row on first sight, and exposes per-vault role guards.
"""
from __future__ import annotations

import time
from typing import Any, Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.errors import ApiError
from app.core.logging import get_logger
from app.db.client import get_supabase

logger = get_logger(__name__)

_bearer = HTTPBearer(auto_error=False)

_JWKS_CACHE: dict[str, Any] = {"keys": None, "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 600  # 10 minutes


class CurrentUser:
    def __init__(self, id: str, email: Optional[str], claims: dict[str, Any]):
        self.id = id
        self.email = email
        self.claims = claims

    def __repr__(self) -> str:  # pragma: no cover
        return f"CurrentUser(id={self.id!r}, email={self.email!r})"


def _get_jwks() -> Optional[dict]:
    if not settings.SUPABASE_JWKS_URL:
        return None
    now = time.time()
    if _JWKS_CACHE["keys"] is not None and (now - _JWKS_CACHE["fetched_at"]) < _JWKS_TTL_SECONDS:
        return _JWKS_CACHE["keys"]
    try:
        import httpx

        resp = httpx.get(settings.SUPABASE_JWKS_URL, timeout=5.0)
        resp.raise_for_status()
        keys = resp.json()
        _JWKS_CACHE["keys"] = keys
        _JWKS_CACHE["fetched_at"] = now
        return keys
    except Exception:
        logger.warning("jwks_fetch_failed", url=settings.SUPABASE_JWKS_URL)
        return _JWKS_CACHE["keys"]


def _decode_jwt(token: str) -> dict[str, Any]:
    """Decode + verify a Supabase access token.

    Prefers JWKS (RS256/ES256, the modern Supabase default). Falls back to
    the legacy HS256 shared secret if SUPABASE_JWT_SECRET is set and JWKS
    verification isn't available/fails.
    """
    last_error: Optional[Exception] = None

    jwks = _get_jwks()
    if jwks:
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            matching = None
            for key in jwks.get("keys", []):
                if kid is None or key.get("kid") == kid:
                    matching = key
                    break
            if matching:
                public_key = jwt.PyJWK.from_json_string  # placeholder to avoid unused import warnings
                signing_key = jwt.PyJWK(matching).key
                claims = jwt.decode(
                    token,
                    key=signing_key,
                    algorithms=[matching.get("alg", "RS256")],
                    audience="authenticated",
                    options={"verify_aud": True},
                )
                return claims
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    if settings.SUPABASE_JWT_SECRET:
        try:
            claims = jwt.decode(
                token,
                key=settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_aud": True},
            )
            return claims
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    if last_error:
        raise last_error
    raise ApiError(
        code="auth_not_configured",
        title="Authentication not configured",
        detail="Neither SUPABASE_JWKS_URL nor SUPABASE_JWT_SECRET is configured on the server.",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def _upsert_profile(user_id: str, email: Optional[str], claims: dict[str, Any]) -> None:
    client = get_supabase()
    if client is None:
        return
    try:
        meta = claims.get("user_metadata", {}) or {}
        full_name = meta.get("full_name") or meta.get("name")
        client.table("profiles").upsert(
            {
                "id": user_id,
                "email": email,
                **({"full_name": full_name} if full_name else {}),
            },
            on_conflict="id",
        ).execute()
    except Exception:
        logger.warning("profile_upsert_failed", user_id=user_id)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> CurrentUser:
    if credentials is None or not credentials.credentials:
        raise ApiError(
            code="unauthorized",
            title="Unauthorized",
            detail="Missing Authorization: Bearer <jwt> header.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    token = credentials.credentials

    try:
        claims = _decode_jwt(token)
    except jwt.ExpiredSignatureError as exc:
        raise ApiError(
            code="token_expired",
            title="Unauthorized",
            detail="Access token has expired.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise ApiError(
            code="invalid_token",
            title="Unauthorized",
            detail=f"Could not verify access token: {exc}",
            status_code=status.HTTP_401_UNAUTHORIZED,
        ) from exc

    if claims.get("aud") != "authenticated":
        raise ApiError(
            code="invalid_audience",
            title="Unauthorized",
            detail="Token audience is not 'authenticated'.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    user_id = claims.get("sub")
    if not user_id:
        raise ApiError(
            code="invalid_token",
            title="Unauthorized",
            detail="Token has no subject (sub) claim.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    email = claims.get("email")
    _upsert_profile(user_id, email, claims)

    request.state.user_id = user_id
    return CurrentUser(id=user_id, email=email, claims=claims)


# --------------------------------------------------------------------------
# Per-vault role guards. Each returns a FastAPI dependency that expects a
# path parameter named `vault_id` on the route it's used on.
# --------------------------------------------------------------------------


def require_owner():
    async def _dep(vault_id: str, user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        client = get_supabase()
        if client is None:
            raise ApiError(
                "db_unavailable", "Service unavailable", "Database not configured.", status.HTTP_503_SERVICE_UNAVAILABLE
            )
        res = client.table("vaults").select("id,owner_id").eq("id", vault_id).limit(1).execute()
        rows = res.data or []
        if not rows or rows[0]["owner_id"] != user.id:
            raise ApiError(
                "forbidden_not_owner",
                "Forbidden",
                "You are not the owner of this vault.",
                status.HTTP_403_FORBIDDEN,
            )
        return user

    return _dep


def require_guardian():
    async def _dep(vault_id: str, user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        client = get_supabase()
        if client is None:
            raise ApiError(
                "db_unavailable", "Service unavailable", "Database not configured.", status.HTTP_503_SERVICE_UNAVAILABLE
            )
        res = (
            client.table("guardians")
            .select("id,user_id,status")
            .eq("vault_id", vault_id)
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            raise ApiError(
                "forbidden_not_guardian",
                "Forbidden",
                "You are not a guardian of this vault.",
                status.HTTP_403_FORBIDDEN,
            )
        return user

    return _dep


def require_nominee(released: bool = False):
    async def _dep(vault_id: str, user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        client = get_supabase()
        if client is None:
            raise ApiError(
                "db_unavailable", "Service unavailable", "Database not configured.", status.HTTP_503_SERVICE_UNAVAILABLE
            )
        res = (
            client.table("nominees")
            .select("id,user_id")
            .eq("vault_id", vault_id)
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            raise ApiError(
                "forbidden_not_nominee",
                "Forbidden",
                "You are not a nominee of this vault.",
                status.HTTP_403_FORBIDDEN,
            )
        if released:
            vres = client.table("vaults").select("state").eq("id", vault_id).limit(1).execute()
            vrows = vres.data or []
            if not vrows or vrows[0]["state"] != "released":
                raise ApiError(
                    "vault_not_released",
                    "Forbidden",
                    "This vault has not been released yet.",
                    status.HTTP_403_FORBIDDEN,
                )
        return user

    return _dep
