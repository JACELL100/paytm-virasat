"""Fast classification of a recurring transaction group into an asset
suggestion (`classify_txn_group.md`, task=fast, section 8.3 step 4)."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel

from app.core.logging import get_logger
from app.services.ai.groq_client import GroqNotConfigured, chat_complete_json

logger = get_logger(__name__)


class TxnGroupClassification(BaseModel):
    product_type: str
    institution_slug: Optional[str] = None
    confidence: float
    rationale: str


async def classify_txn_group(*, merchant: str, amount: float, frequency: str, sample_narrations: list[str]) -> TxnGroupClassification:
    messages = [
        {
            "role": "system",
            "content": (
                "Classify a recurring payment group into a financial product type "
                "(term_life, life_endowment, ulip, health, motor, fd, savings, mutual_fund, "
                "stocks, ppf, epf, nps, gold, loan, credit_card, other) and an institution slug. "
                'Return JSON: {"product_type": str, "institution_slug": str|null, "confidence": float 0..1, "rationale": str}'
            ),
        },
        {
            "role": "user",
            "content": f"Merchant: {merchant}\nAmount: {amount}\nFrequency: {frequency}\nSample narrations: {sample_narrations[:5]}",
        },
    ]
    try:
        return await chat_complete_json("fast", messages, TxnGroupClassification)
    except GroqNotConfigured:
        logger.warning("classify_txn_group_ai_not_configured", merchant=merchant)
        return TxnGroupClassification(product_type="other", institution_slug=None, confidence=0.0, rationale="AI not configured; needs manual review.")
    except Exception:
        logger.exception("classify_txn_group_failed", merchant=merchant)
        return TxnGroupClassification(product_type="other", institution_slug=None, confidence=0.0, rationale="Classification failed; needs manual review.")
