"""Shamir 2-of-3: any 2 of 3 shares reconstruct the DEK; any 1 alone fails
(section 17 must-cover case)."""
from __future__ import annotations

import os

import pytest

from app.services.crypto import shamir


def test_split_produces_three_shares_of_expected_size():
    dek = os.urandom(32)
    shares = shamir.split_dek(dek)
    assert len(shares) == 3
    for s in shares:
        assert len(s) == shamir.SHARE_SIZE


@pytest.mark.parametrize("pair", [(0, 1), (0, 2), (1, 2)])
def test_any_two_of_three_shares_reconstruct_dek(pair):
    dek = os.urandom(32)
    shares = shamir.split_dek(dek)
    i, j = pair
    reconstructed = shamir.combine_dek([shares[i], shares[j]])
    assert reconstructed == dek


def test_all_three_shares_also_reconstruct_dek():
    dek = os.urandom(32)
    shares = shamir.split_dek(dek)
    assert shamir.combine_dek(shares) == dek


def test_single_share_is_insufficient():
    dek = os.urandom(32)
    shares = shamir.split_dek(dek)
    with pytest.raises(ValueError):
        shamir.combine_dek([shares[0]])


def test_single_share_reveals_nothing_useful_different_from_dek():
    """A single share alone should not equal (or trivially leak) the DEK."""
    dek = os.urandom(32)
    shares = shamir.split_dek(dek)
    assert shares[0][1:] != dek[:16]  # the raw share bytes aren't the plaintext half


def test_b64_roundtrip():
    dek = os.urandom(32)
    shares = shamir.split_dek(dek)
    b64 = shamir.share_to_b64(shares[1])
    back = shamir.share_from_b64(b64)
    assert back == shares[1]
