"""Full seal/unseal manifest flow + "manifest hash equals the on-chain hash"
(section 17 must-cover case). Requires WALLET_ENC_KEY/ESCROW_KEY/RECOVERY_KEY
in backend/.env (generated Fernet keys -- see .env.example)."""
from __future__ import annotations

import pytest

from app.core.config import settings
from app.services.crypto import manifest as manifest_service
from app.services.crypto import shamir

pytestmark = pytest.mark.skipif(
    not (settings.ESCROW_KEY and settings.RECOVERY_KEY),
    reason="ESCROW_KEY/RECOVERY_KEY not configured in this environment.",
)


def _sample_manifest() -> dict:
    return manifest_service.build_manifest(
        owner={"full_name": "Rajesh Patil", "email": "rajesh@example.com", "phone": "+91-90000-00000"},
        assets=[{"id": "a1", "type": "term_life", "label": "HDFC Life Term", "value_estimate": 5000000}],
        documents=[],
        nominees=[{"name": "Sunita Patil", "relation": "wife", "share_bps": 6000}],
        note="Take care of Aarav's education.",
    )


def test_seal_produces_hash_matching_recomputed_ciphertext_hash():
    """This is the exact check performed on-chain vs. off-chain: whoever
    submits manifestHash to the registry must get the same value we'd
    recompute from the stored ciphertext (keccak256(ciphertext))."""
    sealed = manifest_service.seal_manifest(_sample_manifest(), vault_id="vault-abc", epoch=0)
    recomputed = manifest_service.keccak256_hex(sealed.ciphertext)
    assert sealed.manifest_hash_hex == recomputed
    assert sealed.manifest_hash_hex.startswith("0x")
    assert len(sealed.manifest_hash_hex) == 66  # 0x + 64 hex chars = 32 bytes


def test_seal_then_unlock_with_escrow_and_nominee_share_recovers_manifest():
    original = _sample_manifest()
    sealed = manifest_service.seal_manifest(original, vault_id="vault-xyz", epoch=0)

    recovered = manifest_service.unseal_manifest(
        ciphertext=sealed.ciphertext,
        escrow_share_enc=sealed.escrow_share_enc,
        nominee_share_b64=sealed.nominee_share_b64,
        vault_id="vault-xyz",
        epoch=0,
        expected_manifest_hash_hex=sealed.manifest_hash_hex,
    )
    assert recovered == original


def test_unlock_rejects_mismatched_onchain_hash():
    sealed = manifest_service.seal_manifest(_sample_manifest(), vault_id="vault-1", epoch=0)
    from app.core.errors import ApiError

    with pytest.raises(ApiError):
        manifest_service.unseal_manifest(
            ciphertext=sealed.ciphertext,
            escrow_share_enc=sealed.escrow_share_enc,
            nominee_share_b64=sealed.nominee_share_b64,
            vault_id="vault-1",
            epoch=0,
            expected_manifest_hash_hex="0x" + "00" * 32,
        )


def test_pack_and_unpack_escrow_column_roundtrip():
    sealed = manifest_service.seal_manifest(_sample_manifest(), vault_id="vault-pack", epoch=0)
    packed = manifest_service.pack_escrow_column(
        escrow_share_enc=sealed.escrow_share_enc, nominee_pending_share_b64=sealed.nominee_share_b64
    )
    escrow_token, nominee_pending = manifest_service.unpack_escrow_column(packed)
    assert escrow_token == sealed.escrow_share_enc
    assert nominee_pending == sealed.nominee_share_b64


def test_reseal_new_epoch_changes_hash_and_shares():
    manifest = _sample_manifest()
    sealed_epoch0 = manifest_service.seal_manifest(manifest, vault_id="vault-resealed", epoch=0)
    sealed_epoch1 = manifest_service.seal_manifest(manifest, vault_id="vault-resealed", epoch=1)
    assert sealed_epoch0.manifest_hash_hex != sealed_epoch1.manifest_hash_hex
    assert sealed_epoch0.nominee_share_b64 != sealed_epoch1.nominee_share_b64
