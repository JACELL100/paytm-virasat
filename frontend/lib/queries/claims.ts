"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { Claim, ClaimEvent } from "@/lib/types";

export function useClaims(vaultId?: string) {
  return useQuery({
    queryKey: queryKeys.claims(vaultId),
    queryFn: () => {
      const qs = vaultId ? `?vault_id=${vaultId}` : "";
      return api.get<Claim[]>(`/claims${qs}`);
    },
    enabled: Boolean(vaultId),
    retry: 1,
  });
}

export function useClaim(id: string) {
  return useQuery({
    queryKey: queryKeys.claim(id),
    queryFn: () => api.get<Claim & { events: ClaimEvent[] }>(`/claims/${id}`),
    enabled: Boolean(id),
    retry: 1,
  });
}

export function useGenerateClaimPack(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ url: string }>(`/claims/${id}/pack`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.claim(id) }),
  });
}

export function useDraftEscalation(id: string) {
  return useMutation({
    mutationFn: (level: "gro" | "irdai" | "ombudsman") =>
      api.post<{ letter: string; pdf_url: string }>(`/claims/${id}/escalation`, { level }),
  });
}
