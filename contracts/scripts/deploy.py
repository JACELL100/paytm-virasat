"""Deploy VirasatRegistry, NomineeCredential and ClaimLedger to Sepolia.

Usage:
    python scripts/deploy.py --network sepolia --min-period 60

Reads `SEPOLIA_RPC_URL` and `DEPLOYER_PRIVATE_KEY` (and `RELAYER_ADDRESS`) from
`contracts/.env`. The deployer key is intentionally distinct from the relayer key
(see contracts/.env.example): the deployer only needs to exist long enough to run
this script and the setup calls, then registry ownership can be moved to a cold
key with `registry.transferOwnership(...)`.

Deploy order (constructor design note):
    1. VirasatRegistry(initialOwner=deployer, minPeriod)
       -- deployed first because NomineeCredential's constructor takes the
          registry address as an immutable, so the registry must already exist.
    2. NomineeCredential(registry=<registry address>)
    3. registry.setCredential(credential)   -- wires the registry -> credential link
       registry.setRelayer(RELAYER_ADDRESS) -- the only address allowed through
                                                onlyRelayer entrypoints
    4. ClaimLedger(initialOwner=deployer, relayer=RELAYER_ADDRESS)
    5. Write deployments/<network>.json with addresses, deploying block numbers,
       and a timestamp. Copy is not needed for the backend (that only needs the
       ABI, produced by compile.py); this file is the human/ops record of what's
       live where.

This script is NOT executed against live Sepolia as part of building it (no funded
deployer key exists yet in this environment) -- it is meant to be correct and
ready to run once `contracts/.env` has real values.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
import os

from eth_account import Account
from web3 import Web3

CONTRACTS_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = CONTRACTS_DIR / "artifacts"
DEPLOYMENTS_DIR = CONTRACTS_DIR / "deployments"

NETWORK_CHAIN_IDS = {
    "sepolia": 11155111,
}


def load_artifact(name: str) -> dict:
    path = ARTIFACTS_DIR / f"{name}.json"
    if not path.exists():
        print(
            f"ERROR: {path} not found. Run `python scripts/compile.py` first.",
            file=sys.stderr,
        )
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def build_and_send(w3: Web3, acct, *, to=None, data: bytes, nonce: int, gas_limit: int | None = None) -> dict:
    """Build an EIP-1559 tx (see backend §8.7 relayer design for the same fee
    pattern), sign it and send it. Returns the mined receipt."""
    latest = w3.eth.get_block("latest")
    base_fee = latest["baseFeePerGas"]
    priority_fee = w3.eth.max_priority_fee
    max_fee = 2 * base_fee + priority_fee

    tx = {
        "chainId": w3.eth.chain_id,
        "from": acct.address,
        "nonce": nonce,
        "maxPriorityFeePerGas": priority_fee,
        "maxFeePerGas": max_fee,
        "data": data,
    }
    if to is not None:
        tx["to"] = to

    if gas_limit is None:
        gas_limit = w3.eth.estimate_gas(tx)
    tx["gas"] = int(gas_limit * 1.2)  # headroom for estimation drift

    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
    if receipt["status"] != 1:
        raise RuntimeError(f"Transaction reverted: {tx_hash.hex()}")
    return receipt


def deploy_contract(w3: Web3, acct, artifact: dict, constructor_args: list, nonce: int) -> tuple[str, dict]:
    contract = w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
    tx_data = contract.constructor(*constructor_args).build_transaction({"from": acct.address})["data"]
    receipt = build_and_send(w3, acct, to=None, data=Web3.to_bytes(hexstr=tx_data), nonce=nonce)
    address = receipt["contractAddress"]
    return address, receipt


def call_write(w3: Web3, acct, address: str, artifact: dict, fn_name: str, args: list, nonce: int) -> dict:
    contract = w3.eth.contract(address=address, abi=artifact["abi"])
    tx_data = getattr(contract.functions, fn_name)(*args).build_transaction({"from": acct.address})["data"]
    return build_and_send(w3, acct, to=address, data=Web3.to_bytes(hexstr=tx_data), nonce=nonce)


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy Paytm Virasat contracts")
    parser.add_argument("--network", default="sepolia", choices=list(NETWORK_CHAIN_IDS.keys()))
    parser.add_argument(
        "--min-period",
        type=int,
        default=60,
        help="MIN_PERIOD (seconds) for VirasatRegistry's inactivity/challenge floor. "
        "60 for the demo (Demo Mode time-warp); use something like 30 days (2592000) in prod.",
    )
    args = parser.parse_args()

    load_dotenv(CONTRACTS_DIR / ".env")

    rpc_url = os.environ.get("SEPOLIA_RPC_URL")
    deployer_key = os.environ.get("DEPLOYER_PRIVATE_KEY")
    relayer_address = os.environ.get("RELAYER_ADDRESS")

    missing = [
        name
        for name, val in [
            ("SEPOLIA_RPC_URL", rpc_url),
            ("DEPLOYER_PRIVATE_KEY", deployer_key),
            ("RELAYER_ADDRESS", relayer_address),
        ]
        if not val
    ]
    if missing:
        print(
            f"ERROR: missing required env vars in contracts/.env: {', '.join(missing)}. "
            "See contracts/.env.example.",
            file=sys.stderr,
        )
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    acct = Account.from_key(deployer_key)

    expected_chain_id = NETWORK_CHAIN_IDS[args.network]
    actual_chain_id = w3.eth.chain_id
    if actual_chain_id != expected_chain_id:
        print(
            f"ERROR: connected chainId {actual_chain_id} != expected {expected_chain_id} for --network {args.network}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Deployer: {acct.address}")
    print(f"Relayer:  {relayer_address}")
    print(f"Network:  {args.network} (chainId {actual_chain_id})")

    nonce = w3.eth.get_transaction_count(acct.address, "pending")

    registry_artifact = load_artifact("VirasatRegistry")
    credential_artifact = load_artifact("NomineeCredential")
    ledger_artifact = load_artifact("ClaimLedger")

    # 1. VirasatRegistry(initialOwner=deployer, minPeriod)
    print("\nDeploying VirasatRegistry ...")
    registry_address, registry_receipt = deploy_contract(
        w3, acct, registry_artifact, [acct.address, args.min_period], nonce
    )
    nonce += 1
    print(f"  VirasatRegistry deployed at {registry_address} (block {registry_receipt['blockNumber']})")

    # 2. NomineeCredential(registry=registry_address)
    print("Deploying NomineeCredential ...")
    credential_address, credential_receipt = deploy_contract(
        w3, acct, credential_artifact, [registry_address], nonce
    )
    nonce += 1
    print(f"  NomineeCredential deployed at {credential_address} (block {credential_receipt['blockNumber']})")

    # 3. Wire the registry: setCredential + setRelayer
    print("Calling registry.setCredential(...) ...")
    call_write(w3, acct, registry_address, registry_artifact, "setCredential", [credential_address], nonce)
    nonce += 1

    print("Calling registry.setRelayer(...) ...")
    call_write(
        w3,
        acct,
        registry_address,
        registry_artifact,
        "setRelayer",
        [Web3.to_checksum_address(relayer_address)],
        nonce,
    )
    nonce += 1

    # 4. ClaimLedger(initialOwner=deployer, relayer=RELAYER_ADDRESS)
    print("Deploying ClaimLedger ...")
    ledger_address, ledger_receipt = deploy_contract(
        w3, acct, ledger_artifact, [acct.address, Web3.to_checksum_address(relayer_address)], nonce
    )
    nonce += 1
    print(f"  ClaimLedger deployed at {ledger_address} (block {ledger_receipt['blockNumber']})")

    # 5. Write deployments/<network>.json
    DEPLOYMENTS_DIR.mkdir(parents=True, exist_ok=True)
    deployment = {
        "network": args.network,
        "chainId": actual_chain_id,
        "deployer": acct.address,
        "relayer": relayer_address,
        "minPeriod": args.min_period,
        "deployedAt": int(time.time()),
        "contracts": {
            "VirasatRegistry": {
                "address": registry_address,
                "deployBlock": registry_receipt["blockNumber"],
                "txHash": registry_receipt["transactionHash"].hex(),
            },
            "NomineeCredential": {
                "address": credential_address,
                "deployBlock": credential_receipt["blockNumber"],
                "txHash": credential_receipt["transactionHash"].hex(),
            },
            "ClaimLedger": {
                "address": ledger_address,
                "deployBlock": ledger_receipt["blockNumber"],
                "txHash": ledger_receipt["transactionHash"].hex(),
            },
        },
    }
    out_path = DEPLOYMENTS_DIR / f"{args.network}.json"
    out_path.write_text(json.dumps(deployment, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")
    print(
        "\nNext steps:\n"
        "  - Put REGISTRY_ADDRESS / CREDENTIAL_ADDRESS / LEDGER_ADDRESS / REGISTRY_DEPLOY_BLOCK "
        "into backend/.env\n"
        "  - Optionally run scripts/verify_etherscan.py for each contract\n"
        "  - Once setup is confirmed, consider registry.transferOwnership(<cold key>)"
    )


if __name__ == "__main__":
    main()
