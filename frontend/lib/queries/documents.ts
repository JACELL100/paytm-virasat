"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { DocumentRecord } from "@/lib/types";

export function useDocuments() {
  return useQuery({
    queryKey: queryKeys.documents(),
    queryFn: () => api.get<DocumentRecord[]>("/documents"),
    retry: 1,
  });
}

export function useDocument(id: string) {
  return useQuery({
    queryKey: queryKeys.document(id),
    queryFn: () => api.get<DocumentRecord>(`/documents/${id}`),
    enabled: Boolean(id),
    refetchInterval: (query) => (query.state.data?.status === "processing" ? 2000 : false),
  });
}

export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { file: File; kind: string; asset_id?: string }) => {
      const fd = new FormData();
      fd.append("file", payload.file);
      fd.append("kind", payload.kind);
      if (payload.asset_id) fd.append("asset_id", payload.asset_id);
      return api.upload<DocumentRecord>("/documents", fd);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.documents() }),
  });
}
