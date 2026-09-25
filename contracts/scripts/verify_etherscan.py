"""Verify the deployed contracts' source on Etherscan (Sepolia) using the
Etherscan API V2 "standard-json-input" verification endpoint.

This is a structural skeleton, not a bulletproof implementation: it shows the
right request shape (multi-file standard-json-input, matching exactly what
solc compiled so bytecode matches byte-for-byte) and polls the check-status
endpoint, but real-world verification is fiddly (metadata hash mismatches,
library linking, etc.) and this script does not try to handle every edge case.

Usage:
    python scripts/verify_etherscan.py --contract VirasatRegistry
    python scripts/verify_etherscan.py --all

Reads ETHERSCAN_API_KEY from contracts/.env. Reads the deployed address from
contracts/deployments/<network>.json and constructor args from the same file
where available (constructor args must be ABI-encoded hex for the API; for
contracts with non-trivial constructor args you may need to fill these in by
hand -- see CONSTRUCTOR_ARGS_HEX below).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

CONTRACTS_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = CONTRACTS_DIR / "artifacts"
DEPLOYMENTS_DIR = CONTRACTS_DIR / "deployments"
SRC_DIR = CONTRACTS_DIR / "src"
NODE_MODULES = CONTRACTS_DIR / "node_modules"

# Etherscan API V2 is multichain: same host, chainid selects the network.
ETHERSCAN_API_URL = "https://api.etherscan.io/v2/api"
SEPOLIA_CHAIN_ID = 11155111
SOLC_VERSION = "0.8.26"

CONTRACT_FILES = {
    "VirasatRegistry": "VirasatRegistry.sol",
    "NomineeCredential": "NomineeCredential.sol",
    "ClaimLedger": "ClaimLedger.sol",
}

# ABI-encoded (hex, no 0x prefix) constructor args per contract. Fill these in
# manually after deploy if you want verification to include constructor
# argument matching -- deploy.py prints the values but does not ABI-encode
# them for you here, to keep this script's dependency footprint small.
CONSTRUCTOR_ARGS_HEX: dict[str, str] = {
    "VirasatRegistry": "",
    "NomineeCredential": "",
    "ClaimLedger": "",
}


def build_standard_json_input() -> dict:
    """Rebuild the exact standard-json-input used by compile.py, so the
    metadata hash embedded in bytecode matches what's on-chain."""
    sources = {}
    for fname in CONTRACT_FILES.values():
        path = SRC_DIR / fname
        sources[f"src/{fname}"] = {"content": path.read_text(encoding="utf-8")}

    return {
        "language": "Solidity",
        "sources": sources,
        "settings": {
            "optimizer": {"enabled": True, "runs": 200},
            "viaIR": True,
            "remappings": ["@openzeppelin/=node_modules/@openzeppelin/"],
            "outputSelection": {"*": {"*": ["abi", "evm.bytecode", "evm.deployedBytecode", "metadata"]}},
        },
    }


def verify_contract(api_key: str, network: str, contract_name: str) -> None:
    deployment_path = DEPLOYMENTS_DIR / f"{network}.json"
    if not deployment_path.exists():
        print(f"ERROR: {deployment_path} not found. Run scripts/deploy.py first.", file=sys.stderr)
        sys.exit(1)
    deployment = json.loads(deployment_path.read_text(encoding="utf-8"))
    address = deployment["contracts"][contract_name]["address"]

    source_file = CONTRACT_FILES[contract_name]
    standard_json = build_standard_json_input()

    payload = {
        "apikey": api_key,
        "chainid": SEPOLIA_CHAIN_ID,
        "module": "contract",
        "action": "verifysourcecode",
        "contractaddress": address,
        "sourceCode": json.dumps(standard_json),
        "codeformat": "solidity-standard-json-input",
        "contractname": f"src/{source_file}:{contract_name}",
        "compilerversion": f"v{SOLC_VERSION}+commit.8a97fa7a",  # pin to solc's exact commit hash for this version
        "constructorArguements": CONSTRUCTOR_ARGS_HEX.get(contract_name, ""),
    }

    print(f"Submitting {contract_name} ({address}) for verification ...")
    resp = requests.post(ETHERSCAN_API_URL, data=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    print(f"  submit response: {result}")

    if result.get("status") != "1":
        print(f"  submission failed: {result.get('result')}", file=sys.stderr)
        return

    guid = result["result"]
    print(f"  guid={guid}, polling status ...")
    for _ in range(10):
        time.sleep(5)
        status_resp = requests.get(
            ETHERSCAN_API_URL,
            params={
                "apikey": api_key,
                "chainid": SEPOLIA_CHAIN_ID,
                "module": "contract",
                "action": "checkverifystatus",
                "guid": guid,
            },
            timeout=30,
        )
        status = status_resp.json()
        print(f"  status: {status}")
        if status.get("result") not in ("Pending in queue",):
            break


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Virasat contracts on Etherscan (Sepolia)")
    parser.add_argument("--network", default="sepolia")
    parser.add_argument("--contract", choices=list(CONTRACT_FILES.keys()))
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    if not args.contract and not args.all:
        parser.error("pass --contract <name> or --all")

    load_dotenv(CONTRACTS_DIR / ".env")
    api_key = os.environ.get("ETHERSCAN_API_KEY")
    if not api_key:
        print("ERROR: ETHERSCAN_API_KEY not set in contracts/.env", file=sys.stderr)
        sys.exit(1)

    names = list(CONTRACT_FILES.keys()) if args.all else [args.contract]
    for name in names:
        verify_contract(api_key, args.network, name)


if __name__ == "__main__":
    main()
