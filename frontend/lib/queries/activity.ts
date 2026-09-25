"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { ActivityEvent } from "@/lib/types";

export function useActivity() {
  return useQuery({
    queryKey: queryKeys.activity(),
    queryFn: () => api.get<ActivityEvent[]>("/activity"),
    retry: 1,
  });
}

export function useRecordActivity() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (kind: "login" | "upi_payment" | "app_open") =>
      api.post("/activity", { kind }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.activity() });
      qc.invalidateQueries({ queryKey: queryKeys.vault() });
    },
  });
}
