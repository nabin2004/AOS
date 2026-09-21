/**
 * Server-side API client for calling the FastAPI backend.
 * This module is used by Next.js API routes to proxy requests.
 * IMPORTANT: This file should only be imported in server-side code (API routes, Server Components).
 */

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export class BackendApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data?: unknown,
  ) {
    super(`Backend API error: ${status} ${statusText}`);
    this.name = "BackendApiError";
  }
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string>;
  /** Return raw text instead of parsing as JSON */
  raw?: boolean;
}

/**
 * Make a request to the FastAPI backend.
 * This should only be called from Next.js API routes or Server Components.
 */
export async function backendFetch<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { params, body, raw, ...fetchOptions } = options;

  let url = `${BACKEND_URL}${endpoint}`;

  if (params) {
    const searchParams = new URLSearchParams(params);
    url += `?${searchParams.toString()}`;
  }

  // Determine content type - don't set for FormData (browser will set with boundary)
  const headers: Record<string, string> = {};
  if (body instanceof FormData) {
    // Let the browser set Content-Type with the multipart boundary
  } else {
    headers["Content-Type"] = "application/json";
  }

  // Set a hard timeout slightly under the Next.js maxDuration (120 s) so we
  // get a meaningful error message rather than a platform-level timeout kill.
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 115_000);

  let response: Response;
  try {
    response = await fetch(url, {
      ...fetchOptions,
      headers: {
        ...headers,
        ...fetchOptions.headers,
      },
      body,
      signal: controller.signal,
    });
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new BackendApiError(504, "Gateway Timeout", {
        detail: "The LLM generation request timed out after 115 seconds.",
      });
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    let errorData;
    try {
      errorData = await response.json();
    } catch {
      errorData = null;
    }
    throw new BackendApiError(response.status, response.statusText, errorData);
  }

  // Handle empty responses
  const text = await response.text();
  if (!text) {
    return null as T;
  }

  if (raw) {
    return text as T;
  }

  return JSON.parse(text);
}

/** Forward a streaming backend response without buffering its SSE body. */
export async function backendFetchStream(endpoint: string, options: RequestOptions = {}): Promise<Response> {
  const { params, body, raw: _raw, ...fetchOptions } = options;
  let url = `${BACKEND_URL}${endpoint}`;
  if (params) url += `?${new URLSearchParams(params).toString()}`;

  const response = await fetch(url, {
    ...fetchOptions,
    headers: {
      Accept: "text/event-stream",
      ...(body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...fetchOptions.headers,
    },
    body,
  });
  if (!response.ok) {
    let data: unknown = null;
    try { data = await response.json(); } catch { /* keep null */ }
    throw new BackendApiError(response.status, response.statusText, data);
  }
  return response;
}

/**
 * Forward authorization header from the incoming request to the backend.
 */
export function getAuthHeaders(authHeader: string | null): Record<string, string> {
  if (!authHeader) {
    return {};
  }
  return { Authorization: authHeader };
}
