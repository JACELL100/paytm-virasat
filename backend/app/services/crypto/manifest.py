"""Builds, seals and unseals the Legacy Vault manifest.

Per Implementation_Plan.md section 11:
    manifest.json --AES-256-GCM(DEK, AAD=vaultId||epoch)--> ciphertext -> Storage
    manifestHash = keccak256(ciphertext) -> on-chain
    DEK -> Shamir 2-of-3 -> escrow / nominee ("Legacy Key") / recovery shares
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.errors import ApiError
from app.core.logging import get_logger
from app.services.crypto import aes, shamir

logger = get_logger(__name__)


@dataclass
class SealedManifest:
    ciphertext: bytes  # nonce || ciphertext+tag
    manifest_hash_hex: str  # 0x-prefixed keccak256(ciphertext)
    escrow_share_enc: str  # Fernet token (store in vaults.escrow_share_enc)
    recovery_share_enc: str  # Fernet token (store in vaults.recovery_share_enc)
    nominee_share_b64: str  # the "Legacy Key" -- hand to the nominee, don't store server-side


def build_manifest(
    *,
    owner: dict[str, Any],
    assets: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    nominees: list[dict[str, Any]],
    note: Optional[str] = None,
) -> dict[str, Any]:
    """Assembles the plaintext manifest JSON described in section 11:
    assets (institution, product, masked+full refs, value, nominee info),
    document references, institution contacts, and an optional owner note.
    """
    return {
        "version": 1,
        "owner": {
            "full_name": owner.get("full_name"),
            "email": owner.get("email"),
            "phone": owner.get("phone"),
        },
        "assets": assets,
        "documents": documents,
        "nominees": nominees,
        "note": note,
    }


def keccak256_hex(data: bytes) -> str:
    from eth_utils import keccak

    return "0x" + keccak(data).hex()


def _fernet(key: Optional[str], name: str) -> Fernet:
    if not key:
        raise ApiError(
            code=f"{name}_not_configured",
            title="Service unavailable",
            detail=f"{name.upper()} is not configured on the server.",
            status_code=503,
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def seal_manifest(manifest: dict[str, Any], *, vault_id: str, epoch: int) -> SealedManifest:
    """Encrypts the manifest, hashes the ciphertext, and splits the DEK into
    the escrow/nominee/recovery shares."""
    dek = os.urandom(32)
    plaintext = json.dumps(manifest, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ciphertext = aes.seal(plaintext, dek, vault_id, epoch)
    manifest_hash_hex = keccak256_hex(ciphertext)

    shares = shamir.split_dek(dek)
    escrow_share, nominee_share, recovery_share = shares[0], shares[1], shares[2]

    escrow_fernet = _fernet(settings.ESCROW_KEY, "escrow_key")
    recovery_fernet = _fernet(settings.RECOVERY_KEY, "recovery_key")

    sealed = SealedManifest(
        ciphertext=ciphertext,
        manifest_hash_hex=manifest_hash_hex,
        escrow_share_enc=escrow_fernet.encrypt(escrow_share).decode("utf-8"),
        recovery_share_enc=recovery_fernet.encrypt(recovery_share).decode("utf-8"),
        nominee_share_b64=shamir.share_to_b64(nominee_share),
    )

    # Best-effort: zero the DEK reference (Python can't guarantee this, but we
    # at least drop all strong references immediately).
    dek = b"\x00" * len(dek)
    return sealed


def pack_escrow_column(*, escrow_share_enc: str, nominee_pending_share_b64: Optional[str]) -> str:
    """The `vaults.escrow_share_enc` column (per supabase/migrations/0001_init.sql)
    has no sibling column to stash the nominee's Shamir share until their
    invite is accepted (section 11: "Share 2 -> NOMINEE ... given at invite
    acceptance"). Rather than alter a schema owned by a different migration
    track, we pack a small JSON envelope into that same `text` column:
    {"escrow": "<fernet token of share0>", "nominee_pending": "<fernet token
    of share1, or null once every nominee has accepted>"}. `unpack_escrow_column`
    is the only other place that needs to know about this envelope."""
    payload = {"escrow": escrow_share_enc, "nominee_pending": None}
    if nominee_pending_share_b64:
        fernet = _fernet(settings.ESCROW_KEY, "escrow_key")
        payload["nominee_pending"] = fernet.encrypt(nominee_pending_share_b64.encode("utf-8")).decode("utf-8")
    return json.dumps(payload)


def unpack_escrow_column(raw: str) -> tuple[str, Optional[str]]:
    """Returns (escrow_share_enc, nominee_pending_share_b64_or_None). Falls
    back to treating `raw` as a bare legacy escrow token (no envelope) for
    forward/backward compatibility."""
    try:
        payload = json.loads(raw)
        escrow_share_enc = payload["escrow"]
        nominee_pending_enc = payload.get("nominee_pending")
        nominee_pending_b64 = None
        if nominee_pending_enc:
            fernet = _fernet(settings.ESCROW_KEY, "escrow_key")
            nominee_pending_b64 = fernet.decrypt(nominee_pending_enc.encode("utf-8")).decode("utf-8")
        return escrow_share_enc, nominee_pending_b64
    except (json.JSONDecodeError, KeyError, TypeError):
        return raw, None


def unseal_manifest(
    *,
    ciphertext: bytes,
    escrow_share_enc: str,
    nominee_share_b64: str,
    vault_id: str,
    epoch: int,
    expected_manifest_hash_hex: Optional[str] = None,
) -> dict[str, Any]:
    """Combines the escrow share + nominee ("Legacy Key") share to rebuild
    the DEK, decrypts the manifest, and verifies the ciphertext hash against
    the on-chain manifestHash if provided."""
    if expected_manifest_hash_hex:
        actual = keccak256_hex(ciphertext)
        if actual.lower() != expected_manifest_hash_hex.lower():
            raise ApiError(
                code="manifest_hash_mismatch",
                title="Integrity check failed",
                detail="Decrypted manifest ciphertext hash does not match the on-chain manifestHash.",
                status_code=409,
            )

    escrow_fernet = _fernet(settings.ESCROW_KEY, "escrow_key")
    try:
        escrow_share = escrow_fernet.decrypt(escrow_share_enc.encode("utf-8"))
    except InvalidToken as exc:
        raise ApiError("escrow_decrypt_failed", "Internal server error", "Could not decrypt escrow share.", 500) from exc

    nominee_share = shamir.share_from_b64(nominee_share_b64)

    dek = shamir.combine_dek([escrow_share, nominee_share])
    try:
        plaintext = aes.unseal(ciphertext, dek, vault_id, epoch)
    finally:
        dek = b"\x00" * len(dek)

    return json.loads(plaintext.decode("utf-8"))
