"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { Insights } from "@/lib/types";

export function useInsights() {
  return useQuery({
    queryKey: queryKeys.insights(),
    queryFn: () => api.get<Insights>("/insights"),
    retry: 1,
  });
}
