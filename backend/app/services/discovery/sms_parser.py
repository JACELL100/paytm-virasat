"""Regex pack for common Indian bank/insurer SMS formats, per section 8.3
step 1. Leftovers that don't match a known pattern are returned as
`unmatched` lines for the LLM classifier to look at."""
from __future__ import annotations

import re
from typing import Any

SMS_PATTERNS = [
    # "Rs.2340 debited from A/c XX1234 on 05-Jan-24 towards HDFCLIFE premium"
    re.compile(
        r"(?:Rs\.?|INR)\s?(?P<amount>[\d,]+(?:\.\d{1,2})?)\s*(?:debited|paid|spent)\b.*?"
        r"(?:A/c|a/c|account)\s*[Xx*]*(?P<account>\d{2,6}).*?"
        r"(?:towards|for)?\s*(?P<merchant>[A-Za-z][A-Za-z0-9 .&_-]{2,40})",
        re.IGNORECASE,
    ),
    # "Premium of Rs 2340 for policy 123456 HDFC Life due on ..."
    re.compile(
        r"(?:premium|SIP|EMI)\s*(?:of)?\s*(?:Rs\.?|INR)\s?(?P<amount>[\d,]+(?:\.\d{1,2})?).*?"
        r"(?:for|towards)?\s*(?P<merchant>[A-Za-z][A-Za-z0-9 .&_-]{2,40})",
        re.IGNORECASE,
    ),
]

KEYWORDS = ["premium", "sip", "emi", "debited", "policy", "maturity", "nav", "instalment"]


def parse_sms_text(text: str) -> dict[str, Any]:
    matched: list[dict[str, Any]] = []
    unmatched: list[str] = []

    for line in [l.strip() for l in text.splitlines() if l.strip()]:
        hit = None
        for pattern in SMS_PATTERNS:
            m = pattern.search(line)
            if m:
                gd = m.groupdict()
                hit = {
                    "amount": float(gd["amount"].replace(",", "")) if gd.get("amount") else None,
                    "merchant": gd.get("merchant", "").strip(),
                    "account_ref_masked": f"XX{gd['account']}" if gd.get("account") else None,
                    "raw": line,
                }
                break
        if hit:
            matched.append(hit)
        elif any(k in line.lower() for k in KEYWORDS):
            unmatched.append(line)

    return {"matched": matched, "unmatched": unmatched}
