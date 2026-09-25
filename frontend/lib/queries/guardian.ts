"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { Vault } from "@/lib/types";

export function useGuardianVaults() {
  return useQuery({
    queryKey: queryKeys.guardianVaults(),
    queryFn: () => api.get<Vault[]>("/guardian/vaults"),
    retry: 1,
  });
}

export function useGuardianVault(id: string) {
  return useQuery({
    queryKey: queryKeys.guardianVault(id),
    queryFn: () => api.get<Vault>(`/guardian/vaults/${id}`),
    enabled: Boolean(id),
    retry: 1,
  });
}

export function useUploadDeathCertificate(vaultId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return api.upload<{
        document_id: string;
        extracted: Record<string, unknown>;
        name_match_score: number;
        qr_decoded_url: string | null;
      }>(`/guardian/vaults/${vaultId}/death-certificate`, fd);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.guardianVault(vaultId) }),
  });
}

export function useAttestDeath(vaultId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { death_cert_hash: string; reason?: string }) =>
      api.post(`/guardian/vaults/${vaultId}/attest`, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.guardianVault(vaultId) }),
  });
}

export function useFinalizeRelease(vaultId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post(`/vaults/${vaultId}/finalize`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.guardianVault(vaultId) }),
  });
}
