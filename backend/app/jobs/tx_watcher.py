"""`tx_watcher` job, section 8.6: polls receipts for `chain_txs` in `sent`,
marks mined/failed, every 15s while awake."""
from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.db.repos import chain as chain_repo
from app.services.chain.web3_client import get_w3

logger = get_logger(__name__)


async def run_tx_watcher() -> dict[str, Any]:
    w3 = get_w3()
    if w3 is None:
        return {"checked": 0, "reason": "chain_unavailable"}

    txs = chain_repo.list_sent_txs()
    mined = 0
    failed = 0
    for tx in txs:
        tx_hash = tx.get("tx_hash")
        if not tx_hash:
            continue
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
        except Exception:
            continue  # not mined yet
        if receipt is None:
            continue
        status = "mined" if receipt.get("status") == 1 else "failed"
        chain_repo.update_tx(tx["idempotency_key"], {"status": status, "gas_used": receipt.get("gasUsed")})
        if status == "mined":
            mined += 1
        else:
            failed += 1
    return {"checked": len(txs), "mined": mined, "failed": failed}
