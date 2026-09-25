// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";
import {Base64} from "@openzeppelin/contracts/utils/Base64.sol";

/// @title NomineeCredential
/// @notice Soulbound (ERC-5192-style "locked") ERC-721 minted to a nominee once their vault is
///         released. It carries no personal data on-chain: `tokenURI` returns an on-chain,
///         Base64-encoded JSON document with an inline brand-gradient SVG, built only from the
///         vaultId, share and release timestamp.
contract NomineeCredential is ERC721 {
    error NotRegistry();
    error TransfersDisabled();

    /// @dev Emitted per ERC-5192 when a token becomes permanently locked (i.e. on mint, since
    ///      every credential is locked from the moment it exists).
    event Locked(uint256 tokenId);

    struct CredentialData {
        uint256 vaultId;
        uint16 shareBps;
        uint64 releasedAt;
    }

    /// @notice The only address allowed to mint. Set once, at deploy time, to the
    ///         VirasatRegistry address.
    address public immutable registry;

    uint256 public nextTokenId = 1;
    mapping(uint256 => CredentialData) public credentialData;

    modifier onlyRegistry() {
        if (msg.sender != registry) revert NotRegistry();
        _;
    }

    constructor(address registry_) ERC721("Virasat Nominee Credential", "VNC") {
        registry = registry_;
    }

    /// @notice Mint a soulbound credential to a nominee. Only callable by the registry, as part
    ///         of `finalizeRelease`.
    function mint(address to, uint256 vaultId, uint16 shareBps) external onlyRegistry returns (uint256) {
        uint256 tokenId = nextTokenId++;
        credentialData[tokenId] =
            CredentialData({vaultId: vaultId, shareBps: shareBps, releasedAt: uint64(block.timestamp)});
        _safeMint(to, tokenId);
        emit Locked(tokenId);
        return tokenId;
    }

    /// @notice ERC-5192: every credential that exists is locked (non-transferable).
    function locked(uint256 tokenId) external view returns (bool) {
        _requireOwned(tokenId);
        return true;
    }

    /// @dev Soulbound: allow the mint transition (from == address(0)) and, in principle, a burn
    ///      transition (to == address(0), even though no burn function is exposed), but revert
    ///      on any wallet-to-wallet transfer.
    function _update(address to, uint256 tokenId, address auth) internal override returns (address) {
        address from = _ownerOf(tokenId);
        if (from != address(0) && to != address(0)) {
            revert TransfersDisabled();
        }
        return super._update(to, tokenId, auth);
    }

    function approve(address, uint256) public pure override {
        revert TransfersDisabled();
    }

    function setApprovalForAll(address, bool) public pure override {
        revert TransfersDisabled();
    }

    function supportsInterface(bytes4 interfaceId) public view override returns (bool) {
        // ERC-5192 (Minimal Soulbound NFTs) interface id.
        return interfaceId == 0xb45a3c0e || super.supportsInterface(interfaceId);
    }

    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        _requireOwned(tokenId);
        CredentialData memory d = credentialData[tokenId];

        string memory svg = _svg(tokenId, d.shareBps);
        string memory json = string(
            abi.encodePacked(
                '{"name":"Virasat Nominee Credential #',
                Strings.toString(tokenId),
                '","description":"Soulbound proof of a released Paytm Virasat vault share. Carries no personal data on-chain.",',
                '"attributes":[{"trait_type":"Vault ID","value":',
                Strings.toString(d.vaultId),
                '},{"trait_type":"Share (bps)","value":',
                Strings.toString(d.shareBps),
                '},{"trait_type":"Released At","value":',
                Strings.toString(d.releasedAt),
                "}],",
                '"vaultId":',
                Strings.toString(d.vaultId),
                ',"shareBps":',
                Strings.toString(d.shareBps),
                ',"releasedAt":',
                Strings.toString(d.releasedAt),
                ',"image":"data:image/svg+xml;base64,',
                Base64.encode(bytes(svg)),
                '"}'
            )
        );
        return string(abi.encodePacked("data:application/json;base64,", Base64.encode(bytes(json))));
    }

    function _svg(uint256 tokenId, uint16 shareBps) internal pure returns (string memory) {
        // Brand gradient: navy -> cyan, matching the frontend design tokens. No personal data.
        return string(
            abi.encodePacked(
                '<svg xmlns="http://www.w3.org/2000/svg" width="360" height="360" viewBox="0 0 360 360">',
                '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">',
                '<stop offset="0%" stop-color="#00112B"/>',
                '<stop offset="55%" stop-color="#002E6E"/>',
                '<stop offset="130%" stop-color="#00BAF2"/>',
                "</linearGradient></defs>",
                '<rect width="360" height="360" rx="24" fill="url(#g)"/>',
                '<circle cx="180" cy="140" r="54" fill="none" stroke="#E9B44C" stroke-width="4"/>',
                '<text x="180" y="150" font-family="monospace" font-size="20" fill="#EAF2FF" text-anchor="middle">VIRASAT</text>',
                '<text x="180" y="230" font-family="monospace" font-size="16" fill="#EAF2FF" text-anchor="middle">Credential #',
                Strings.toString(tokenId),
                "</text>",
                '<text x="180" y="258" font-family="monospace" font-size="14" fill="#8FA3BF" text-anchor="middle">Share: ',
                Strings.toString(shareBps / 100),
                ".",
                Strings.toString(shareBps % 100),
                "%</text>",
                "</svg>"
            )
        );
    }
}
