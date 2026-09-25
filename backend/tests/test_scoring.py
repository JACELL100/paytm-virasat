from __future__ import annotations

from app.services.scoring.claim_priority import compute_claim_priority, ease_score, payout_norm, rank_claims, urgency_score
from app.services.scoring.coverage import compute_coverage_gap
from app.services.scoring.legacy_score import compute_legacy_score, detect_nominee_gaps


def test_legacy_score_all_gaps_scores_low():
    result = compute_legacy_score(
        assets=[{"id": "a1", "type": "term_life", "nominee_status": "missing", "value_estimate": 0}],
        guardians=[],
        documents=[],
        threshold=2,
        annual_income=None,
        contact_updated_at=None,
    )
    assert result["legacy_score"] == 0


def test_legacy_score_full_coverage_scores_high():
    assets = [{"id": "a1", "type": "term_life", "nominee_status": "ok", "value_estimate": 12_000_000}]
    guardians = [{"status": "accepted"}, {"status": "accepted"}]
    documents = [{"asset_id": "a1"}]
    from datetime import datetime, timezone

    result = compute_legacy_score(
        assets=assets,
        guardians=guardians,
        documents=documents,
        threshold=2,
        annual_income=1_000_000,
        contact_updated_at=datetime.now(timezone.utc).isoformat(),
    )
    assert result["legacy_score"] == 100


def test_detect_nominee_gaps_flags_missing_and_outdated():
    assets = [
        {"id": "a1", "nominee_status": "missing", "label": "Term plan"},
        {"id": "a2", "nominee_status": "outdated", "label": "FD"},
        {"id": "a3", "nominee_status": "ok", "label": "Health"},
    ]
    gaps = detect_nominee_gaps(assets=assets)
    kinds = {g["kind"] for g in gaps}
    assert "nominee_missing" in kinds
    assert "nominee_outdated" in kinds
    assert len(gaps) == 2


def test_detect_nominee_gaps_share_mismatch():
    gaps = detect_nominee_gaps(assets=[], vault_nominees=[{"share_bps": 6000}, {"share_bps": 3000}])
    assert any(g["kind"] == "share_mismatch" for g in gaps)


def test_coverage_gap_none_when_adequately_covered():
    assets = [{"type": "term_life", "value_estimate": 10_000_000}]
    assert compute_coverage_gap(assets=assets, annual_income=1_000_000) is None


def test_coverage_gap_flagged_when_under_covered():
    assets = [{"type": "term_life", "value_estimate": 1_000_000}]
    gap = compute_coverage_gap(assets=assets, annual_income=1_000_000)
    assert gap is not None
    assert gap["kind"] == "coverage_gap"


def test_payout_norm_bounds():
    assert payout_norm(50, 100) == 0.5
    assert payout_norm(None, 100) == 0.0
    assert payout_norm(200, 100) == 1.0


def test_urgency_loan_with_protection_is_max():
    assert urgency_score("loan", has_active_loan_protection=True) == 1.0


def test_claim_priority_ranks_urgent_loan_above_low_value_motor():
    claims = [
        {"asset_type": "loan", "value_estimate": 800_000, "required_docs": ["a"], "available_docs": ["a"], "has_active_loan_protection": True},
        {"asset_type": "motor", "value_estimate": 50_000, "required_docs": ["a", "b"], "available_docs": []},
    ]
    ranked = rank_claims(claims)
    assert ranked[0]["asset_type"] == "loan"
    assert ranked[0]["priority_score"] > ranked[1]["priority_score"]


def test_ease_score_full_when_all_docs_available():
    assert ease_score(["a", "b"], ["a", "b", "c"]) == 1.0
    assert ease_score([], []) == 1.0
    assert ease_score(["a", "b"], []) == 0.0
