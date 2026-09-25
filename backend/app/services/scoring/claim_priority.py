"""Claim priority scoring, per Implementation_Plan.md section 8.5:

    priority = 0.45 * payout_norm + 0.35 * urgency + 0.20 * ease

- payout_norm: the claim's payout size relative to the largest payout in the
  claim set (0..1).
- urgency: running EMIs on a loan with a protection cover (stops the family
  paying EMIs), time-bound intimation clauses, and health reimbursements
  score higher.
- ease: fraction of required documents already available (0..1).
"""
from __future__ import annotations

from typing import Any, Optional

W_PAYOUT = 0.45
W_URGENCY = 0.35
W_EASE = 0.20

# Base urgency by asset/product type -- a loan with protection cover is most
# urgent (stops EMIs accruing against the family), then health (often has a
# tight intimation window), then life covers with claim-intimation clauses.
URGENCY_BY_TYPE = {
    "loan": 1.0,
    "health": 0.85,
    "term_life": 0.6,
    "life_endowment": 0.55,
    "ulip": 0.5,
    "motor": 0.4,
    "credit_card": 0.35,
}
DEFAULT_URGENCY = 0.3


def payout_norm(value_estimate: Optional[float], max_payout: Optional[float]) -> float:
    if not value_estimate or not max_payout or max_payout <= 0:
        return 0.0
    return max(0.0, min(1.0, value_estimate / max_payout))


def urgency_score(asset_type: str, *, has_active_loan_protection: bool = False) -> float:
    base = URGENCY_BY_TYPE.get(asset_type, DEFAULT_URGENCY)
    if asset_type == "loan" and has_active_loan_protection:
        return 1.0
    return base


def ease_score(required_docs: list[str], available_docs: list[str]) -> float:
    if not required_docs:
        return 1.0
    have = set(d.lower() for d in available_docs)
    matched = sum(1 for d in required_docs if d.lower() in have)
    return matched / len(required_docs)


def compute_claim_priority(
    *,
    asset_type: str,
    value_estimate: Optional[float],
    max_payout: Optional[float],
    required_docs: list[str],
    available_docs: list[str],
    has_active_loan_protection: bool = False,
) -> float:
    p = payout_norm(value_estimate, max_payout)
    u = urgency_score(asset_type, has_active_loan_protection=has_active_loan_protection)
    e = ease_score(required_docs, available_docs)
    score = W_PAYOUT * p + W_URGENCY * u + W_EASE * e
    return round(score * 100, 1)  # 0..100 for easy display


def rank_claims(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """`claims` items need: asset_type, value_estimate, required_docs, available_docs,
    optional has_active_loan_protection. Adds/overwrites `priority_score` and
    returns claims sorted descending by it."""
    max_payout = max((c.get("value_estimate") or 0) for c in claims) if claims else 0
    scored = []
    for c in claims:
        score = compute_claim_priority(
            asset_type=c.get("asset_type", "other"),
            value_estimate=c.get("value_estimate"),
            max_payout=max_payout,
            required_docs=c.get("required_docs", []),
            available_docs=c.get("available_docs", []),
            has_active_loan_protection=c.get("has_active_loan_protection", False),
        )
        scored.append({**c, "priority_score": score})
    return sorted(scored, key=lambda c: c["priority_score"], reverse=True)
