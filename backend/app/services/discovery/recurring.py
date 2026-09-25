"""Merchant normalisation (rapidfuzz vs institutions.json aliases) and
recurring-payment detection (pandas), per section 8.3 steps 2-3."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

STRONG_KEYWORDS = ["premium", "sip", "emi", "instalment", "installment"]


def _clean_merchant(raw: str) -> str:
    text = raw.lower()
    text = re.sub(r"[@/].*", "", text)  # strip UPI handles
    text = re.sub(r"\b\d{6,}\b", "", text)  # strip long ref numbers
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


_institutions_cache: Optional[list[dict]] = None


def _load_institutions() -> list[dict]:
    global _institutions_cache
    if _institutions_cache is not None:
        return _institutions_cache
    path = DATA_DIR / "institutions.json"
    if not path.exists():
        _institutions_cache = []
        return []
    try:
        _institutions_cache = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("institutions_json_unreadable")
        _institutions_cache = []
    return _institutions_cache


def match_institution(raw_merchant: str, min_score: float = 80.0) -> Optional[dict[str, Any]]:
    """rapidfuzz-matches a cleaned merchant string against institutions.json aliases."""
    cleaned = _clean_merchant(raw_merchant)
    institutions = _load_institutions()
    if not institutions or not cleaned:
        return None
    try:
        from rapidfuzz import fuzz, process, utils

        best = None
        best_score = 0.0
        for inst in institutions:
            candidates = [inst["name"]] + inst.get("aliases", [])
            match = process.extractOne(cleaned, candidates, scorer=fuzz.token_set_ratio, processor=utils.default_process)
            if match and match[1] > best_score:
                best_score = match[1]
                best = inst
        if best and best_score >= min_score:
            return {**best, "match_score": best_score}
        return None
    except Exception:
        logger.warning("rapidfuzz_match_failed")
        return None


def _periodicity(days_between: list[float]) -> Optional[str]:
    if not days_between:
        return None
    avg = sum(days_between) / len(days_between)
    if 25 <= avg <= 35:
        return "monthly"
    if 80 <= avg <= 100:
        return "quarterly"
    if 350 <= avg <= 380:
        return "yearly"
    return None


def detect_recurring_groups(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Groups transactions by (cleaned merchant, amount within +-5%) and flags
    recurring groups: >= 2 occurrences, OR 1 occurrence with a strong keyword."""
    if not transactions:
        return []

    try:
        import pandas as pd

        df = pd.DataFrame(transactions)
        if df.empty or "narration" not in df.columns:
            return []
        df["merchant_clean"] = df["narration"].fillna("").map(_clean_merchant)
        df["amount"] = df.get("debit").fillna(0) if "debit" in df.columns else 0

        groups = []
        for merchant, sub in df.groupby("merchant_clean"):
            if not merchant:
                continue
            amounts = sorted(sub["amount"].tolist())
            # bucket amounts within +-5% of the median
            median = amounts[len(amounts) // 2] if amounts else 0
            bucket = sub[(sub["amount"] >= median * 0.95) & (sub["amount"] <= median * 1.05)] if median else sub
            occurrences = len(bucket)
            dates = sorted(pd.to_datetime(bucket["date"]).tolist()) if "date" in bucket.columns else []
            days_between = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)] if len(dates) > 1 else []
            periodicity = _periodicity(days_between)

            has_strong_keyword = bucket["narration"].fillna("").str.lower().str.contains("|".join(STRONG_KEYWORDS)).any()

            if occurrences >= 2 or (occurrences >= 1 and has_strong_keyword):
                groups.append(
                    {
                        "merchant": merchant,
                        "amount": float(median),
                        "occurrences": int(occurrences),
                        "periodicity": periodicity or ("unknown" if occurrences < 2 else None),
                        "sample_narrations": bucket["narration"].tolist()[:5],
                        "has_strong_keyword": bool(has_strong_keyword),
                    }
                )
        return groups
    except Exception:
        logger.exception("detect_recurring_groups_failed")
        return []
