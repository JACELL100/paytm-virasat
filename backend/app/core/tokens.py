"""Random invite tokens: 32 random bytes, stored hashed, single-use.
Per Implementation_Plan.md section 14 (Abuse)."""
from __future__ import annotations

import hashlib
import secrets


def generate_invite_token() -> tuple[str, str]:
    """Returns (raw_token_urlsafe, sha256_hash_hex). Only the hash is stored;
    the raw token is embedded in the invite link/email and never persisted."""
    raw = secrets.token_urlsafe(32)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return raw, digest


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
