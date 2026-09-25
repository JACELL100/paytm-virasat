"""Safety-property tests for VirasatRegistry, per Implementation_Plan.md §10.1
"Safety properties to test" and §17's contracts test-coverage checklist.
"""

from __future__ import annotations

import pytest
from eth_tester.exceptions import TransactionFailed
from eth_utils import keccak

from conftest import MIN_PERIOD, advance_time, assert_custom_error, far_future_deadline

State_ACTIVE = 1
State_CHALLENGE = 2
State_RELEASED = 3


def _vault(deployment, vault_id):
    return deployment.registry.functions.getVault(vault_id).call()


def attest(deployment, accounts, signer, vault_id, guardian_account, death_hash, *, epoch=None, deadline=None):
    v = _vault(deployment, vault_id)
    epoch = v[6] if epoch is None else epoch
    deadline = deadline or far_future_deadline()
    sig = signer.attest_death(
        guardian_account, vault_id=vault_id, death_cert_hash=death_hash, epoch=epoch, deadline=deadline
    )
    return deployment.registry.functions.attestDeath(
        vault_id, death_hash, guardian_account.address, deadline, sig
    ).transact({"from": accounts.relayer})


def make_inactive(w3, tester, deployment, vault_id):
    """Advance the chain clock past the vault's inactivityPeriod."""
    v = _vault(deployment, vault_id)
    inactivity_period = v[4]
    advance_time(w3, tester, inactivity_period + 1)


# ---------------------------------------------------------------------------
# Inactivity gate
# ---------------------------------------------------------------------------


def test_attest_before_inactivity_reverts(w3, deployment, accounts, signer, create_default_vault):
    vault_id = create_default_vault()
    death_hash = keccak(text="death-cert-1")
    with pytest.raises(TransactionFailed) as exc:
        attest(deployment, accounts, signer, vault_id, accounts.guardian1, death_hash)
    assert_custom_error(exc, "OwnerStillActive()")


def test_attest_after_inactivity_succeeds(w3, tester, deployment, accounts, signer, create_default_vault):
    vault_id = create_default_vault()
    make_inactive(w3, tester, deployment, vault_id)
    death_hash = keccak(text="death-cert-1")
    attest(deployment, accounts, signer, vault_id, accounts.guardian1, death_hash)
    v = _vault(deployment, vault_id)
    assert v[8] == 1  # attestCount


def test_isInactive_view(w3, tester, deployment, create_default_vault):
    vault_id = create_default_vault()
    assert deployment.registry.functions.isInactive(vault_id).call() is False
    make_inactive(w3, tester, deployment, vault_id)
    assert deployment.registry.functions.isInactive(vault_id).call() is True


# ---------------------------------------------------------------------------
# M-of-N threshold gate
# ---------------------------------------------------------------------------


def test_single_guardian_does_not_start_challenge(w3, tester, deployment, accounts, signer, create_default_vault):
    vault_id = create_default_vault(threshold=2)
    make_inactive(w3, tester, deployment, vault_id)
    death_hash = keccak(text="death-cert-1")
    attest(deployment, accounts, signer, vault_id, accounts.guardian1, death_hash)
    v = _vault(deployment, vault_id)
    assert v[9] == State_ACTIVE  # still Active, not Challenge
    assert v[8] == 1


def test_threshold_reached_starts_challenge(w3, tester, deployment, accounts, signer, create_default_vault):
    vault_id = create_default_vault(threshold=2)
    make_inactive(w3, tester, deployment, vault_id)
    death_hash = keccak(text="death-cert-1")
    attest(deployment, accounts, signer, vault_id, accounts.guardian1, death_hash)
    tx = attest(deployment, accounts, signer, vault_id, accounts.guardian2, death_hash)
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    events = deployment.registry.events.ChallengeStarted().process_receipt(receipt)
    assert len(events) == 1

    v = _vault(deployment, vault_id)
    assert v[9] == State_CHALLENGE
    assert v[8] == 2
    assert v[3] > 0  # challengeEndsAt set


# ---------------------------------------------------------------------------
# Duplicate attestation rejection
# ---------------------------------------------------------------------------


def test_duplicate_attestation_same_guardian_reverts(w3, tester, deployment, accounts, signer, create_default_vault):
    vault_id = create_default_vault(threshold=2)
    make_inactive(w3, tester, deployment, vault_id)
    death_hash = keccak(text="death-cert-1")
    attest(deployment, accounts, signer, vault_id, accounts.guardian1, death_hash)
    with pytest.raises(TransactionFailed) as exc:
        attest(deployment, accounts, signer, vault_id, accounts.guardian1, death_hash)
    assert_custom_error(exc, "AlreadyAttested()")


def test_mismatched_death_cert_hash_reverts(w3, tester, deployment, accounts, signer, create_default_vault):
    vault_id = create_default_vault(threshold=2)
    make_inactive(w3, tester, deployment, vault_id)
    attest(deployment, accounts, signer, vault_id, accounts.guardian1, keccak(text="cert-a"))
    with pytest.raises(TransactionFailed) as exc:
        attest(deployment, accounts, signer, vault_id, accounts.guardian2, keccak(text="cert-b"))
    assert_custom_error(exc, "DeathCertMismatch()")


def test_non_guardian_cannot_attest(w3, tester, deployment, accounts, signer, create_default_vault):
    vault_id = create_default_vault(threshold=2)
    make_inactive(w3, tester, deployment, vault_id)
    with pytest.raises(TransactionFailed) as exc:
        attest(deployment, accounts, signer, vault_id, accounts.nominee1, keccak(text="cert-a"))
    assert_custom_error(exc, "NotGuardian()")


# ---------------------------------------------------------------------------
# Owner cancel / activity auto-cancel during Challenge
# ---------------------------------------------------------------------------


def _start_challenge(w3, tester, deployment, accounts, signer, vault_id, death_hash=None):
    death_hash = death_hash or keccak(text="death-cert-1")
    make_inactive(w3, tester, deployment, vault_id)
    attest(deployment, accounts, signer, vault_id, accounts.guardian1, death_hash)
    attest(deployment, accounts, signer, vault_id, accounts.guardian2, death_hash)
    v = _vault(deployment, vault_id)
    assert v[9] == State_CHALLENGE
    return v


def test_owner_cancel_during_challenge(w3, tester, deployment, accounts, signer, create_default_vault):
    vault_id = create_default_vault(threshold=2)
    v = _start_challenge(w3, tester, deployment, accounts, signer, vault_id)
    old_epoch = v[6]

    nonce = deployment.registry.functions.nonces(accounts.owner.address).call()
    deadline = far_future_deadline()
    sig = signer.cancel_release(accounts.owner, vault_id=vault_id, epoch=old_epoch, nonce=nonce, deadline=deadline)
    tx = deployment.registry.functions.cancelRelease(vault_id, deadline, sig).transact({"from": accounts.relayer})
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    events = deployment.registry.events.ReleaseCancelled().process_receipt(receipt)
    assert len(events) == 1
    assert events[0]["args"]["byActivity"] is False

    v2 = _vault(deployment, vault_id)
    assert v2[9] == State_ACTIVE
    assert v2[6] == old_epoch + 1
    assert v2[8] == 0  # attestCount reset


def test_heartbeat_auto_cancels_challenge(w3, tester, deployment, accounts, signer, create_default_vault):
    vault_id = create_default_vault(threshold=2)
    v = _start_challenge(w3, tester, deployment, accounts, signer, vault_id)
    old_epoch = v[6]

    tx = deployment.registry.functions.heartbeatBatch([vault_id]).transact({"from": accounts.relayer})
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    events = deployment.registry.events.ReleaseCancelled().process_receipt(receipt)
    assert len(events) == 1
    assert events[0]["args"]["byActivity"] is True

    v2 = _vault(deployment, vault_id)
    assert v2[9] == State_ACTIVE
    assert v2[6] == old_epoch + 1


def test_epoch_invalidates_stale_attestations_after_cancel(
    w3, tester, deployment, accounts, signer, create_default_vault
):
    """After a cancel, guardians must re-attest: an attestation signature for
    the old epoch cannot be replayed to reach threshold again, because
    `hasAttested` is keyed by epoch and the *new* AttestDeath signature must
    reference the *current* epoch (a stale signature's epoch field no longer
    matches, so recovery still succeeds but the mismatch would only matter if
    a stale off-chain epoch was reused -- here we prove the concrete guarantee:
    guardian1's original attestation no longer counts post-cancel, and a fresh
    attestation against the new epoch is required to build back to threshold).
    """
    vault_id = create_default_vault(threshold=2)
    v = _start_challenge(w3, tester, deployment, accounts, signer, vault_id)
    old_epoch = v[6]

    # Owner cancels -> epoch bumps, attestCount resets to 0.
    nonce = deployment.registry.functions.nonces(accounts.owner.address).call()
    deadline = far_future_deadline()
    sig = signer.cancel_release(accounts.owner, vault_id=vault_id, epoch=old_epoch, nonce=nonce, deadline=deadline)
    deployment.registry.functions.cancelRelease(vault_id, deadline, sig).transact({"from": accounts.relayer})

    v2 = _vault(deployment, vault_id)
    new_epoch = v2[6]
    assert new_epoch == old_epoch + 1
    assert v2[8] == 0

    # A signature built for the OLD epoch is now rejected (guardian must
    # re-attest against the new epoch).
    make_inactive(w3, tester, deployment, vault_id)
    stale_deadline = far_future_deadline()
    stale_sig = signer.attest_death(
        accounts.guardian1,
        vault_id=vault_id,
        death_cert_hash=keccak(text="death-cert-1"),
        epoch=old_epoch,
        deadline=stale_deadline,
    )
    with pytest.raises(TransactionFailed) as exc:
        deployment.registry.functions.attestDeath(
            vault_id, keccak(text="death-cert-1"), accounts.guardian1.address, stale_deadline, stale_sig
        ).transact({"from": accounts.relayer})
    assert_custom_error(exc, "BadSignature()")

    # A fresh attestation against the *current* epoch is accepted, and
    # hasAttested for the new epoch starts empty again (guardian1 can attest
    # even though they already attested once before, in the old epoch).
    fresh_hash = keccak(text="death-cert-1")
    attest(deployment, accounts, signer, vault_id, accounts.guardian1, fresh_hash)
    v3 = _vault(deployment, vault_id)
    assert v3[8] == 1


# ---------------------------------------------------------------------------
# Finalize timing
# ---------------------------------------------------------------------------


def test_finalize_before_challenge_ends_reverts(w3, tester, deployment, accounts, signer, create_default_vault):
    vault_id = create_default_vault(threshold=2, challenge_period=MIN_PERIOD)
    _start_challenge(w3, tester, deployment, accounts, signer, vault_id)
    with pytest.raises(TransactionFailed) as exc:
        deployment.registry.functions.finalizeRelease(vault_id).transact({"from": accounts.stranger})
    assert_custom_error(exc, "ChallengeNotEnded()")


def test_finalize_not_in_challenge_reverts(w3, tester, deployment, accounts, create_default_vault):
    vault_id = create_default_vault()
    with pytest.raises(TransactionFailed) as exc:
        deployment.registry.functions.finalizeRelease(vault_id).transact({"from": accounts.stranger})
    assert_custom_error(exc, "WrongState()")


def test_finalize_after_challenge_ends_releases_and_mints(
    w3, tester, deployment, accounts, signer, create_default_vault
):
    vault_id = create_default_vault(threshold=2, challenge_period=MIN_PERIOD)
    _start_challenge(w3, tester, deployment, accounts, signer, vault_id)
    advance_time(w3, tester, MIN_PERIOD + 1)

    # Anyone can finalize -- use the unrelated "stranger" account.
    tx = deployment.registry.functions.finalizeRelease(vault_id).transact({"from": accounts.stranger})
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    events = deployment.registry.events.Released().process_receipt(receipt)
    assert len(events) == 1

    v = _vault(deployment, vault_id)
    assert v[9] == State_RELEASED

    assert deployment.credential.functions.balanceOf(accounts.nominee1.address).call() == 1
    assert deployment.credential.functions.balanceOf(accounts.nominee2.address).call() == 1
    assert deployment.credential.functions.ownerOf(1).call() == accounts.nominee1.address
    data = deployment.credential.functions.credentialData(1).call()
    assert data[0] == vault_id
    assert data[1] == 6000


# ---------------------------------------------------------------------------
# EIP-712 signature integrity: replay, wrong chainId, expired deadline
# ---------------------------------------------------------------------------


def test_signature_replay_rejected(w3, deployment, accounts, signer, create_default_vault):
    vault_id = create_default_vault()
    nonce = deployment.registry.functions.nonces(accounts.owner.address).call()
    deadline = far_future_deadline()
    new_hash = keccak(text="manifest-v2")
    sig = signer.update_manifest(
        accounts.owner, vault_id=vault_id, manifest_hash=new_hash, nonce=nonce, deadline=deadline
    )
    deployment.registry.functions.updateManifest(vault_id, new_hash, deadline, sig).transact(
        {"from": accounts.relayer}
    )
    # Same signature replayed: the contract always rebuilds the struct hash
    # from the *current* on-chain nonce (there's no client-supplied nonce
    # parameter to fake), so the stale signature -- signed over the old nonce
    # -- no longer recovers to the owner's address at all.
    with pytest.raises(TransactionFailed) as exc:
        deployment.registry.functions.updateManifest(vault_id, new_hash, deadline, sig).transact(
            {"from": accounts.relayer}
        )
    assert_custom_error(exc, "BadSignature()")


def test_create_vault_replay_rejected_via_explicit_nonce(w3, deployment, accounts, signer):
    """createVault's request struct carries an explicit `nonce` field (unlike
    the vault-scoped owner actions), so replaying the exact same signed
    request a second time is caught by the explicit BadNonce() check."""
    nonce = deployment.registry.functions.nonces(accounts.owner.address).call()
    deadline = far_future_deadline()
    guardians = [accounts.guardian1.address, accounts.guardian2.address]
    nominees = [accounts.nominee1.address]
    shares = [10000]
    manifest_hash = keccak(text="m")
    sig = signer.create_vault(
        accounts.owner,
        owner=accounts.owner.address,
        manifest_hash=manifest_hash,
        inactivity_period=MIN_PERIOD,
        challenge_period=MIN_PERIOD,
        threshold=1,
        guardians=guardians,
        nominees=nominees,
        share_bps=shares,
        nonce=nonce,
        deadline=deadline,
    )
    req = (
        accounts.owner.address,
        manifest_hash,
        MIN_PERIOD,
        MIN_PERIOD,
        1,
        guardians,
        nominees,
        shares,
        nonce,
        deadline,
    )
    deployment.registry.functions.createVault(req, sig).transact({"from": accounts.relayer})
    with pytest.raises(TransactionFailed) as exc:
        deployment.registry.functions.createVault(req, sig).transact({"from": accounts.relayer})
    assert_custom_error(exc, "BadNonce()")


def test_wrong_chain_id_rejected(w3, deployment, accounts, signer, create_default_vault):
    vault_id = create_default_vault()
    nonce = deployment.registry.functions.nonces(accounts.owner.address).call()
    deadline = far_future_deadline()
    new_hash = keccak(text="manifest-v2")
    # Sign with a different chainId than the one the contract's domain separator uses.
    bad_sig = signer.update_manifest(
        accounts.owner,
        vault_id=vault_id,
        manifest_hash=new_hash,
        nonce=nonce,
        deadline=deadline,
        chain_id=999999,
    )
    with pytest.raises(TransactionFailed) as exc:
        deployment.registry.functions.updateManifest(vault_id, new_hash, deadline, bad_sig).transact(
            {"from": accounts.relayer}
        )
    assert_custom_error(exc, "BadSignature()")


def test_expired_deadline_rejected(w3, deployment, accounts, signer, create_default_vault):
    vault_id = create_default_vault()
    nonce = deployment.registry.functions.nonces(accounts.owner.address).call()
    expired_deadline = 1  # far in the past (unix epoch + 1s)
    new_hash = keccak(text="manifest-v2")
    sig = signer.update_manifest(
        accounts.owner, vault_id=vault_id, manifest_hash=new_hash, nonce=nonce, deadline=expired_deadline
    )
    with pytest.raises(TransactionFailed) as exc:
        deployment.registry.functions.updateManifest(vault_id, new_hash, expired_deadline, sig).transact(
            {"from": accounts.relayer}
        )
    assert_custom_error(exc, "Expired()")


def test_wrong_signer_rejected(w3, deployment, accounts, signer, create_default_vault):
    """A guardian's key signing an owner-only action (or vice versa) must be
    rejected -- the relayer can relay bytes, but it can't make someone else's
    signature pass as the owner's."""
    vault_id = create_default_vault()
    nonce = deployment.registry.functions.nonces(accounts.owner.address).call()
    deadline = far_future_deadline()
    new_hash = keccak(text="manifest-v2")
    wrong_sig = signer.update_manifest(
        accounts.guardian1, vault_id=vault_id, manifest_hash=new_hash, nonce=nonce, deadline=deadline
    )
    with pytest.raises(TransactionFailed) as exc:
        deployment.registry.functions.updateManifest(vault_id, new_hash, deadline, wrong_sig).transact(
            {"from": accounts.relayer}
        )
    assert_custom_error(exc, "BadSignature()")


# ---------------------------------------------------------------------------
# Only-relayer enforcement
# ---------------------------------------------------------------------------


def test_only_relayer_create_vault(w3, deployment, accounts, signer):
    nonce = deployment.registry.functions.nonces(accounts.owner.address).call()
    deadline = far_future_deadline()
    guardians = [accounts.guardian1.address, accounts.guardian2.address]
    nominees = [accounts.nominee1.address]
    shares = [10000]
    manifest_hash = keccak(text="m")
    sig = signer.create_vault(
        accounts.owner,
        owner=accounts.owner.address,
        manifest_hash=manifest_hash,
        inactivity_period=MIN_PERIOD,
        challenge_period=MIN_PERIOD,
        threshold=1,
        guardians=guardians,
        nominees=nominees,
        share_bps=shares,
        nonce=nonce,
        deadline=deadline,
    )
    req = (
        accounts.owner.address,
        manifest_hash,
        MIN_PERIOD,
        MIN_PERIOD,
        1,
        guardians,
        nominees,
        shares,
        nonce,
        deadline,
    )
    with pytest.raises(TransactionFailed) as exc:
        deployment.registry.functions.createVault(req, sig).transact({"from": accounts.stranger})
    assert_custom_error(exc, "NotRelayer()")


def test_only_relayer_heartbeat(deployment, accounts):
    with pytest.raises(TransactionFailed) as exc:
        deployment.registry.functions.heartbeatBatch([1]).transact({"from": accounts.stranger})
    assert_custom_error(exc, "NotRelayer()")


def test_only_relayer_attest_death(deployment, accounts, signer, create_default_vault):
    vault_id = create_default_vault()
    deadline = far_future_deadline()
    sig = signer.attest_death(
        accounts.guardian1, vault_id=vault_id, death_cert_hash=keccak(text="c"), epoch=0, deadline=deadline
    )
    with pytest.raises(TransactionFailed) as exc:
        deployment.registry.functions.attestDeath(
            vault_id, keccak(text="c"), accounts.guardian1.address, deadline, sig
        ).transact({"from": accounts.stranger})
    assert_custom_error(exc, "NotRelayer()")


def test_only_relayer_cancel_release(deployment, accounts, signer):
    deadline = far_future_deadline()
    sig = signer.cancel_release(accounts.owner, vault_id=1, epoch=0, nonce=0, deadline=deadline)
    with pytest.raises(TransactionFailed) as exc:
        deployment.registry.functions.cancelRelease(1, deadline, sig).transact({"from": accounts.stranger})
    assert_custom_error(exc, "NotRelayer()")


def test_finalize_release_is_open_to_anyone(w3, tester, deployment, accounts, signer, create_default_vault):
    """Unlike the other entrypoints, finalizeRelease has no onlyRelayer gate --
    confirm a random funded account (not the relayer) can call it."""
    vault_id = create_default_vault(threshold=2, challenge_period=MIN_PERIOD)
    _start_challenge(w3, tester, deployment, accounts, signer, vault_id)
    advance_time(w3, tester, MIN_PERIOD + 1)
    # accounts.stranger is deliberately not the relayer.
    deployment.registry.functions.finalizeRelease(vault_id).transact({"from": accounts.stranger})
    v = _vault(deployment, vault_id)
    assert v[9] == State_RELEASED


# ---------------------------------------------------------------------------
# Vault construction validation
# ---------------------------------------------------------------------------


def test_shares_must_sum_to_10000(create_default_vault, accounts):
    with pytest.raises(TransactionFailed) as exc:
        create_default_vault(share_bps=[5000, 4000])
    assert_custom_error(exc, "BadShares()")


def test_period_below_min_reverts(create_default_vault):
    with pytest.raises(TransactionFailed) as exc:
        create_default_vault(inactivity_period=MIN_PERIOD - 1)
    assert_custom_error(exc, "PeriodTooShort()")


def test_threshold_zero_reverts(create_default_vault):
    with pytest.raises(TransactionFailed) as exc:
        create_default_vault(threshold=0)
    assert_custom_error(exc, "BadThreshold()")


def test_threshold_above_guardian_count_reverts(create_default_vault, accounts):
    with pytest.raises(TransactionFailed) as exc:
        create_default_vault(threshold=5, guardians=[accounts.guardian1.address, accounts.guardian2.address])
    assert_custom_error(exc, "BadThreshold()")
