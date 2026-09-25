/** Central TanStack Query key registry, one factory per resource (Implementation Plan §7). */
export const queryKeys = {
  me: () => ["me"] as const,
  insights: () => ["insights"] as const,
  vault: () => ["vault"] as const,
  assets: (filters?: Record<string, unknown>) => ["assets", filters ?? {}] as const,
  asset: (id: string) => ["assets", id] as const,
  documents: () => ["documents"] as const,
  document: (id: string) => ["documents", id] as const,
  activity: () => ["activity"] as const,
  guardianVaults: () => ["guardian", "vaults"] as const,
  guardianVault: (id: string) => ["guardian", "vaults", id] as const,
  nomineeVaults: () => ["nominee", "vaults"] as const,
  nomineeVault: (id: string) => ["nominee", "vaults", id] as const,
  claims: (vaultId?: string) => ["claims", vaultId ?? "all"] as const,
  claim: (id: string) => ["claims", "detail", id] as const,
  verify: (tokenId: string) => ["verify", tokenId] as const,
  copilotSession: (sid: string) => ["copilot", "session", sid] as const,
};
