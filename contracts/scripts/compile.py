"""Compile the Virasat Solidity contracts with py-solc-x.

Usage:
    python scripts/compile.py

Installs solc 0.8.26 (cached by solcx after the first run), compiles every
contract in `contracts/src/`, applies the `@openzeppelin/=node_modules/@openzeppelin/`
import remapping, enables the optimizer (200 runs), and writes one
`{ "abi": [...], "bytecode": "0x...", "deployedBytecode": "0x...", "contractName": ... }`
JSON file per contract to `contracts/artifacts/`. Each artifact is also copied to
`backend/app/chain_artifacts/` so the FastAPI backend can load the ABI + bytecode
without depending on the contracts/ package.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import solcx

SOLC_VERSION = "0.8.26"

CONTRACTS_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = CONTRACTS_DIR / "src"
ARTIFACTS_DIR = CONTRACTS_DIR / "artifacts"
NODE_MODULES = CONTRACTS_DIR / "node_modules"

BACKEND_ARTIFACTS_DIR = CONTRACTS_DIR.parent / "backend" / "app" / "chain_artifacts"

# contracts/src/<file>.sol -> the single top-level contract we want to export from it.
SOURCE_FILES = [
    "VirasatRegistry.sol",
    "NomineeCredential.sol",
    "ClaimLedger.sol",
]


def ensure_solc() -> None:
    installed = [str(v) for v in solcx.get_installed_solc_versions()]
    if SOLC_VERSION not in installed:
        print(f"Installing solc {SOLC_VERSION} ...")
        solcx.install_solc(SOLC_VERSION)
    solcx.set_solc_version(SOLC_VERSION)


def compile_all() -> dict:
    if not NODE_MODULES.exists():
        print(
            "ERROR: node_modules/ not found. Run `npm install` in contracts/ first "
            "(it vendors @openzeppelin/contracts as a Solidity source dependency).",
            file=sys.stderr,
        )
        sys.exit(1)

    sources = {}
    for filename in SOURCE_FILES:
        path = SRC_DIR / filename
        sources[f"src/{filename}"] = {"content": path.read_text(encoding="utf-8")}

    # Relative remapping (resolved against base_path below), matching the exact
    # remapping the plan specifies: @openzeppelin/=node_modules/@openzeppelin/
    remappings = ["@openzeppelin/=node_modules/@openzeppelin/"]

    input_json = {
        "language": "Solidity",
        "sources": sources,
        "settings": {
            "remappings": remappings,
            "optimizer": {"enabled": True, "runs": 200},
            # createVault/tokenURI have enough local variables to hit "stack too
            # deep" under the legacy codegen; the IR pipeline avoids that.
            "viaIR": True,
            "outputSelection": {
                "*": {
                    "*": [
                        "abi",
                        "evm.bytecode.object",
                        "evm.deployedBytecode.object",
                        "metadata",
                    ]
                }
            },
        },
    }

    output = solcx.compile_standard(
        input_json,
        base_path=str(CONTRACTS_DIR).replace("\\", "/"),
        allow_paths=str(NODE_MODULES).replace("\\", "/"),
        solc_version=SOLC_VERSION,
    )

    errors = [e for e in output.get("errors", []) if e.get("severity") == "error"]
    if errors:
        for e in errors:
            print(e.get("formattedMessage", e), file=sys.stderr)
        print("Compilation failed.", file=sys.stderr)
        sys.exit(1)

    warnings = [e for e in output.get("errors", []) if e.get("severity") != "error"]
    for w in warnings:
        print(w.get("formattedMessage", w), file=sys.stderr)

    return output


def write_artifacts(output: dict) -> list[str]:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    BACKEND_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    written = []
    for source_path, contracts in output["contracts"].items():
        # Skip imported/library sources pulled in transitively from node_modules
        # (OpenZeppelin's ERC721, ECDSA, etc.) -- we only want artifacts for our
        # own contracts.
        if not source_path.startswith("src/"):
            continue
        for contract_name, data in contracts.items():
            # A source file can also declare interfaces/libraries alongside its
            # main contract (e.g. INomineeCredential lives in VirasatRegistry.sol);
            # only emit the contract that matches the file's own basename.
            expected_stem = Path(source_path).stem
            if contract_name != expected_stem:
                continue

            abi = data["abi"]
            bytecode = "0x" + data["evm"]["bytecode"]["object"]
            deployed_bytecode = "0x" + data["evm"]["deployedBytecode"]["object"]

            artifact = {
                "contractName": contract_name,
                "sourceName": source_path,
                "abi": abi,
                "bytecode": bytecode,
                "deployedBytecode": deployed_bytecode,
                "solcVersion": SOLC_VERSION,
            }

            out_path = ARTIFACTS_DIR / f"{contract_name}.json"
            out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
            written.append(contract_name)

            backend_path = BACKEND_ARTIFACTS_DIR / f"{contract_name}.json"
            shutil.copyfile(out_path, backend_path)

            print(f"Wrote {out_path.relative_to(CONTRACTS_DIR)} (+ copy in backend/app/chain_artifacts/)")

    return written


def main() -> None:
    ensure_solc()
    output = compile_all()
    written = write_artifacts(output)
    expected = {Path(f).stem for f in SOURCE_FILES}
    missing = expected - set(written)
    if missing:
        print(f"WARNING: expected contracts not found in output: {missing}", file=sys.stderr)
        sys.exit(1)
    print(f"Compiled {len(written)} contracts: {', '.join(sorted(written))}")


if __name__ == "__main__":
    main()
