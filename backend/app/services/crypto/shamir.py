"""2-of-3 Shamir secret sharing over the 32-byte manifest DEK.

pycryptodome's `Crypto.Protocol.SecretSharing.Shamir` only operates on
16-byte (128-bit) secrets, so per Implementation_Plan.md section 11 we split
the 32-byte DEK into two 16-byte halves and Shamir-split each half
independently into 3 shares (threshold 2). A participant's "share" is the
concatenation of: 1 index byte + 16-byte half-1 share + 16-byte half-2 share
(33 bytes total), so any 2 participants' shares are enough to reconstruct
the whole DEK, and any 1 alone reveals nothing.

Share ordering per section 11:
    shares[0] -> ESCROW    (Fernet(ESCROW_KEY) in vaults.escrow_share_enc)
    shares[1] -> NOMINEE   ("Legacy Key", QR / PDF card, never stored server-side after issuance)
    shares[2] -> RECOVERY  (Fernet(RECOVERY_KEY) in vaults.recovery_share_enc, break-glass)
"""
from __future__ import annotations

import base64

from Crypto.Protocol.SecretSharing import Shamir

HALF_SIZE = 16
DEK_SIZE = 32
SHARE_SIZE = 1 + HALF_SIZE + HALF_SIZE  # index byte + two 16-byte half-shares
THRESHOLD = 2
TOTAL_SHARES = 3

ESCROW_INDEX = 0
NOMINEE_INDEX = 1
RECOVERY_INDEX = 2


def split_dek(dek: bytes) -> list[bytes]:
    """Splits a 32-byte DEK into 3 shares (2-of-3 threshold), each 33 bytes."""
    if len(dek) != DEK_SIZE:
        raise ValueError(f"DEK must be {DEK_SIZE} bytes, got {len(dek)}")

    half1, half2 = dek[:HALF_SIZE], dek[HALF_SIZE:]
    shares1 = Shamir.split(THRESHOLD, TOTAL_SHARES, half1, ssss=False)
    shares2 = Shamir.split(THRESHOLD, TOTAL_SHARES, half2, ssss=False)

    shares: list[bytes] = []
    for (idx1, s1), (idx2, s2) in zip(shares1, shares2):
        if idx1 != idx2:
            raise RuntimeError("Shamir share indices for the two halves diverged unexpectedly.")
        shares.append(bytes([idx1]) + s1 + s2)
    return shares


def combine_dek(shares: list[bytes]) -> bytes:
    """Reconstructs the 32-byte DEK from >= 2 of the 3 shares."""
    if len(shares) < THRESHOLD:
        raise ValueError(f"Need at least {THRESHOLD} shares to reconstruct the DEK, got {len(shares)}")
    for s in shares:
        if len(s) != SHARE_SIZE:
            raise ValueError(f"Each share must be {SHARE_SIZE} bytes, got {len(s)}")

    shares1 = [(s[0], s[1 : 1 + HALF_SIZE]) for s in shares]
    shares2 = [(s[0], s[1 + HALF_SIZE : 1 + 2 * HALF_SIZE]) for s in shares]

    half1 = Shamir.combine(shares1, ssss=False)
    half2 = Shamir.combine(shares2, ssss=False)
    return half1 + half2


def share_to_b64(share: bytes) -> str:
    return base64.urlsafe_b64encode(share).decode("ascii")


def share_from_b64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text.encode("ascii"))
