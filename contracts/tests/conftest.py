"""Shared pytest fixtures for the Virasat contract test suite.

Everything runs against an in-memory eth-tester (py-evm) chain via
`web3[tester]` -- there is no real network involved. Contracts are compiled
fresh (via py-solc-x, same settings as scripts/compile.py) once per test
session and redeployed per-test so each test starts from a clean chain state.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Callable

import pytest
import solcx
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_abi import encode as abi_encode
from eth_utils import keccak
from web3 import Web3
from eth_tester import EthereumTester, PyEVMBackend
from web3.providers.eth_tester import EthereumTesterProvider

CONTRACTS_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = CONTRACTS_DIR / "src"
NODE_MODULES = CONTRACTS_DIR / "node_modules"
SOLC_VERSION = "0.8.26"

DOMAIN_NAME = "PaytmVirasat"
DOMAIN_VERSION = "1"

# A short-but-not-degenerate period so tests can exercise the inactivity gate
# and the challenge window without waiting around; MIN_PERIOD enforces vaults
# can't be created with anything shorter than this.
MIN_PERIOD = 5


# ---------------------------------------------------------------------------
# Compilation (once per test session)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def compiled_contracts() -> dict:
    installed = [str(v) for v in solcx.get_installed_solc_versions()]
    if SOLC_VERSION not in installed:
        solcx.install_solc(SOLC_VERSION)
    solcx.set_solc_version(SOLC_VERSION)

    sources = {}
    for filename in ["VirasatRegistry.sol", "NomineeCredential.sol", "ClaimLedger.sol"]:
        sources[f"src/{filename}"] = {"content": (SRC_DIR / filename).read_text(encoding="utf-8")}

    input_json = {
        "language": "Solidity",
        "sources": sources,
        "settings": {
            "remappings": ["@openzeppelin/=node_modules/@openzeppelin/"],
            "optimizer": {"enabled": True, "runs": 200},
            "viaIR": True,
            "outputSelection": {"*": {"*": ["abi", "evm.bytecode.object", "evm.deployedBytecode.object"]}},
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
        pytest.exit("Solidity compilation failed, see errors above.")

    result = {}
    for name in ["VirasatRegistry", "NomineeCredential", "ClaimLedger"]:
        data = output["contracts"][f"src/{name}.sol"][name]
        result[name] = {
            "abi": data["abi"],
            "bytecode": "0x" + data["evm"]["bytecode"]["object"],
        }
    return result


# ---------------------------------------------------------------------------
# Chain / accounts
# ---------------------------------------------------------------------------


@pytest.fixture()
def tester():
    return EthereumTester(backend=PyEVMBackend())


@pytest.fixture()
def w3(tester) -> Web3:
    return Web3(EthereumTesterProvider(tester))


class Accounts:
    """Funded, tx-sending accounts (managed by eth-tester) plus arbitrary
    off-chain keypairs (owner/guardians/nominees) that only ever sign
    EIP-712 messages -- exactly like the real custodial-EOA design, where
    only the relayer submits transactions."""

    def __init__(self, w3: Web3):
        funded = w3.eth.accounts
        self.deployer = funded[0]
        self.relayer = funded[1]
        self.stranger = funded[2]  # a funded account that is not the relayer

        self.owner = Account.create()
        self.guardian1 = Account.create()
        self.guardian2 = Account.create()
        self.guardian3 = Account.create()
        self.nominee1 = Account.create()
        self.nominee2 = Account.create()


@pytest.fixture()
def accounts(w3) -> Accounts:
    return Accounts(w3)


# ---------------------------------------------------------------------------
# Contract deployment
# ---------------------------------------------------------------------------


class Deployment:
    def __init__(self, w3: Web3, registry, credential, ledger):
        self.w3 = w3
        self.registry = registry
        self.credential = credential
        self.ledger = ledger


def _deploy(w3: Web3, abi, bytecode, args, sender):
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = contract.constructor(*args).transact({"from": sender})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return w3.eth.contract(address=receipt["contractAddress"], abi=abi)


@pytest.fixture()
def deployment(w3, accounts, compiled_contracts) -> Deployment:
    reg_art = compiled_contracts["VirasatRegistry"]
    cred_art = compiled_contracts["NomineeCredential"]
    ledger_art = compiled_contracts["ClaimLedger"]

    registry = _deploy(w3, reg_art["abi"], reg_art["bytecode"], [accounts.deployer, MIN_PERIOD], accounts.deployer)
    credential = _deploy(w3, cred_art["abi"], cred_art["bytecode"], [registry.address], accounts.deployer)
    ledger = _deploy(
        w3, ledger_art["abi"], ledger_art["bytecode"], [accounts.deployer, accounts.relayer], accounts.deployer
    )

    registry.functions.setCredential(credential.address).transact({"from": accounts.deployer})
    registry.functions.setRelayer(accounts.relayer).transact({"from": accounts.deployer})

    return Deployment(w3, registry, credential, ledger)


# ---------------------------------------------------------------------------
# EIP-712 signing helpers (mirrors eth_account.messages.encode_typed_data as
# described in Implementation_Plan.md §10.1 / §13.1)
# ---------------------------------------------------------------------------


class Signer:
    """Builds the exact typed-data structures VirasatRegistry expects and
    signs them with a given eth_account LocalAccount. `chain_id` and
    `verifying_contract` can be overridden per-call to construct deliberately
    *wrong* signatures for negative tests."""

    def __init__(self, chain_id: int, verifying_contract: str):
        self.chain_id = chain_id
        self.verifying_contract = verifying_contract

    def _domain(self, chain_id=None, verifying_contract=None):
        return {
            "name": DOMAIN_NAME,
            "version": DOMAIN_VERSION,
            "chainId": chain_id if chain_id is not None else self.chain_id,
            "verifyingContract": verifying_contract or self.verifying_contract,
        }

    def _sign(self, types, primary_type, message, account, *, chain_id=None, verifying_contract=None):
        full_message = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                **types,
            },
            "domain": self._domain(chain_id, verifying_contract),
            "primaryType": primary_type,
            "message": message,
        }
        signable = encode_typed_data(full_message=full_message)
        signed = Account.sign_message(signable, account.key)
        return signed.signature

    @staticmethod
    def guardians_hash(guardians: list[str]) -> bytes:
        return keccak(abi_encode(["address[]"], [guardians]))

    @staticmethod
    def nominees_hash(nominees: list[str], share_bps: list[int]) -> bytes:
        return keccak(abi_encode(["address[]", "uint16[]"], [nominees, share_bps]))

    def create_vault(
        self,
        account,
        *,
        owner,
        manifest_hash,
        inactivity_period,
        challenge_period,
        threshold,
        guardians,
        nominees,
        share_bps,
        nonce,
        deadline,
        chain_id=None,
        verifying_contract=None,
    ) -> bytes:
        types = {
            "CreateVault": [
                {"name": "owner", "type": "address"},
                {"name": "manifestHash", "type": "bytes32"},
                {"name": "inactivityPeriod", "type": "uint32"},
                {"name": "challengePeriod", "type": "uint32"},
                {"name": "threshold", "type": "uint8"},
                {"name": "guardiansHash", "type": "bytes32"},
                {"name": "nomineesHash", "type": "bytes32"},
                {"name": "nonce", "type": "uint256"},
                {"name": "deadline", "type": "uint256"},
            ]
        }
        message = {
            "owner": owner,
            "manifestHash": manifest_hash,
            "inactivityPeriod": inactivity_period,
            "challengePeriod": challenge_period,
            "threshold": threshold,
            "guardiansHash": self.guardians_hash(guardians),
            "nomineesHash": self.nominees_hash(nominees, share_bps),
            "nonce": nonce,
            "deadline": deadline,
        }
        return self._sign(
            types, "CreateVault", message, account, chain_id=chain_id, verifying_contract=verifying_contract
        )

    def update_manifest(self, account, *, vault_id, manifest_hash, nonce, deadline, chain_id=None):
        types = {
            "UpdateManifest": [
                {"name": "vaultId", "type": "uint256"},
                {"name": "manifestHash", "type": "bytes32"},
                {"name": "nonce", "type": "uint256"},
                {"name": "deadline", "type": "uint256"},
            ]
        }
        message = {"vaultId": vault_id, "manifestHash": manifest_hash, "nonce": nonce, "deadline": deadline}
        return self._sign(types, "UpdateManifest", message, account, chain_id=chain_id)

    def cancel_release(self, account, *, vault_id, epoch, nonce, deadline, chain_id=None):
        types = {
            "CancelRelease": [
                {"name": "vaultId", "type": "uint256"},
                {"name": "epoch", "type": "uint16"},
                {"name": "nonce", "type": "uint256"},
                {"name": "deadline", "type": "uint256"},
            ]
        }
        message = {"vaultId": vault_id, "epoch": epoch, "nonce": nonce, "deadline": deadline}
        return self._sign(types, "CancelRelease", message, account, chain_id=chain_id)

    def attest_death(self, account, *, vault_id, death_cert_hash, epoch, deadline, chain_id=None):
        types = {
            "AttestDeath": [
                {"name": "vaultId", "type": "uint256"},
                {"name": "deathCertHash", "type": "bytes32"},
                {"name": "epoch", "type": "uint16"},
                {"name": "deadline", "type": "uint256"},
            ]
        }
        message = {"vaultId": vault_id, "deathCertHash": death_cert_hash, "epoch": epoch, "deadline": deadline}
        return self._sign(types, "AttestDeath", message, account, chain_id=chain_id)

    def set_guardians(self, account, *, vault_id, guardians, threshold, nonce, deadline, chain_id=None):
        types = {
            "SetGuardians": [
                {"name": "vaultId", "type": "uint256"},
                {"name": "guardiansHash", "type": "bytes32"},
                {"name": "threshold", "type": "uint8"},
                {"name": "nonce", "type": "uint256"},
                {"name": "deadline", "type": "uint256"},
            ]
        }
        message = {
            "vaultId": vault_id,
            "guardiansHash": self.guardians_hash(guardians),
            "threshold": threshold,
            "nonce": nonce,
            "deadline": deadline,
        }
        return self._sign(types, "SetGuardians", message, account, chain_id=chain_id)

    def set_nominees(self, account, *, vault_id, nominees, share_bps, nonce, deadline, chain_id=None):
        types = {
            "SetNominees": [
                {"name": "vaultId", "type": "uint256"},
                {"name": "nomineesHash", "type": "bytes32"},
                {"name": "nonce", "type": "uint256"},
                {"name": "deadline", "type": "uint256"},
            ]
        }
        message = {
            "vaultId": vault_id,
            "nomineesHash": self.nominees_hash(nominees, share_bps),
            "nonce": nonce,
            "deadline": deadline,
        }
        return self._sign(types, "SetNominees", message, account, chain_id=chain_id)


@pytest.fixture()
def signer(w3, deployment) -> Signer:
    return Signer(chain_id=w3.eth.chain_id, verifying_contract=deployment.registry.address)


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------


def far_future_deadline() -> int:
    return int(time.time()) + 3600


def assert_custom_error(exc_info, error_signature: str) -> None:
    """Assert a `pytest.raises(TransactionFailed)` failure was caused by a
    specific Solidity custom error, e.g. `assert_custom_error(exc, "BadNonce()")`.

    eth-tester/py-evm doesn't decode custom errors back into names -- it
    surfaces the raw 4-byte selector embedded in the exception message as the
    repr of a bytes object (see tests/conftest.py's probing notes). We
    recompute the expected selector the same way solc does (keccak of the
    error signature, first 4 bytes) and check it appears in that message.
    """
    expected_selector = keccak(text=error_signature)[:4]
    message = str(exc_info.value)
    assert repr(expected_selector) in message, (
        f"expected revert with {error_signature} (selector {expected_selector.hex()}), got: {message}"
    )


def advance_time(w3: Web3, tester: EthereumTester, seconds: int) -> None:
    """Move the chain clock forward. eth-tester's time_travel sets the *next*
    block's timestamp, so this also mines a block."""
    now = w3.eth.get_block("latest")["timestamp"]
    tester.time_travel(now + seconds)


@pytest.fixture()
def create_default_vault(w3, tester, deployment, accounts, signer) -> Callable[..., int]:
    """Create a vault with sensible defaults (2-of-3 guardians, 2 nominees
    60/40) and return its vaultId. Individual tests override what they need
    to via kwargs."""

    def _create(
        *,
        inactivity_period=MIN_PERIOD,
        challenge_period=MIN_PERIOD,
        threshold=2,
        guardians=None,
        nominees=None,
        share_bps=None,
        manifest_hash=None,
        deadline=None,
    ):
        guardians = guardians or [accounts.guardian1.address, accounts.guardian2.address, accounts.guardian3.address]
        nominees = nominees or [accounts.nominee1.address, accounts.nominee2.address]
        share_bps = share_bps or [6000, 4000]
        manifest_hash = manifest_hash or keccak(text="manifest-v1")
        deadline = deadline or far_future_deadline()
        nonce = deployment.registry.functions.nonces(accounts.owner.address).call()

        sig = signer.create_vault(
            accounts.owner,
            owner=accounts.owner.address,
            manifest_hash=manifest_hash,
            inactivity_period=inactivity_period,
            challenge_period=challenge_period,
            threshold=threshold,
            guardians=guardians,
            nominees=nominees,
            share_bps=share_bps,
            nonce=nonce,
            deadline=deadline,
        )

        req = (
            accounts.owner.address,
            manifest_hash,
            inactivity_period,
            challenge_period,
            threshold,
            guardians,
            nominees,
            share_bps,
            nonce,
            deadline,
        )
        tx_hash = deployment.registry.functions.createVault(req, sig).transact({"from": accounts.relayer})
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        logs = deployment.registry.events.VaultCreated().process_receipt(receipt)
        return logs[0]["args"]["vaultId"]

    return _create
