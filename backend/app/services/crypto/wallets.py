"""Custodial EOA wallets.

Each user (owner, nominee, guardian) gets a server-generated EOA so they can
be a distinct on-chain signer without ever touching a real wallet. The
private key is encrypted at rest with Fernet(WALLET_ENC_KEY) and only ever
decrypted in memory, right before signing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from eth_account import Account

from app.core.config import settings
from app.core.errors import ApiError
from app.core.logging import get_logger

logger = get_logger(__name__)

Account.enable_unaudited_hdwallet_features()


@dataclass
class CustodialWallet:
    address: str
    encrypted_private_key: str  # Fernet token, str (safe to store in a text/jsonb column)


def _fernet() -> Fernet:
    if not settings.WALLET_ENC_KEY:
        raise ApiError(
            code="wallet_enc_not_configured",
            title="Service unavailable",
            detail="WALLET_ENC_KEY is not configured on the server.",
            status_code=503,
        )
    return Fernet(settings.WALLET_ENC_KEY.encode() if isinstance(settings.WALLET_ENC_KEY, str) else settings.WALLET_ENC_KEY)


def create_wallet() -> CustodialWallet:
    acct = Account.create()
    key_hex = acct.key.hex()
    if not key_hex.startswith("0x"):
        key_hex = "0x" + key_hex
    encrypted = _fernet().encrypt(key_hex.encode("utf-8")).decode("utf-8")
    return CustodialWallet(address=acct.address, encrypted_private_key=encrypted)


def decrypt_private_key(encrypted_private_key: str) -> str:
    try:
        raw = _fernet().decrypt(encrypted_private_key.encode("utf-8"))
    except InvalidToken as exc:
        raise ApiError(
            code="wallet_decrypt_failed",
            title="Internal server error",
            detail="Could not decrypt custodial wallet key.",
            status_code=500,
        ) from exc
    return raw.decode("utf-8")


def sign_message_hash(encrypted_private_key: str, message_hash: bytes) -> bytes:
    """Signs a pre-hashed EIP-712 digest (from eth_account.messages.encode_typed_data)."""
    from eth_account._utils.signing import sign_message_hash as _sign_hash
    from eth_keys import keys

    private_key_hex = decrypt_private_key(encrypted_private_key)
    pk = keys.PrivateKey(bytes.fromhex(private_key_hex.removeprefix("0x")))
    _, _, _, signature_bytes = _sign_hash(pk, message_hash)
    return signature_bytes
