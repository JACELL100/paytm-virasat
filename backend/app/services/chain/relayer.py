"""Nonce-locked relayer, per Implementation_Plan.md section 8.7.

One funded relayer EOA submits every on-chain transaction and pays gas. An
asyncio.Lock serialises nonce allocation (single Uvicorn worker, so this is
sufficient -- see section 4 decision #4). Every transaction is persisted in
`chain_txs` **before** sending, keyed by an idempotency key
(`kind:vault_id:epoch`), so a retried request never double-sends.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

from app.core.config import settings
from app.core.errors import ApiError
from app.core.logging import get_logger
from app.db.repos import chain as chain_repo
from app.services.chain.web3_client import get_w3

logger = get_logger(__name__)

LOW_BALANCE_THRESHOLD_WEI = int(0.02 * 10**18)  # 0.02 SepoliaETH


class Relayer:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._nonce: Optional[int] = None
        self._account = None

    def _ensure_account(self):
        if self._account is not None:
            return self._account
        if not settings.RELAYER_PRIVATE_KEY:
            return None
        from eth_account import Account

        self._account = Account.from_key(settings.RELAYER_PRIVATE_KEY)
        return self._account

    @property
    def address(self) -> Optional[str]:
        acct = self._ensure_account()
        return acct.address if acct else None

    def is_configured(self) -> bool:
        return get_w3() is not None and self._ensure_account() is not None

    async def _next_nonce(self, w3) -> int:
        async with self._lock:
            if self._nonce is None:
                self._nonce = w3.eth.get_transaction_count(self.address, "pending")
            else:
                self._nonce += 1
            return self._nonce

    def check_balance(self) -> dict[str, Any]:
        w3 = get_w3()
        acct = self._ensure_account()
        if w3 is None or acct is None:
            return {"configured": False, "balance_wei": None, "degraded": True}
        try:
            balance = w3.eth.get_balance(acct.address)
        except Exception:
            logger.warning("relayer_balance_check_failed")
            return {"configured": True, "balance_wei": None, "degraded": True}
        degraded = balance < LOW_BALANCE_THRESHOLD_WEI
        if degraded:
            logger.warning("relayer_low_balance", balance_wei=balance, address=acct.address)
        return {"configured": True, "balance_wei": balance, "degraded": degraded}

    def _fees(self, w3) -> dict[str, int]:
        try:
            base_fee = w3.eth.get_block("latest")["baseFeePerGas"]
            priority = w3.eth.max_priority_fee
        except Exception:
            # Fallback for chains/mocks without EIP-1559 fee history
            base_fee = w3.eth.gas_price
            priority = w3.to_wei(1, "gwei")
        max_fee = 2 * base_fee + priority
        return {"maxPriorityFeePerGas": priority, "maxFeePerGas": max_fee}

    async def send(
        self,
        *,
        kind: str,
        vault_id: Optional[str],
        idempotency_key: str,
        build_fn: Callable[[Any, dict], Any],
        payload: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Builds, signs and sends a transaction, with idempotency + nonce locking.

        `build_fn(contract_fn_target, fees) -> unsent web3 tx dict` is supplied
        by the caller (each API route knows which contract function to call).
        """
        existing = chain_repo.get_tx_by_idempotency_key(idempotency_key)
        if existing and existing.get("status") in ("sent", "mined"):
            return existing

        w3 = get_w3()
        acct = self._ensure_account()
        if w3 is None or acct is None:
            raise ApiError(
                "chain_not_configured",
                "Service unavailable",
                "Blockchain relayer is not configured (SEPOLIA_RPC_URL / RELAYER_PRIVATE_KEY).",
                503,
            )

        if existing is None:
            chain_repo.create_queued_tx(idempotency_key, kind, vault_id, payload or {})

        async with self._lock:
            nonce = w3.eth.get_transaction_count(acct.address, "pending") if self._nonce is None else self._nonce + 1
            self._nonce = nonce

            fees = self._fees(w3)
            try:
                tx = build_fn(w3, fees)
                tx["nonce"] = nonce
                tx["chainId"] = settings.CHAIN_ID
                tx.setdefault("from", acct.address)
                signed = acct.sign_transaction(tx)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                tx_hash_hex = tx_hash.hex() if isinstance(tx_hash, (bytes, bytearray)) else tx_hash
                chain_repo.update_tx(
                    idempotency_key,
                    {"status": "sent", "tx_hash": tx_hash_hex, "nonce": nonce},
                )
                logger.info("relayer_tx_sent", kind=kind, tx_hash=tx_hash_hex, nonce=nonce)
                return {"status": "sent", "tx_hash": tx_hash_hex, "nonce": nonce, "idempotency_key": idempotency_key}
            except Exception as exc:  # noqa: BLE001
                self._nonce = nonce - 1  # allow retry to reuse nonce
                chain_repo.update_tx(idempotency_key, {"status": "failed", "error": str(exc)})
                logger.exception("relayer_tx_failed", kind=kind)
                raise ApiError(
                    "chain_tx_failed", "Chain transaction failed", str(exc), 502
                ) from exc


_relayer: Optional[Relayer] = None


def get_relayer() -> Relayer:
    global _relayer
    if _relayer is None:
        _relayer = Relayer()
    return _relayer
