"""EIP-712 typed-data builders for the VirasatRegistry actions, per
Implementation_Plan.md section 10.1.

Domain: name="PaytmVirasat", version="1", chainId=11155111 (or CHAIN_ID),
verifyingContract=<registry address>.
"""
from __future__ import annotations

from typing import Any, Optional

from eth_account import Account
from eth_account.messages import encode_typed_data

from app.core.config import settings

DOMAIN_NAME = "PaytmVirasat"
DOMAIN_VERSION = "1"


def _domain(verifying_contract: str) -> dict[str, Any]:
    return {
        "name": DOMAIN_NAME,
        "version": DOMAIN_VERSION,
        "chainId": settings.CHAIN_ID,
        "verifyingContract": verifying_contract,
    }


def build_create_vault(
    *,
    verifying_contract: str,
    owner: str,
    manifest_hash: bytes,
    inactivity_period: int,
    challenge_period: int,
    threshold: int,
    guardians_hash: bytes,
    nominees_hash: bytes,
    nonce: int,
    deadline: int,
) -> dict[str, Any]:
    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "CreateVault": [
                {"name": "owner", "type": "address"},
                {"name": "manifestHash", "type": "bytes32"},
                {"name": "inactivityPeriod", "type": "uint32"},
                {"name": "challengePeriod", "type": "uint32"},
                {"name": "threshold", "type": "uint8"},
                {"name": "guardiansHash", "type": "bytes32"},
                {"name": "nomineesHash", "type": "bytes32"},
                {"name": "nonce", "type": "uint256"},
                {"name": "deadline", "type": "uint256"},
            ],
        },
        "primaryType": "CreateVault",
        "domain": _domain(verifying_contract),
        "message": {
            "owner": owner,
            "manifestHash": manifest_hash,
            "inactivityPeriod": inactivity_period,
            "challengePeriod": challenge_period,
            "threshold": threshold,
            "guardiansHash": guardians_hash,
            "nomineesHash": nominees_hash,
            "nonce": nonce,
            "deadline": deadline,
        },
    }


def build_update_manifest(
    *, verifying_contract: str, vault_id: int, manifest_hash: bytes, nonce: int, deadline: int
) -> dict[str, Any]:
    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "UpdateManifest": [
                {"name": "vaultId", "type": "uint256"},
                {"name": "manifestHash", "type": "bytes32"},
                {"name": "nonce", "type": "uint256"},
                {"name": "deadline", "type": "uint256"},
            ],
        },
        "primaryType": "UpdateManifest",
        "domain": _domain(verifying_contract),
        "message": {
            "vaultId": vault_id,
            "manifestHash": manifest_hash,
            "nonce": nonce,
            "deadline": deadline,
        },
    }


def build_cancel_release(
    *, verifying_contract: str, vault_id: int, epoch: int, nonce: int, deadline: int
) -> dict[str, Any]:
    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "CancelRelease": [
                {"name": "vaultId", "type": "uint256"},
                {"name": "epoch", "type": "uint16"},
                {"name": "nonce", "type": "uint256"},
                {"name": "deadline", "type": "uint256"},
            ],
        },
        "primaryType": "CancelRelease",
        "domain": _domain(verifying_contract),
        "message": {
            "vaultId": vault_id,
            "epoch": epoch,
            "nonce": nonce,
            "deadline": deadline,
        },
    }


def build_set_guardians(
    *, verifying_contract: str, vault_id: int, guardians_hash: bytes, threshold: int, nonce: int, deadline: int
) -> dict[str, Any]:
    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "SetGuardians": [
                {"name": "vaultId", "type": "uint256"},
                {"name": "guardiansHash", "type": "bytes32"},
                {"name": "threshold", "type": "uint8"},
                {"name": "nonce", "type": "uint256"},
                {"name": "deadline", "type": "uint256"},
            ],
        },
        "primaryType": "SetGuardians",
        "domain": _domain(verifying_contract),
        "message": {
            "vaultId": vault_id,
            "guardiansHash": guardians_hash,
            "threshold": threshold,
            "nonce": nonce,
            "deadline": deadline,
        },
    }


def build_set_nominees(
    *, verifying_contract: str, vault_id: int, nominees_hash: bytes, nonce: int, deadline: int
) -> dict[str, Any]:
    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "SetNominees": [
                {"name": "vaultId", "type": "uint256"},
                {"name": "nomineesHash", "type": "bytes32"},
                {"name": "nonce", "type": "uint256"},
                {"name": "deadline", "type": "uint256"},
            ],
        },
        "primaryType": "SetNominees",
        "domain": _domain(verifying_contract),
        "message": {
            "vaultId": vault_id,
            "nomineesHash": nominees_hash,
            "nonce": nonce,
            "deadline": deadline,
        },
    }


def build_attest_death(
    *, verifying_contract: str, vault_id: int, death_cert_hash: bytes, epoch: int, deadline: int
) -> dict[str, Any]:
    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "AttestDeath": [
                {"name": "vaultId", "type": "uint256"},
                {"name": "deathCertHash", "type": "bytes32"},
                {"name": "epoch", "type": "uint16"},
                {"name": "deadline", "type": "uint256"},
            ],
        },
        "primaryType": "AttestDeath",
        "domain": _domain(verifying_contract),
        "message": {
            "vaultId": vault_id,
            "deathCertHash": death_cert_hash,
            "epoch": epoch,
            "deadline": deadline,
        },
    }


def sign_typed_data(private_key_hex: str, full_message: dict[str, Any]) -> str:
    """Signs an EIP-712 typed-data message with a raw private key.
    Returns the 0x-prefixed 65-byte signature hex."""
    signable = encode_typed_data(full_message=full_message)
    signed = Account.sign_message(signable, private_key=private_key_hex)
    return signed.signature.hex() if isinstance(signed.signature, (bytes, bytearray)) else signed.signature
