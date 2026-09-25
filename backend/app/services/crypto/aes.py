"""AES-256-GCM helpers for sealing/unsealing the manifest.

Per Implementation_Plan.md section 11:
    manifest.json --AES-256-GCM(DEK, 96-bit nonce, AAD = vaultId||epoch)--> ciphertext
    manifestHash = keccak256(ciphertext)

The ciphertext blob we store/return is: nonce (12 bytes) || ciphertext_with_tag.
`aesgcm.encrypt`/`decrypt` from the `cryptography` package already appends/
strips the 16-byte GCM tag, so callers just need the nonce alongside it.
"""
from __future__ import annotations

import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_SIZE = 12  # 96 bits, per spec


def build_aad(vault_id: str, epoch: int) -> bytes:
    """AAD = vaultId || epoch, as specified in section 11."""
    return f"{vault_id}|{epoch}".encode("utf-8")


def seal(plaintext: bytes, dek: bytes, vault_id: str, epoch: int) -> bytes:
    """Encrypts `plaintext` with AES-256-GCM. Returns nonce || ciphertext(+tag)."""
    if len(dek) != 32:
        raise ValueError("DEK must be 32 bytes (AES-256).")
    aesgcm = AESGCM(dek)
    nonce = os.urandom(NONCE_SIZE)
    aad = build_aad(vault_id, epoch)
    ct = aesgcm.encrypt(nonce, plaintext, aad)
    return nonce + ct


def unseal(blob: bytes, dek: bytes, vault_id: str, epoch: int) -> bytes:
    """Decrypts a blob produced by `seal`. Raises InvalidTag on tamper/wrong key/AAD."""
    if len(dek) != 32:
        raise ValueError("DEK must be 32 bytes (AES-256).")
    if len(blob) < NONCE_SIZE:
        raise ValueError("Ciphertext blob too short to contain a nonce.")
    nonce, ct = blob[:NONCE_SIZE], blob[NONCE_SIZE:]
    aesgcm = AESGCM(dek)
    aad = build_aad(vault_id, epoch)
    return aesgcm.decrypt(nonce, ct, aad)


__all__ = ["seal", "unseal", "build_aad", "InvalidTag", "NONCE_SIZE"]
