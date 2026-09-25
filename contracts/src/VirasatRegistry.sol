// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

interface INomineeCredential {
    function mint(address to, uint256 vaultId, uint16 shareBps) external returns (uint256);
}

/// @title VirasatRegistry
/// @notice One registry holds every vault (cheaper than a per-vault factory). Owners and
///         guardians never touch a wallet directly: each of them controls a custodial EOA
///         off-chain, and the *only* thing that key ever does is produce an EIP-712 signature
///         over an exact, typed intent. A single funded relayer address is the only account
///         allowed to submit transactions, but the relayer can never forge an owner's or a
///         guardian's intent -- every state-changing call is guarded by an on-chain signature
///         check against the address that intent claims to come from.
/// @dev Trust model: the relayer is trusted to *report* activity (heartbeats) honestly and to
///      relay signatures promptly. It cannot fabricate a signature, and if it withholds
///      heartbeats the M-of-N guardian threshold, the challenge window and the owner's own
///      cancel right still protect the owner.
contract VirasatRegistry is EIP712, Ownable {
    // ---------------------------------------------------------------------
    // Types
    // ---------------------------------------------------------------------

    enum State {
        None,
        Active,
        Challenge,
        Released,
        Revoked
    }

    struct Vault {
        address owner;
        bytes32 manifestHash; // keccak256(ciphertext of sealed manifest)
        uint64 lastHeartbeat;
        uint64 challengeEndsAt;
        uint32 inactivityPeriod; // seconds
        uint32 challengePeriod; // seconds
        uint16 epoch; // bumps on cancel -> invalidates stale attestations
        uint8 threshold; // M of N guardians
        uint8 attestCount;
        State state;
        bytes32 deathCertHash;
    }

    /// @dev Request payload for `createVault`. Guardians/nominees are passed in full here (the
    ///      contract needs the real arrays to set up storage); `guardiansHash`/`nomineesHash` in
    ///      the EIP-712 struct are commitments computed from these same arrays so the relayer
    ///      cannot substitute different guardians/nominees than the owner actually signed for.
    struct CreateVaultReq {
        address owner;
        bytes32 manifestHash;
        uint32 inactivityPeriod;
        uint32 challengePeriod;
        uint8 threshold;
        address[] guardians;
        address[] nominees;
        uint16[] shareBps; // basis points, must sum to 10000, parallel to `nominees`
        uint256 nonce;
        uint256 deadline;
    }

    // ---------------------------------------------------------------------
    // EIP-712 type hashes
    // ---------------------------------------------------------------------

    bytes32 private constant CREATE_VAULT_TYPEHASH = keccak256(
        "CreateVault(address owner,bytes32 manifestHash,uint32 inactivityPeriod,uint32 challengePeriod,uint8 threshold,bytes32 guardiansHash,bytes32 nomineesHash,uint256 nonce,uint256 deadline)"
    );
    bytes32 private constant UPDATE_MANIFEST_TYPEHASH =
        keccak256("UpdateManifest(uint256 vaultId,bytes32 manifestHash,uint256 nonce,uint256 deadline)");
    bytes32 private constant CANCEL_RELEASE_TYPEHASH =
        keccak256("CancelRelease(uint256 vaultId,uint16 epoch,uint256 nonce,uint256 deadline)");
    bytes32 private constant ATTEST_DEATH_TYPEHASH =
        keccak256("AttestDeath(uint256 vaultId,bytes32 deathCertHash,uint16 epoch,uint256 deadline)");
    bytes32 private constant SET_GUARDIANS_TYPEHASH = keccak256(
        "SetGuardians(uint256 vaultId,bytes32 guardiansHash,uint8 threshold,uint256 nonce,uint256 deadline)"
    );
    bytes32 private constant SET_NOMINEES_TYPEHASH =
        keccak256("SetNominees(uint256 vaultId,bytes32 nomineesHash,uint256 nonce,uint256 deadline)");

    // ---------------------------------------------------------------------
    // Storage
    // ---------------------------------------------------------------------

    /// @notice Minimum allowed value for `inactivityPeriod` / `challengePeriod`. 60s in the
    ///         hackathon demo deploy (Demo Mode time-warp), production deploys would set this to
    ///         something like 30 days.
    uint32 public immutable MIN_PERIOD;

    address public relayer;
    INomineeCredential public credential;
    uint256 public nextVaultId = 1;

    mapping(uint256 => Vault) public vaults;
    mapping(uint256 => mapping(address => bool)) public isGuardian;
    mapping(uint256 => address[]) private _guardianList; // kept so setGuardians can clear old entries
    mapping(uint256 => address[]) private _nominees;
    mapping(uint256 => uint16[]) private _shares; // basis points, sum = 10000
    mapping(uint256 => mapping(uint16 => mapping(address => bool))) public hasAttested; // vault -> epoch -> guardian
    mapping(address => uint256) public nonces; // owner-signed actions (global per signer, spans vaults)

    // ---------------------------------------------------------------------
    // Events
    // ---------------------------------------------------------------------

    event RelayerUpdated(address indexed relayer);
    event CredentialUpdated(address indexed credential);
    event VaultCreated(uint256 indexed vaultId, address indexed owner, bytes32 manifestHash);
    event Heartbeat(uint256 indexed vaultId, uint64 at);
    event ManifestUpdated(uint256 indexed vaultId, bytes32 manifestHash);
    event GuardiansSet(uint256 indexed vaultId, uint8 threshold, uint256 count);
    event NomineesSet(uint256 indexed vaultId, uint256 count);
    event DeathAttested(uint256 indexed vaultId, address indexed guardian, bytes32 deathCertHash, uint8 count);
    event ChallengeStarted(uint256 indexed vaultId, uint64 endsAt);
    event ReleaseCancelled(uint256 indexed vaultId, uint16 newEpoch, bool byActivity);
    event Released(uint256 indexed vaultId, uint64 at);

    // ---------------------------------------------------------------------
    // Errors
    // ---------------------------------------------------------------------

    error NotRelayer();
    error Expired();
    error BadNonce();
    error BadSignature();
    error PeriodTooShort();
    error BadThreshold();
    error BadShares();
    error VaultNotFound();
    error WrongState();
    error NotGuardian();
    error AlreadyAttested();
    error OwnerInactive();
    error OwnerStillActive();
    error DeathCertMismatch();
    error ChallengeNotEnded();
    error ZeroAddress();

    // ---------------------------------------------------------------------
    // Constructor / admin
    // ---------------------------------------------------------------------

    constructor(address initialOwner, uint32 minPeriod)
        EIP712("PaytmVirasat", "1")
        Ownable(initialOwner)
    {
        MIN_PERIOD = minPeriod;
    }

    modifier onlyRelayer() {
        if (msg.sender != relayer) revert NotRelayer();
        _;
    }

    function setRelayer(address r) external onlyOwner {
        if (r == address(0)) revert ZeroAddress();
        relayer = r;
        emit RelayerUpdated(r);
    }

    function setCredential(address c) external onlyOwner {
        if (c == address(0)) revert ZeroAddress();
        credential = INomineeCredential(c);
        emit CredentialUpdated(c);
    }

    // ---------------------------------------------------------------------
    // Owner actions (EIP-712 signed by the owner's custodial key, relayed)
    // ---------------------------------------------------------------------

    function createVault(CreateVaultReq calldata r, bytes calldata ownerSig) external onlyRelayer returns (uint256) {
        if (block.timestamp > r.deadline) revert Expired();
        if (r.nonce != nonces[r.owner]) revert BadNonce();
        if (r.inactivityPeriod < MIN_PERIOD || r.challengePeriod < MIN_PERIOD) revert PeriodTooShort();
        if (r.threshold == 0 || r.threshold > r.guardians.length) revert BadThreshold();
        if (r.nominees.length == 0 || r.nominees.length != r.shareBps.length) revert BadShares();
        _checkSharesSum(r.shareBps);

        bytes32 guardiansHash = keccak256(abi.encode(r.guardians));
        bytes32 nomineesHash = keccak256(abi.encode(r.nominees, r.shareBps));

        bytes32 structHash = keccak256(
            abi.encode(
                CREATE_VAULT_TYPEHASH,
                r.owner,
                r.manifestHash,
                r.inactivityPeriod,
                r.challengePeriod,
                r.threshold,
                guardiansHash,
                nomineesHash,
                r.nonce,
                r.deadline
            )
        );
        _verify(structHash, r.owner, ownerSig);
        nonces[r.owner]++;

        uint256 vaultId = nextVaultId++;
        vaults[vaultId] = Vault({
            owner: r.owner,
            manifestHash: r.manifestHash,
            lastHeartbeat: uint64(block.timestamp),
            challengeEndsAt: 0,
            inactivityPeriod: r.inactivityPeriod,
            challengePeriod: r.challengePeriod,
            epoch: 0,
            threshold: r.threshold,
            attestCount: 0,
            state: State.Active,
            deathCertHash: bytes32(0)
        });

        _setGuardianList(vaultId, r.guardians);
        _nominees[vaultId] = r.nominees;
        _shares[vaultId] = r.shareBps;

        emit VaultCreated(vaultId, r.owner, r.manifestHash);
        emit GuardiansSet(vaultId, r.threshold, r.guardians.length);
        emit NomineesSet(vaultId, r.nominees.length);
        return vaultId;
    }

    function updateManifest(uint256 vaultId, bytes32 newHash, uint256 deadline, bytes calldata ownerSig)
        external
        onlyRelayer
    {
        Vault storage v = _requireVault(vaultId);
        if (v.state != State.Active) revert WrongState();
        if (block.timestamp > deadline) revert Expired();

        uint256 nonce = nonces[v.owner];
        bytes32 structHash =
            keccak256(abi.encode(UPDATE_MANIFEST_TYPEHASH, vaultId, newHash, nonce, deadline));
        _verify(structHash, v.owner, ownerSig);
        nonces[v.owner]++;

        v.manifestHash = newHash;
        emit ManifestUpdated(vaultId, newHash);
    }

    function setGuardians(
        uint256 vaultId,
        address[] calldata g,
        uint8 threshold,
        uint256 deadline,
        bytes calldata ownerSig
    ) external onlyRelayer {
        Vault storage v = _requireVault(vaultId);
        if (v.state != State.Active) revert WrongState();
        if (block.timestamp > deadline) revert Expired();
        if (threshold == 0 || threshold > g.length) revert BadThreshold();

        uint256 nonce = nonces[v.owner];
        bytes32 guardiansHash = keccak256(abi.encode(g));
        bytes32 structHash = keccak256(
            abi.encode(SET_GUARDIANS_TYPEHASH, vaultId, guardiansHash, threshold, nonce, deadline)
        );
        _verify(structHash, v.owner, ownerSig);
        nonces[v.owner]++;

        _setGuardianList(vaultId, g);
        v.threshold = threshold;
        emit GuardiansSet(vaultId, threshold, g.length);
    }

    function setNominees(
        uint256 vaultId,
        address[] calldata n,
        uint16[] calldata shareBps,
        uint256 deadline,
        bytes calldata ownerSig
    ) external onlyRelayer {
        Vault storage v = _requireVault(vaultId);
        if (v.state != State.Active) revert WrongState();
        if (block.timestamp > deadline) revert Expired();
        if (n.length == 0 || n.length != shareBps.length) revert BadShares();
        _checkSharesSum(shareBps);

        uint256 nonce = nonces[v.owner];
        bytes32 nomineesHash = keccak256(abi.encode(n, shareBps));
        bytes32 structHash = keccak256(abi.encode(SET_NOMINEES_TYPEHASH, vaultId, nomineesHash, nonce, deadline));
        _verify(structHash, v.owner, ownerSig);
        nonces[v.owner]++;

        _nominees[vaultId] = n;
        _shares[vaultId] = shareBps;
        emit NomineesSet(vaultId, n.length);
    }

    function cancelRelease(uint256 vaultId, uint256 deadline, bytes calldata ownerSig) external onlyRelayer {
        Vault storage v = _requireVault(vaultId);
        if (v.state != State.Challenge) revert WrongState();
        if (block.timestamp > deadline) revert Expired();

        uint256 nonce = nonces[v.owner];
        bytes32 structHash =
            keccak256(abi.encode(CANCEL_RELEASE_TYPEHASH, vaultId, v.epoch, nonce, deadline));
        _verify(structHash, v.owner, ownerSig);
        nonces[v.owner]++;

        _cancelChallenge(vaultId, v, false);
    }

    // ---------------------------------------------------------------------
    // Proof of life (relayer attests off-chain Paytm activity)
    // ---------------------------------------------------------------------

    /// @notice Batched heartbeat. While Active it just refreshes `lastHeartbeat`. If a vault is
    ///         in Challenge, any reported activity is treated as proof the owner is alive and
    ///         auto-cancels the challenge (bumping the epoch so stale guardian attestations can
    ///         never be reused). Vaults that don't exist yet or are already Released/Revoked are
    ///         silently skipped so one bad id can't revert the whole batch.
    function heartbeatBatch(uint256[] calldata vaultIds) external onlyRelayer {
        for (uint256 i = 0; i < vaultIds.length; i++) {
            uint256 vaultId = vaultIds[i];
            Vault storage v = vaults[vaultId];
            if (v.state == State.Active) {
                v.lastHeartbeat = uint64(block.timestamp);
                emit Heartbeat(vaultId, v.lastHeartbeat);
            } else if (v.state == State.Challenge) {
                _cancelChallenge(vaultId, v, true);
            }
            // State.None / Released / Revoked: no-op, keep the batch resilient.
        }
    }

    // ---------------------------------------------------------------------
    // Guardians (EIP-712 signed by the guardian's custodial key, relayed)
    // ---------------------------------------------------------------------

    function attestDeath(uint256 vaultId, bytes32 deathCertHash, address guardian, uint256 deadline, bytes calldata sig)
        external
        onlyRelayer
    {
        Vault storage v = _requireVault(vaultId);
        if (v.state != State.Active) revert WrongState();
        if (!isInactive(vaultId)) revert OwnerStillActive();
        if (!isGuardian[vaultId][guardian]) revert NotGuardian();
        if (hasAttested[vaultId][v.epoch][guardian]) revert AlreadyAttested();
        if (block.timestamp > deadline) revert Expired();

        bytes32 structHash =
            keccak256(abi.encode(ATTEST_DEATH_TYPEHASH, vaultId, deathCertHash, v.epoch, deadline));
        _verify(structHash, guardian, sig);

        if (v.deathCertHash == bytes32(0)) {
            v.deathCertHash = deathCertHash;
        } else if (v.deathCertHash != deathCertHash) {
            revert DeathCertMismatch();
        }

        hasAttested[vaultId][v.epoch][guardian] = true;
        v.attestCount++;
        emit DeathAttested(vaultId, guardian, deathCertHash, v.attestCount);

        if (v.attestCount >= v.threshold) {
            v.state = State.Challenge;
            v.challengeEndsAt = uint64(block.timestamp) + v.challengePeriod;
            emit ChallengeStarted(vaultId, v.challengeEndsAt);
        }
    }

    // ---------------------------------------------------------------------
    // Anyone
    // ---------------------------------------------------------------------

    function finalizeRelease(uint256 vaultId) external {
        Vault storage v = _requireVault(vaultId);
        if (v.state != State.Challenge) revert WrongState();
        if (block.timestamp < v.challengeEndsAt) revert ChallengeNotEnded();

        v.state = State.Released;
        emit Released(vaultId, uint64(block.timestamp));

        address[] memory noms = _nominees[vaultId];
        uint16[] memory shares = _shares[vaultId];
        if (address(credential) != address(0)) {
            for (uint256 i = 0; i < noms.length; i++) {
                credential.mint(noms[i], vaultId, shares[i]);
            }
        }
    }

    // ---------------------------------------------------------------------
    // Views
    // ---------------------------------------------------------------------

    function getVault(uint256 vaultId) external view returns (Vault memory) {
        return vaults[vaultId];
    }

    function getNominees(uint256 vaultId) external view returns (address[] memory, uint16[] memory) {
        return (_nominees[vaultId], _shares[vaultId]);
    }

    function getGuardians(uint256 vaultId) external view returns (address[] memory) {
        return _guardianList[vaultId];
    }

    /// @notice True once the vault owner has been silent for at least `inactivityPeriod`.
    ///         This is the gate that must pass before any guardian attestation counts at all.
    function isInactive(uint256 vaultId) public view returns (bool) {
        Vault storage v = vaults[vaultId];
        if (v.state == State.None) return false;
        return block.timestamp >= uint256(v.lastHeartbeat) + uint256(v.inactivityPeriod);
    }

    // ---------------------------------------------------------------------
    // Internal helpers
    // ---------------------------------------------------------------------

    function _requireVault(uint256 vaultId) internal view returns (Vault storage v) {
        v = vaults[vaultId];
        if (v.state == State.None) revert VaultNotFound();
    }

    function _verify(bytes32 structHash, address expectedSigner, bytes calldata sig) internal view {
        bytes32 digest = _hashTypedDataV4(structHash);
        address signer = ECDSA.recover(digest, sig);
        if (signer != expectedSigner) revert BadSignature();
    }

    function _checkSharesSum(uint16[] calldata shareBps) internal pure {
        uint256 total;
        for (uint256 i = 0; i < shareBps.length; i++) {
            total += shareBps[i];
        }
        if (total != 10000) revert BadShares();
    }

    function _setGuardianList(uint256 vaultId, address[] calldata g) internal {
        address[] storage old = _guardianList[vaultId];
        for (uint256 i = 0; i < old.length; i++) {
            isGuardian[vaultId][old[i]] = false;
        }
        delete _guardianList[vaultId];
        for (uint256 i = 0; i < g.length; i++) {
            isGuardian[vaultId][g[i]] = true;
            _guardianList[vaultId].push(g[i]);
        }
    }

    /// @dev Shared by owner-cancel and relayer-reported-activity auto-cancel. Bumping the epoch
    ///      is what makes every attestation gathered so far permanently stale: guardians must
    ///      re-attest against the new epoch if the owner turns out to actually be gone.
    function _cancelChallenge(uint256 vaultId, Vault storage v, bool byActivity) internal {
        v.state = State.Active;
        v.epoch += 1;
        v.attestCount = 0;
        v.challengeEndsAt = 0;
        v.deathCertHash = bytes32(0);
        v.lastHeartbeat = uint64(block.timestamp);
        emit ReleaseCancelled(vaultId, v.epoch, byActivity);
    }
}
