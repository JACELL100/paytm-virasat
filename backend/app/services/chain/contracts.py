"""Thin wrappers around the VirasatRegistry / NomineeCredential / ClaimLedger
contract calls described in Implementation_Plan.md section 10.

Each `build_*` function returns a `(w3, fees) -> tx_dict` closure suitable
for `Relayer.send(build_fn=...)`. Each `read_*` function is a plain view
call that returns None if the chain/contract isn't available.
"""
from __future__ import annotations

from typing import Any, Optional

from app.core.logging import get_logger
from app.services.chain.web3_client import get_contract, get_w3

logger = get_logger(__name__)


def _gas_tx(fees: dict, gas: int = 400_000) -> dict:
    return {"gas": gas, **fees}


def compute_guardians_hash(guardians: list[str]) -> bytes:
    """Must match the contract exactly: keccak256(abi.encode(address[])),
    i.e. abi-encoding a single dynamic array of addresses (VirasatRegistry.sol
    line 185)."""
    from eth_abi import encode
    from eth_utils import keccak

    return keccak(encode(["address[]"], [guardians]))


def compute_nominees_hash(nominees: list[str], shares_bps: list[int]) -> bytes:
    """Must match the contract exactly: keccak256(abi.encode(address[], uint16[]))
    (VirasatRegistry.sol line 186)."""
    from eth_abi import encode
    from eth_utils import keccak

    return keccak(encode(["address[]", "uint16[]"], [nominees, shares_bps]))


def build_create_vault_req_tuple(
    *,
    owner: str,
    manifest_hash: bytes,
    inactivity_period: int,
    challenge_period: int,
    threshold: int,
    guardians: list[str],
    nominees: list[str],
    shares_bps: list[int],
    nonce: int,
    deadline: int,
) -> tuple:
    """Builds the on-chain `CreateVaultReq` calldata tuple, in the exact field
    order VirasatRegistry.sol declares (owner, manifestHash, inactivityPeriod,
    challengePeriod, threshold, guardians, nominees, shareBps, nonce, deadline).
    This is a *different* shape from the EIP-712 signing message (which
    carries guardiansHash/nomineesHash commitments instead of the raw
    arrays) -- see eip712.build_create_vault."""
    return (
        owner,
        manifest_hash,
        inactivity_period,
        challenge_period,
        threshold,
        guardians,
        nominees,
        shares_bps,
        nonce,
        deadline,
    )


def build_create_vault(req_tuple: tuple, owner_sig: bytes):
    def _build(w3, fees):
        registry = get_contract("registry")
        fn = registry.functions.createVault(req_tuple, owner_sig)
        return {**fn.build_transaction(_gas_tx(fees, 800_000))}

    return _build


def read_nonce(owner_address: str) -> int:
    """VirasatRegistry keeps one nonce per signer, shared across
    createVault/updateManifest/setGuardians/setNominees/cancelRelease (it is
    NOT reset per-vault or per-action-type)."""
    registry = get_contract("registry")
    if registry is None:
        return 0
    try:
        return registry.functions.nonces(owner_address).call()
    except Exception:
        logger.warning("read_nonce_failed", owner=owner_address)
        return 0


def build_update_manifest(vault_id: int, new_hash: bytes, deadline: int, owner_sig: bytes):
    def _build(w3, fees):
        registry = get_contract("registry")
        fn = registry.functions.updateManifest(vault_id, new_hash, deadline, owner_sig)
        return {**fn.build_transaction(_gas_tx(fees))}

    return _build


def build_set_guardians(vault_id: int, guardians: list[str], threshold: int, deadline: int, owner_sig: bytes):
    def _build(w3, fees):
        registry = get_contract("registry")
        fn = registry.functions.setGuardians(vault_id, guardians, threshold, deadline, owner_sig)
        return {**fn.build_transaction(_gas_tx(fees))}

    return _build


def build_set_nominees(vault_id: int, nominees: list[str], shares_bps: list[int], deadline: int, owner_sig: bytes):
    def _build(w3, fees):
        registry = get_contract("registry")
        fn = registry.functions.setNominees(vault_id, nominees, shares_bps, deadline, owner_sig)
        return {**fn.build_transaction(_gas_tx(fees))}

    return _build


def build_cancel_release(vault_id: int, deadline: int, owner_sig: bytes):
    def _build(w3, fees):
        registry = get_contract("registry")
        fn = registry.functions.cancelRelease(vault_id, deadline, owner_sig)
        return {**fn.build_transaction(_gas_tx(fees))}

    return _build


def build_heartbeat_batch(vault_ids: list[int]):
    def _build(w3, fees):
        registry = get_contract("registry")
        fn = registry.functions.heartbeatBatch(vault_ids)
        return {**fn.build_transaction(_gas_tx(fees, 200_000 + 30_000 * len(vault_ids)))}

    return _build


def build_attest_death(vault_id: int, death_cert_hash: bytes, guardian: str, deadline: int, sig: bytes):
    def _build(w3, fees):
        registry = get_contract("registry")
        fn = registry.functions.attestDeath(vault_id, death_cert_hash, guardian, deadline, sig)
        return {**fn.build_transaction(_gas_tx(fees))}

    return _build


def build_finalize_release(vault_id: int):
    def _build(w3, fees):
        registry = get_contract("registry")
        fn = registry.functions.finalizeRelease(vault_id)
        return {**fn.build_transaction(_gas_tx(fees, 500_000))}

    return _build


def build_claim_log(claim_id: bytes, vault_id: int, status: int, doc_hash: bytes):
    def _build(w3, fees):
        ledger = get_contract("ledger")
        fn = ledger.functions.log(claim_id, vault_id, status, doc_hash)
        return {**fn.build_transaction(_gas_tx(fees, 150_000))}

    return _build


def read_vault(vault_id: int) -> Optional[dict]:
    registry = get_contract("registry")
    if registry is None:
        return None
    try:
        v = registry.functions.getVault(vault_id).call()
        # Struct tuple order matches Vault{} in section 10.1
        keys = [
            "owner",
            "manifestHash",
            "lastHeartbeat",
            "challengeEndsAt",
            "inactivityPeriod",
            "challengePeriod",
            "epoch",
            "threshold",
            "attestCount",
            "state",
            "deathCertHash",
        ]
        return dict(zip(keys, v))
    except Exception:
        logger.warning("read_vault_failed", vault_id=vault_id)
        return None


def read_nominees(vault_id: int) -> Optional[tuple[list[str], list[int]]]:
    registry = get_contract("registry")
    if registry is None:
        return None
    try:
        addrs, shares = registry.functions.getNominees(vault_id).call()
        return list(addrs), list(shares)
    except Exception:
        logger.warning("read_nominees_failed", vault_id=vault_id)
        return None


VAULT_STATE_NAMES = ["none", "active", "challenge", "released", "revoked"]
