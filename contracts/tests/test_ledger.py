"""Tests for ClaimLedger: relayer-gated, event-only claim tracking."""

from __future__ import annotations

import pytest
from eth_tester.exceptions import TransactionFailed
from eth_utils import keccak

from conftest import assert_custom_error


def test_only_relayer_can_log(deployment, accounts):
    claim_id = keccak(text="claim-1")
    with pytest.raises(TransactionFailed) as exc:
        deployment.ledger.functions.log(claim_id, 1, 3, b"\x00" * 32).transact({"from": accounts.stranger})
    assert_custom_error(exc, "NotRelayer()")


def test_relayer_log_emits_event(w3, deployment, accounts):
    claim_id = keccak(text="claim-1")
    doc_hash = keccak(text="doc-1")
    tx = deployment.ledger.functions.log(claim_id, 42, 3, doc_hash).transact({"from": accounts.relayer})
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    events = deployment.ledger.events.ClaimEvent().process_receipt(receipt)
    assert len(events) == 1
    args = events[0]["args"]
    assert args["claimId"] == claim_id
    assert args["vaultId"] == 42
    assert args["status"] == 3
    assert args["docHash"] == doc_hash
    assert args["at"] > 0


def test_owner_can_update_relayer(deployment, accounts):
    deployment.ledger.functions.setRelayer(accounts.stranger).transact({"from": accounts.deployer})
    assert deployment.ledger.functions.relayer().call() == accounts.stranger

    claim_id = keccak(text="claim-2")
    # Old relayer no longer works.
    with pytest.raises(TransactionFailed) as exc:
        deployment.ledger.functions.log(claim_id, 1, 1, b"\x00" * 32).transact({"from": accounts.relayer})
    assert_custom_error(exc, "NotRelayer()")

    # New relayer works.
    deployment.ledger.functions.log(claim_id, 1, 1, b"\x00" * 32).transact({"from": accounts.stranger})


def test_non_owner_cannot_update_relayer(deployment, accounts):
    with pytest.raises(TransactionFailed):
        deployment.ledger.functions.setRelayer(accounts.stranger).transact({"from": accounts.stranger})
