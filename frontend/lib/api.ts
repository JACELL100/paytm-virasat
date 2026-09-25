import { createClient } from "@/lib/supabase/client";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  code?: string;
  detail?: unknown;

  constructor(message: string, status: number, code?: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  skipAuth?: boolean;
  /** Set to false to send `body` as-is (e.g. FormData) instead of JSON-encoding it. */
  json?: boolean;
};

async function getAccessToken(): Promise<string | null> {
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

async function refreshAccessToken(): Promise<string | null> {
  const supabase = createClient();
  const { data, error } = await supabase.auth.refreshSession();
  if (error) return null;
  return data.session?.access_token ?? null;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, skipAuth, json = true, headers, ...rest } = options;

  const doFetch = async (token: string | null) => {
    const finalHeaders = new Headers(headers);
    if (json && body !== undefined) finalHeaders.set("Content-Type", "application/json");
    if (token && !skipAuth) finalHeaders.set("Authorization", `Bearer ${token}`);

    return fetch(`${API_BASE}${path}`, {
      ...rest,
      headers: finalHeaders,
      body: body === undefined ? undefined : json ? JSON.stringify(body) : (body as BodyInit),
    });
  };

  const token = skipAuth ? null : await getAccessToken();
  let res = await doFetch(token);

  // Silent-refresh-then-retry once on 401.
  if (res.status === 401 && !skipAuth) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      res = await doFetch(refreshed);
    }
  }

  if (!res.ok) {
    let detail: unknown;
    let message = res.statusText || "Request failed";
    let code: string | undefined;
    try {
      detail = await res.json();
      if (detail && typeof detail === "object") {
        const d = detail as Record<string, unknown>;
        message = (d.detail as string) || (d.title as string) || message;
        code = d.code as string | undefined;
      }
    } catch {
      // non-JSON error body
    }
    throw new ApiError(message, res.status, code, detail);
  }

  if (res.status === 204) return undefined as T;

  const contentType = res.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return (await res.json()) as T;
  }
  return (await res.text()) as unknown as T;
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "POST", body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PATCH", body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PUT", body }),
  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "DELETE" }),
  /** Upload a File/FormData without JSON-encoding the body. */
  upload: <T>(path: string, formData: FormData, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "POST", body: formData, json: false }),
};

export { API_BASE };
