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
export function getAuthHeaders(authHeader?: string | null): Record<string, string> {
  if (!authHeader) {
    return {};
  }
  return { Authorization: authHeader };
}

export interface ResolvedBackendAuth {
  authHeader: string | null;
  refreshedAccessToken?: string;
  refreshedRefreshToken?: string;
}

/**
 * Resolves an active Bearer Authorization header for backend requests.
 * Uses client Authorization header, access_token cookie, or transparently
 * refreshes via the refresh_token cookie when access_token has expired.
 */
export async function resolveBackendAuth(request: import("next/server").NextRequest): Promise<ResolvedBackendAuth> {
  const authorization = request.headers.get("authorization");
  if (authorization) {
    return { authHeader: authorization };
  }

  const accessToken = request.cookies.get("access_token")?.value;
  if (accessToken) {
    return { authHeader: `Bearer ${accessToken}` };
  }

  const refreshToken = request.cookies.get("refresh_token")?.value;
  if (refreshToken) {
    try {
      const refreshed = await backendFetch<{ access_token: string; refresh_token?: string }>(
        "/api/v1/auth/refresh",
        {
          method: "POST",
          body: JSON.stringify({ refresh_token: refreshToken }),
        },
      );
      if (refreshed?.access_token) {
        return {
          authHeader: `Bearer ${refreshed.access_token}`,
          refreshedAccessToken: refreshed.access_token,
          refreshedRefreshToken: refreshed.refresh_token,
        };
      }
    } catch {
      // Refresh token also invalid or backend unavailable
    }
  }

  return { authHeader: null };
}

/**
 * Attaches refreshed auth cookies to a NextResponse if token rotation occurred.
 */
export function attachRefreshedCookies<T extends Response>(
  response: T,
  refreshed: ResolvedBackendAuth,
): T {
  const res = response as unknown as { cookies?: { set: (name: string, val: string, opts: Record<string, unknown>) => void } };
  if (res && res.cookies && typeof res.cookies.set === "function") {
    if (refreshed.refreshedAccessToken) {
      res.cookies.set("access_token", refreshed.refreshedAccessToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        maxAge: 60 * 15, // 15 min
        path: "/",
      });
    }
    if (refreshed.refreshedRefreshToken) {
      res.cookies.set("refresh_token", refreshed.refreshedRefreshToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        maxAge: 60 * 60 * 24 * 7, // 7 days
        path: "/",
      });
    }
  }
  return response;
}
