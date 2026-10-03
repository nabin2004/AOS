import { NextRequest, NextResponse } from "next/server";
import {
  backendFetch,
  BackendApiError,
  resolveBackendAuth,
  attachRefreshedCookies,
  getAuthHeaders,
} from "@/lib/server-api";

// Source-preserving repair calls can need model startup time, but are bounded
// by the backend repair service.
export const maxDuration = 120;
export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  try {
    let auth = await resolveBackendAuth(request);
    const body = await request.json();

    let data;
    try {
      data = await backendFetch("/api/v1/videos/repair", {
        method: "POST",
        headers: getAuthHeaders(auth.authHeader),
        body: JSON.stringify(body),
      });
    } catch (err) {
      const refreshToken = request.cookies.get("refresh_token")?.value;
      if (err instanceof BackendApiError && err.status === 401 && refreshToken) {
        const refreshed = await backendFetch<{ access_token: string; refresh_token?: string }>(
          "/api/v1/auth/refresh",
          { method: "POST", body: JSON.stringify({ refresh_token: refreshToken }) },
        );
        auth = {
          authHeader: `Bearer ${refreshed.access_token}`,
          refreshedAccessToken: refreshed.access_token,
          refreshedRefreshToken: refreshed.refresh_token,
        };
        data = await backendFetch("/api/v1/videos/repair", {
          method: "POST",
          headers: getAuthHeaders(auth.authHeader),
          body: JSON.stringify(body),
        });
      } else {
        throw err;
      }
    }

    const response = NextResponse.json(data);
    return attachRefreshedCookies(response, auth);
  } catch (error) {
    if (error instanceof BackendApiError) {
      const data = error.data as { detail?: unknown } | null;
      const detail =
        typeof data?.detail === "string" && data.detail.trim()
          ? data.detail
          : error.message || "Manim repair failed";
      return NextResponse.json({ detail }, { status: error.status });
    }
    const msg = error instanceof Error ? error.message : "Internal server error";
    return NextResponse.json({ detail: msg }, { status: 500 });
  }
}
