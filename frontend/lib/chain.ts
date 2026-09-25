import type { VaultState } from "@/lib/types";

export const CHAIN_EXPLORER = process.env.NEXT_PUBLIC_CHAIN_EXPLORER ?? "https://sepolia.etherscan.io";
export const CHAIN_ID = 11155111; // Sepolia (Implementation Plan §10.1)
export const CHAIN_NAME = "Sepolia";

export { etherscanAddressUrl, etherscanTxUrl } from "@/lib/format";

/** Human labels for on-chain vault state, shared across owner/guardian/nominee views. */
export const VAULT_STATE_LABEL: Record<VaultState, string> = {
  draft: "Not sealed yet",
  active: "Active — protected",
  challenge: "Challenge window open",
  released: "Released to family",
  revoked: "Revoked",
};
