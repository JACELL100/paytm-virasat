// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title ClaimLedger
/// @notice Cheap, event-only anchor for claim-tracker timestamps. No storage beyond the relayer
///         address: institutions and the backend read history via `eth_getLogs`, not via calls.
///         `claimId = keccak256(supabase_claim_uuid)`; `status` mirrors the backend's
///         `claim_status` enum ordinal so events stay small.
contract ClaimLedger is Ownable {
    error NotRelayer();
    error ZeroAddress();

    event RelayerUpdated(address indexed relayer);
    event ClaimEvent(bytes32 indexed claimId, uint256 indexed vaultId, uint8 status, bytes32 docHash, uint64 at);

    address public relayer;

    modifier onlyRelayer() {
        if (msg.sender != relayer) revert NotRelayer();
        _;
    }

    constructor(address initialOwner, address relayer_) Ownable(initialOwner) {
        if (relayer_ == address(0)) revert ZeroAddress();
        relayer = relayer_;
        emit RelayerUpdated(relayer_);
    }

    function setRelayer(address r) external onlyOwner {
        if (r == address(0)) revert ZeroAddress();
        relayer = r;
        emit RelayerUpdated(r);
    }

    /// @notice Anchor a claim status transition on-chain. Purely additive/event-based: no state
    ///         is kept in contract storage beyond `relayer`.
    function log(bytes32 claimId, uint256 vaultId, uint8 status, bytes32 docHash) external onlyRelayer {
        emit ClaimEvent(claimId, vaultId, status, docHash, uint64(block.timestamp));
    }
}
