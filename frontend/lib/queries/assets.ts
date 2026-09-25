"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { Asset, DiscoverySuggestion } from "@/lib/types";

export function useAssets(filters?: { type?: string }) {
  return useQuery({
    queryKey: queryKeys.assets(filters),
    queryFn: () => {
      const qs = filters?.type ? `?type=${encodeURIComponent(filters.type)}` : "";
      return api.get<Asset[]>(`/assets${qs}`);
    },
    retry: 1,
  });
}

export function useAsset(id: string) {
  return useQuery({
    queryKey: queryKeys.asset(id),
    queryFn: () => api.get<Asset>(`/assets/${id}`),
    enabled: Boolean(id),
    retry: 1,
  });
}

export function useAskAboutAsset(id: string) {
  return useMutation({
    mutationFn: (question: string) =>
      api.post<{ answer: string; citations: Array<{ page: number; quote: string }> }>(
        `/assets/${id}/ask`,
        { question },
      ),
  });
}

export function useUploadStatement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return api.upload<DiscoverySuggestion[]>("/discovery/statement", fd);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["discovery"] }),
  });
}

export function usePasteSms() {
  return useMutation({
    mutationFn: (text: string) => api.post<DiscoverySuggestion[]>("/discovery/sms", { text }),
  });
}

export function useConnectPaytmFeed() {
  return useMutation({
    mutationFn: () => api.post<DiscoverySuggestion[]>("/discovery/paytm-feed"),
  });
}

export function useAcceptSuggestion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<Asset>(`/discovery/suggestions/${id}/accept`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.assets() });
      qc.invalidateQueries({ queryKey: queryKeys.insights() });
    },
  });
}

export function useRejectSuggestion() {
  return useMutation({
    mutationFn: (id: string) => api.post(`/discovery/suggestions/${id}/reject`),
  });
}
