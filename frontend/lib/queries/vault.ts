"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { Vault } from "@/lib/types";

export function useVault() {
  return useQuery({
    queryKey: queryKeys.vault(),
    queryFn: () => api.get<Vault>("/vault"),
    retry: 1,
    // Poll fast while a release is pending (Implementation Plan §7).
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      return state === "challenge" ? 5000 : false;
    },
  });
}

export function useCreateVault() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { inactivity_secs: number; challenge_secs: number; threshold: number }) =>
      api.post<{ txHash: string }>("/vault", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.vault() }),
  });
}

export function useUpdateVaultSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { inactivity_secs?: number; challenge_secs?: number; threshold?: number }) =>
      api.patch("/vault/settings", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.vault() }),
  });
}

export function useCancelRelease() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post("/vault/cancel"),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.vault() }),
  });
}

export function useInviteNominee() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; relation: string; email: string; share_bps: number }) =>
      api.post("/vault/nominees", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.vault() }),
  });
}

export function useInviteGuardian() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; relation: string; email: string }) =>
      api.post("/vault/guardians", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.vault() }),
  });
}
