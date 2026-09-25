"""AES-256-GCM seal/unseal + tamper detection (section 17 must-cover case)."""
from __future__ import annotations

import os

import pytest
from cryptography.exceptions import InvalidTag

from app.services.crypto import aes


def test_seal_unseal_roundtrip():
    dek = os.urandom(32)
    plaintext = b'{"hello": "world"}'
    blob = aes.seal(plaintext, dek, vault_id="vault-123", epoch=0)
    recovered = aes.unseal(blob, dek, vault_id="vault-123", epoch=0)
    assert recovered == plaintext


def test_tampered_ciphertext_raises_invalid_tag():
    dek = os.urandom(32)
    plaintext = b"sensitive manifest data"
    blob = aes.seal(plaintext, dek, vault_id="vault-1", epoch=0)
    tampered = bytearray(blob)
    tampered[-1] ^= 0xFF  # flip a bit in the tag/ciphertext
    with pytest.raises(InvalidTag):
        aes.unseal(bytes(tampered), dek, vault_id="vault-1", epoch=0)


def test_wrong_aad_fails():
    """AAD = vaultId||epoch must match exactly, or GCM authentication fails."""
    dek = os.urandom(32)
    plaintext = b"data"
    blob = aes.seal(plaintext, dek, vault_id="vault-1", epoch=0)
    with pytest.raises(InvalidTag):
        aes.unseal(blob, dek, vault_id="vault-1", epoch=1)  # wrong epoch


def test_wrong_key_fails():
    dek1 = os.urandom(32)
    dek2 = os.urandom(32)
    blob = aes.seal(b"data", dek1, vault_id="v", epoch=0)
    with pytest.raises(InvalidTag):
        aes.unseal(blob, dek2, vault_id="v", epoch=0)


def test_dek_must_be_32_bytes():
    with pytest.raises(ValueError):
        aes.seal(b"x", os.urandom(16), vault_id="v", epoch=0)
