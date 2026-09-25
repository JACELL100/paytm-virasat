"""Deterministic Legacy Score + nominee-gap detection.

Per Implementation_Plan.md section 8.5:
    Legacy Score (0-100) =
        nominee coverage across assets       (40)
      + guardians accepted >= threshold      (15)
      + key docs uploaded                    (15)
      + protection adequacy                  (20)   term cover / (10 x annual income), capped at 1
      + contact freshness                    (10)

The LLM is only ever used to *explain* this score in plain language
(services/ai/... `explain_gaps.md`); the number itself is always computed
here, deterministically, so it's stable and testable.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

W_NOMINEE_COVERAGE = 40
W_GUARDIANS = 15
W_DOCS = 15
W_PROTECTION = 20
W_CONTACT = 10

CONTACT_FULL_MARKS_DAYS = 180
CONTACT_ZERO_MARKS_DAYS = 720


def _nominee_coverage_score(assets: list[dict[str, Any]]) -> float:
    if not assets:
        return 0.0
    ok = sum(1 for a in assets if a.get("nominee_status") == "ok")
    return W_NOMINEE_COVERAGE * (ok / len(assets))


def _guardians_score(guardians: list[dict[str, Any]], threshold: int) -> float:
    if threshold <= 0:
        return W_GUARDIANS
    accepted = sum(1 for g in guardians if g.get("status") == "accepted")
    return W_GUARDIANS * min(1.0, accepted / threshold)


def _docs_score(assets: list[dict[str, Any]], documents: list[dict[str, Any]]) -> float:
    if not assets:
        return 0.0
    asset_ids_with_docs = {d.get("asset_id") for d in documents if d.get("asset_id")}
    covered = sum(1 for a in assets if a.get("id") in asset_ids_with_docs)
    return W_DOCS * (covered / len(assets))


def _protection_score(assets: list[dict[str, Any]], annual_income: Optional[float]) -> float:
    if not annual_income or annual_income <= 0:
        return 0.0
    term_cover = sum(
        (a.get("value_estimate") or 0) for a in assets if a.get("type") in ("term_life",)
    )
    target = 10 * annual_income
    if target <= 0:
        return 0.0
    ratio = min(1.0, term_cover / target)
    return W_PROTECTION * ratio


def _contact_freshness_score(contact_updated_at: Optional[str]) -> float:
    if not contact_updated_at:
        return 0.0
    try:
        updated = datetime.fromisoformat(contact_updated_at.replace("Z", "+00:00"))
    except Exception:
        return 0.0
    now = datetime.now(timezone.utc)
    days = (now - updated).total_seconds() / 86400
    if days <= CONTACT_FULL_MARKS_DAYS:
        return float(W_CONTACT)
    if days >= CONTACT_ZERO_MARKS_DAYS:
        return 0.0
    frac = 1 - (days - CONTACT_FULL_MARKS_DAYS) / (CONTACT_ZERO_MARKS_DAYS - CONTACT_FULL_MARKS_DAYS)
    return W_CONTACT * frac


def compute_legacy_score(
    *,
    assets: list[dict[str, Any]],
    guardians: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    threshold: int,
    annual_income: Optional[float],
    contact_updated_at: Optional[str],
) -> dict[str, Any]:
    nominee_coverage = _nominee_coverage_score(assets)
    guardians_score = _guardians_score(guardians, threshold)
    docs_score = _docs_score(assets, documents)
    protection_score = _protection_score(assets, annual_income)
    contact_score = _contact_freshness_score(contact_updated_at)

    total = nominee_coverage + guardians_score + docs_score + protection_score + contact_score
    return {
        "legacy_score": round(total),
        "breakdown": {
            "nominee_coverage": round(nominee_coverage, 1),
            "guardians": round(guardians_score, 1),
            "documents": round(docs_score, 1),
            "protection_adequacy": round(protection_score, 1),
            "contact_freshness": round(contact_score, 1),
        },
    }


def detect_nominee_gaps(
    *, assets: list[dict[str, Any]], vault_nominees: Optional[list[dict[str, Any]]] = None
) -> list[dict[str, Any]]:
    """Nominee gap: missing, outdated (user-flagged), share total != 100%,
    or a minor nominee with no appointee (section 8.5)."""
    gaps: list[dict[str, Any]] = []

    for a in assets:
        status = a.get("nominee_status")
        if status == "missing":
            gaps.append(
                {
                    "kind": "nominee_missing",
                    "asset_id": a.get("id"),
                    "title": f"No nominee on {a.get('label', 'this asset')}",
                    "detail": "This asset has no nominee recorded. Add one so it can be claimed smoothly.",
                    "severity": "high",
                }
            )
        elif status == "outdated":
            gaps.append(
                {
                    "kind": "nominee_outdated",
                    "asset_id": a.get("id"),
                    "title": f"Nominee may be outdated on {a.get('label', 'this asset')}",
                    "detail": "The nominee on record may no longer be correct. Please review and update.",
                    "severity": "medium",
                }
            )

    if vault_nominees:
        total_bps = sum(n.get("share_bps", 0) for n in vault_nominees)
        if vault_nominees and total_bps != 10000:
            gaps.append(
                {
                    "kind": "share_mismatch",
                    "asset_id": None,
                    "title": "Nominee shares don't add up to 100%",
                    "detail": f"Vault nominee shares currently total {total_bps / 100:.1f}%, not 100%.",
                    "severity": "high",
                }
            )
        for n in vault_nominees:
            if n.get("is_minor") and not n.get("appointee_name"):
                gaps.append(
                    {
                        "kind": "minor_no_appointee",
                        "asset_id": None,
                        "title": f"{n.get('name', 'A nominee')} is a minor with no appointee",
                        "detail": "A minor nominee needs a guardian/appointee to legally receive funds.",
                        "severity": "high",
                    }
                )

    return gaps
