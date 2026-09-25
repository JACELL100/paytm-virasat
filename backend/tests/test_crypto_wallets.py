from __future__ import annotations

import pytest

from app.core.config import settings
from app.services.crypto import wallets as wallet_service

pytestmark = pytest.mark.skipif(not settings.WALLET_ENC_KEY, reason="WALLET_ENC_KEY not configured.")


def test_create_wallet_returns_valid_address_and_encrypted_key():
    wallet = wallet_service.create_wallet()
    assert wallet.address.startswith("0x")
    assert len(wallet.address) == 42
    assert wallet.encrypted_private_key
    # ciphertext should not contain the plaintext hex key anywhere obvious
    assert "0x" not in wallet.encrypted_private_key or wallet.encrypted_private_key.count("0x") == 0


def test_decrypt_private_key_roundtrip():
    wallet = wallet_service.create_wallet()
    decrypted = wallet_service.decrypt_private_key(wallet.encrypted_private_key)
    assert decrypted.startswith("0x")
    assert len(decrypted) == 66  # 0x + 64 hex chars


def test_two_wallets_are_different():
    w1 = wallet_service.create_wallet()
    w2 = wallet_service.create_wallet()
    assert w1.address != w2.address
