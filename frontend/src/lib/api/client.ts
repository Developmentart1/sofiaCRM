import { API_BASE_URL } from "@/lib/config";
import type { ApiError } from "@/lib/types/api";

export class ApiClientError extends Error {
  public readonly status: number;
  public readonly code: string | undefined;
  public readonly field: string | undefined;
  public readonly details: unknown;

  constructor(message: string, status: number, payload?: ApiError | null, details?: unknown) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = payload?.code;
    this.field = payload?.field;
    this.details = details;
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  get isForbidden(): boolean {
    return this.status === 403;
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  get isValidationError(): boolean {
    return this.status === 422 || this.status === 400;
  }

  get isServerError(): boolean {
    return this.status >= 500;
  }
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  query?: { [key: string]: unknown };
  signal?: AbortSignal;
  headers?: Record<string, string>;
  cache?: RequestCache;
  next?: { revalidate?: number | false; tags?: string[] };
}

function buildQuery(query: RequestOptions["query"]): string {
  if (!query) return "";
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") continue;
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      params.append(key, String(value));
    }
  }
  const s = params.toString();
  return s ? `?${s}` : "";
}

export async function apiFetch<T = unknown>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = "GET", body, query, signal, headers, cache, next } = options;

  const url = path.startsWith("http")
    ? `${path}${buildQuery(query)}`
    : `${API_BASE_URL}${path}${buildQuery(query)}`;

  const init: RequestInit = {
    method,
    credentials: "include",
    signal,
    cache,
    headers: {
      Accept: "application/json",
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
  };

  if (body !== undefined) {
    init.body = typeof body === "string" ? body : JSON.stringify(body);
  }

  let response: Response;
  try {
    response = await fetch(url, init as RequestInit & { next?: unknown });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw err;
    }
    throw new ApiClientError(
      "No se pudo conectar con el servidor. Verifica tu conexión.",
      0
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? await response.json().catch(() => null) : await response.text().catch(() => null);

  if (!response.ok) {
    const errPayload = isJson && payload && typeof payload === "object"
      ? (payload as ApiError)
      : null;
    const message = errPayload?.detail || (typeof payload === "string" && payload) || `Error ${response.status}`;
    throw new ApiClientError(message, response.status, errPayload, payload);
  }

  return payload as T;
}

export const api = {
  get: <T>(path: string, options?: Omit<RequestOptions, "method" | "body">) =>
    apiFetch<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method">) =>
    apiFetch<T>(path, { ...options, method: "POST", body }),
  patch: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method">) =>
    apiFetch<T>(path, { ...options, method: "PATCH", body }),
  put: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method">) =>
    apiFetch<T>(path, { ...options, method: "PUT", body }),
  delete: <T>(path: string, options?: Omit<RequestOptions, "method" | "body">) =>
    apiFetch<T>(path, { ...options, method: "DELETE" }),
};

export function getErrorMessage(err: unknown, fallback = "Algo salió mal"): string {
  if (err instanceof ApiClientError) return err.message;
  if (err instanceof Error) return err.message;
  return fallback;
}
