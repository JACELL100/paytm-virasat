# Paytm Virasat — Smart Contracts (`contracts/`)

Solidity sources for the three contracts backing Paytm Virasat's Legacy Vault
and Claim Co-pilot flows, deployed to Sepolia:

- **`VirasatRegistry.sol`** — one registry, many vaults. Owns vault lifecycle
  (Active → Challenge → Released), guardian M-of-N attestation, EIP-712
  signature verification, and proof-of-life heartbeats.
- **`NomineeCredential.sol`** — soulbound (ERC-5192-style) ERC-721 minted to
  nominees on release. On-chain Base64 JSON `tokenURI` with an inline SVG,
  no personal data.
- **`ClaimLedger.sol`** — cheap, event-only anchor for claim-tracker status
  transitions, read back via `eth_getLogs`.

Everything here is compiled and tested with **Python only** (`py-solc-x` +
`web3.py` + `pytest`) — no Hardhat/Foundry/JS build tooling. `package.json`
exists solely to vendor `@openzeppelin/contracts` as a Solidity import source.

## Setup

```bash
cd contracts

# 1. Solidity dependency (OpenZeppelin Contracts v5, sources only)
npm install

# 2. Python environment (a local venv is used here; the user site works too,
#    just be consistent about which interpreter runs the scripts below)
python -m venv .venv
.venv/Scripts/activate        # Windows (PowerShell: .venv\Scripts\Activate.ps1)
# source .venv/bin/activate    # macOS/Linux
pip install -r requirements.txt
```

## Compile

```bash
python scripts/compile.py
```

Installs solc 0.8.26 (via `solcx.install_solc`, cached after the first run),
compiles all three contracts with the `@openzeppelin/=node_modules/@openzeppelin/`
import remapping, optimizer enabled (200 runs), `viaIR: true` (the registry's
`createVault` and the credential's `tokenURI` have enough local variables to
hit "stack too deep" under the legacy codegen). Writes one
`{contractName, sourceName, abi, bytecode, deployedBytecode, solcVersion}`
JSON file per contract to `contracts/artifacts/`, and copies the same files
into `backend/app/chain_artifacts/` so the FastAPI backend can load ABI +
bytecode without depending on this package.

## Test

```bash
pytest tests -q
```

Runs entirely against an in-memory `web3[tester]` chain (`eth-tester` +
`py-evm`) — no real network, no gas cost, no funded keys needed. 38 tests
across `tests/test_registry.py`, `tests/test_credential.py` and
`tests/test_ledger.py` cover every safety property called out in
Implementation_Plan.md §10.1 / §17:

- Inactivity gate (no attestation counts before the owner has been silent
  for `inactivityPeriod`)
- M-of-N guardian threshold before a Challenge starts
- Duplicate-attestation and mismatched-death-cert-hash rejection
- Owner cancel **and** any relayer-reported activity both auto-cancel a
  Challenge
- Epoch bump on cancel invalidates stale attestations (guardians must
  re-attest post-cancel)
- `finalizeRelease` only succeeds once the challenge window has actually
  elapsed, and only from `Challenge` state; anyone (not just the relayer)
  may call it
- Soulbound `NomineeCredential`: only the registry can mint, transfers and
  approvals always revert, `tokenURI` is valid on-chain Base64 JSON with no
  personal data
- EIP-712 signature integrity: replay rejection, wrong `chainId` rejection,
  expired-deadline rejection, wrong-signer rejection
- `onlyRelayer` enforced on every relayer-gated entrypoint on all three
  contracts

`tests/conftest.py` holds the shared fixtures: it compiles the contracts
once per session, deploys a fresh Registry/Credential/Ledger per test, and
provides a `Signer` helper that builds the exact EIP-712 typed-data
structures the contract expects (mirroring how the backend's
`services/chain/eip712.py` will sign owner/guardian intents with
`eth_account.messages.encode_typed_data`).

## Deploy (Sepolia)

```bash
cp .env.example .env   # fill in SEPOLIA_RPC_URL, DEPLOYER_PRIVATE_KEY, RELAYER_ADDRESS, ...
python scripts/deploy.py --network sepolia --min-period 60
```

Deploy order (see the docstring in `scripts/deploy.py` for the full
rationale):

1. `VirasatRegistry(initialOwner=deployer, minPeriod)`
2. `NomineeCredential(registry=<registry address>)` — the credential's
   `registry` is an immutable set at construction, so the registry must
   exist first.
3. `registry.setCredential(credential)` and `registry.setRelayer(RELAYER_ADDRESS)`
4. `ClaimLedger(initialOwner=deployer, relayer=RELAYER_ADDRESS)`
5. Write `deployments/sepolia.json` with addresses, deploy block numbers,
   tx hashes and a timestamp.

Uses EIP-1559 fees (`maxPriorityFeePerGas = w3.eth.max_priority_fee`,
`maxFeePerGas = 2 * baseFee + priority`), the same pattern
Implementation_Plan.md §8.7 specifies for the backend relayer.

This script has **not** been run against live Sepolia as part of building
it — there is no funded deployer key in this environment. It's meant to be
correct and ready to run once `contracts/.env` has real values funded with
~0.1–0.3 SepoliaETH.

After deploying, copy `REGISTRY_ADDRESS` / `CREDENTIAL_ADDRESS` /
`LEDGER_ADDRESS` / `REGISTRY_DEPLOY_BLOCK` from `deployments/sepolia.json`
into `backend/.env`, and consider moving the registry's `owner` to a cold
key with `registry.transferOwnership(...)` — the deployer key only needs to
exist long enough to deploy and run the setup calls above; it is
intentionally separate from the relayer key.

## Verify (optional)

```bash
python scripts/verify_etherscan.py --all
```

Submits standard-json-input source verification to Etherscan API V2. This
is a structural skeleton (see the module docstring) — real-world
verification is fiddly (constructor-argument ABI encoding, exact solc
commit hash, metadata hashes) and this script doesn't try to paper over
every edge case.

## Environment variables (`contracts/.env`)

See `.env.example`. Summary:

| Var | Purpose |
|---|---|
| `SEPOLIA_RPC_URL` | Alchemy (or other) Sepolia RPC endpoint |
| `DEPLOYER_PRIVATE_KEY` | Deploys the contracts; separate from the relayer key |
| `RELAYER_ADDRESS` | Wired into `registry.setRelayer(...)` and `ClaimLedger`'s constructor |
| `ETHERSCAN_API_KEY` | For `scripts/verify_etherscan.py` |
| `MIN_PERIOD` | Floor (seconds) for `inactivityPeriod`/`challengePeriod`; 60 for the demo, ~30 days in production |

## Trust model

The relayer is the **only** address allowed to call any relayer-gated
entrypoint (`createVault`, `updateManifest`, `setGuardians`, `setNominees`,
`cancelRelease`, `heartbeatBatch`, `attestDeath`), but it can never forge an
owner's or a guardian's intent: every one of those calls carries an EIP-712
signature (with nonce/current-on-chain-nonce binding, an explicit
`deadline`, and the domain's `chainId`) that the contract verifies on-chain
against the exact address that intent claims to come from. The relayer just
relays already-signed intents and pays the gas — it has no way to originate
one itself. The one thing it genuinely holds power over is **timing**: it
could delay or withhold a heartbeat that would otherwise refresh
`lastHeartbeat`, or delay relaying a guardian's attestation. That's why the
protocol doesn't rely on the relayer alone for owner safety — it needs the
M-of-N guardian threshold *and* the inactivity gate *and* a challenge window
*and* the owner's own cancel right (or any fresh activity at all) before a
release can ever finalize. A dishonest or negligent relayer can slow things
down; it cannot single-handedly manufacture a release, and it cannot stop a
genuinely active owner or an engaged guardian set from cancelling one.
