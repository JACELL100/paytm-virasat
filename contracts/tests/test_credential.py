"""Tests for NomineeCredential: soulbound minting, transfer revert, and the
on-chain tokenURI (no personal data, valid Base64 JSON + inline SVG)."""

from __future__ import annotations

import base64
import json

import pytest
from eth_tester.exceptions import TransactionFailed

from conftest import MIN_PERIOD, advance_time, assert_custom_error

ERC5192_INTERFACE_ID = "0xb45a3c0e"


def test_only_registry_can_mint(deployment, accounts):
    with pytest.raises(TransactionFailed) as exc:
        deployment.credential.functions.mint(accounts.nominee1.address, 1, 6000).transact(
            {"from": accounts.stranger}
        )
    assert_custom_error(exc, "NotRegistry()")


def _mint_via_registry(w3, tester, deployment, accounts, signer, create_default_vault):
    """Drive a vault all the way through inactivity -> 2-of-3 attestation ->
    challenge -> finalize, so the registry mints real credentials to
    nominee1 (60%) and nominee2 (40%)."""
    vault_id = create_default_vault(threshold=2, challenge_period=MIN_PERIOD)
    v = deployment.registry.functions.getVault(vault_id).call()
    advance_time(w3, tester, v[4] + 1)  # past inactivityPeriod

    death_hash = b"\x11" * 32
    for guardian in (accounts.guardian1, accounts.guardian2):
        epoch = deployment.registry.functions.getVault(vault_id).call()[6]
        deadline = 9999999999
        sig = signer.attest_death(
            guardian, vault_id=vault_id, death_cert_hash=death_hash, epoch=epoch, deadline=deadline
        )
        deployment.registry.functions.attestDeath(vault_id, death_hash, guardian.address, deadline, sig).transact(
            {"from": accounts.relayer}
        )

    advance_time(w3, tester, MIN_PERIOD + 1)  # past challengePeriod
    deployment.registry.functions.finalizeRelease(vault_id).transact({"from": accounts.stranger})
    return vault_id


def _fund(w3, accounts, address, amount_wei=10**18):
    """Nominee/guardian/owner accounts are custodial keys that normally only
    ever *sign* -- the relayer submits every transaction on their behalf. To
    prove the soulbound revert fires even for a direct call "as" the token
    owner, give that address enough SepoliaETH-equivalent test balance to pay
    gas for the one transaction it sends here."""
    w3.eth.send_transaction({"from": accounts.deployer, "to": address, "value": amount_wei})


def test_soulbound_transfer_reverts(w3, tester, deployment, accounts, signer, create_default_vault):
    _mint_via_registry(w3, tester, deployment, accounts, signer, create_default_vault)

    owner = accounts.nominee1.address
    assert deployment.credential.functions.ownerOf(1).call() == owner
    _fund(w3, accounts, owner)

    with pytest.raises(TransactionFailed) as exc:
        deployment.credential.functions.transferFrom(owner, accounts.nominee2.address, 1).transact({"from": owner})
    assert_custom_error(exc, "TransfersDisabled()")


def test_soulbound_approve_reverts(w3, tester, deployment, accounts, signer, create_default_vault):
    _mint_via_registry(w3, tester, deployment, accounts, signer, create_default_vault)
    owner = accounts.nominee1.address
    _fund(w3, accounts, owner)
    with pytest.raises(TransactionFailed) as exc:
        deployment.credential.functions.approve(accounts.nominee2.address, 1).transact({"from": owner})
    assert_custom_error(exc, "TransfersDisabled()")


def test_locked_returns_true(w3, tester, deployment, accounts, signer, create_default_vault):
    _mint_via_registry(w3, tester, deployment, accounts, signer, create_default_vault)
    assert deployment.credential.functions.locked(1).call() is True


def test_supports_erc5192_interface(deployment):
    assert deployment.credential.functions.supportsInterface(ERC5192_INTERFACE_ID).call() is True


def test_token_uri_is_valid_base64_json_with_no_pii(w3, tester, deployment, accounts, signer, create_default_vault):
    vault_id = _mint_via_registry(w3, tester, deployment, accounts, signer, create_default_vault)

    uri = deployment.credential.functions.tokenURI(1).call()
    assert uri.startswith("data:application/json;base64,")
    b64 = uri.split(",", 1)[1]
    decoded = json.loads(base64.b64decode(b64))

    assert decoded["vaultId"] == vault_id
    assert decoded["shareBps"] == 6000
    assert "releasedAt" in decoded
    assert decoded["image"].startswith("data:image/svg+xml;base64,")

    # No personal data: only vaultId / shareBps / releasedAt / name / description / image.
    allowed_keys = {"name", "description", "attributes", "vaultId", "shareBps", "releasedAt", "image"}
    assert set(decoded.keys()) <= allowed_keys

    svg_b64 = decoded["image"].split(",", 1)[1]
    svg = base64.b64decode(svg_b64).decode()
    assert svg.startswith("<svg")
    assert "#00BAF2" in svg  # brand cyan gradient stop present
