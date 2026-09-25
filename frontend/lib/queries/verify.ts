"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { VerifyResponse } from "@/lib/types";

export function useVerify(tokenId: string) {
  return useQuery({
    queryKey: queryKeys.verify(tokenId),
    queryFn: () => api.get<VerifyResponse>(`/verify/${tokenId}`, { skipAuth: true }),
    enabled: Boolean(tokenId),
    retry: 1,
  });
}
