"""Web3 connection + contract loading.

Degrades gracefully: if SEPOLIA_RPC_URL / contract addresses / ABI artifact
files aren't available yet (e.g. the contracts-building agent hasn't
finished, or this is a bare dev sandbox), every getter here returns None and
logs a single clear warning instead of raising at import time. Callers
(routers, relayer, event_sync) must check for None and respond with a 503 /
skip-gracefully rather than crash.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

CHAIN_ARTIFACTS_DIR = Path(__file__).resolve().parent.parent.parent / "chain_artifacts"

# Contract name -> (settings attribute holding its deployed address, artifact file stem candidates)
_CONTRACTS: dict[str, tuple[str, list[str]]] = {
    "registry": ("REGISTRY_ADDRESS", ["VirasatRegistry", "Registry"]),
    "credential": ("CREDENTIAL_ADDRESS", ["NomineeCredential", "Credential"]),
    "ledger": ("LEDGER_ADDRESS", ["ClaimLedger", "Ledger"]),
}


@lru_cache
def get_w3():
    if not settings.SEPOLIA_RPC_URL:
        logger.warning("chain_not_configured", hint="SEPOLIA_RPC_URL is not set -- chain calls will be skipped.")
        return None
    try:
        from web3 import Web3

        for url in [settings.SEPOLIA_RPC_URL, settings.SEPOLIA_RPC_FALLBACK]:
            if not url:
                continue
            try:
                w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 10}))
                if w3.is_connected():
                    return w3
                logger.warning("rpc_unreachable", url=url)
            except Exception:
                logger.warning("rpc_connect_failed", url=url)
        logger.warning("chain_all_rpcs_failed")
        return None
    except Exception:
        logger.exception("web3_init_failed")
        return None


def _load_abi(stems: list[str]) -> Optional[list[dict]]:
    if not CHAIN_ARTIFACTS_DIR.exists():
        return None
    for stem in stems:
        for candidate in (CHAIN_ARTIFACTS_DIR / f"{stem}.json", CHAIN_ARTIFACTS_DIR / f"{stem.lower()}.json"):
            if candidate.exists():
                try:
                    data = json.loads(candidate.read_text(encoding="utf-8"))
                except Exception:
                    logger.warning("chain_artifact_unreadable", path=str(candidate))
                    continue
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "abi" in data:
                    return data["abi"]
    return None


def _artifact_address(stems: list[str]) -> Optional[str]:
    if not CHAIN_ARTIFACTS_DIR.exists():
        return None
    for stem in stems:
        candidate = CHAIN_ARTIFACTS_DIR / f"{stem}.json"
        if candidate.exists():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(data, dict):
                for key in ("address", "deployedTo", "deployed_to"):
                    if data.get(key):
                        return data[key]
    # also try deployments/sepolia.json style bundle, if the contracts agent dropped one in
    bundle = CHAIN_ARTIFACTS_DIR / "sepolia.json"
    if bundle.exists():
        try:
            data = json.loads(bundle.read_text(encoding="utf-8"))
            addresses = data.get("addresses", {})
            for stem in stems:
                if stem in addresses:
                    return addresses[stem]
        except Exception:
            pass
    return None


@lru_cache
def get_contract(name: str):
    """Returns a web3 Contract instance for 'registry' | 'credential' | 'ledger', or None."""
    if name not in _CONTRACTS:
        raise ValueError(f"Unknown contract name {name!r}")

    w3 = get_w3()
    if w3 is None:
        return None

    setting_attr, stems = _CONTRACTS[name]
    address = getattr(settings, setting_attr, None) or _artifact_address(stems)
    abi = _load_abi(stems)

    if not address or not abi:
        logger.warning(
            "contract_not_available",
            contract=name,
            has_address=bool(address),
            has_abi=bool(abi),
            hint="Missing env address or ABI JSON in app/chain_artifacts/ -- chain calls for this contract will no-op.",
        )
        return None

    try:
        from web3 import Web3

        return w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)
    except Exception:
        logger.exception("contract_load_failed", contract=name)
        return None


def is_chain_available() -> bool:
    return get_w3() is not None and get_contract("registry") is not None
