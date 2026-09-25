"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { Vault } from "@/lib/types";

export function useNomineeVaults() {
  return useQuery({
    queryKey: queryKeys.nomineeVaults(),
    queryFn: () => api.get<Vault[]>("/nominee/vaults"),
    retry: 1,
  });
}

export function useNomineeVault(id: string) {
  return useQuery({
    queryKey: queryKeys.nomineeVault(id),
    queryFn: () => api.get<Vault>(`/nominee/vaults/${id}`),
    enabled: Boolean(id),
    retry: 1,
  });
}

export function useUnlockVault(vaultId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (legacy_key_share: string) =>
      api.post(`/nominee/vaults/${vaultId}/unlock`, { legacy_key_share }),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.nomineeVault(vaultId) }),
  });
}
