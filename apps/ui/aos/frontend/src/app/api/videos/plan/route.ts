import { NextRequest, NextResponse } from "next/server";
import {
  backendFetch,
  BackendApiError,
  resolveBackendAuth,
  attachRefreshedCookies,
  getAuthHeaders,
} from "@/lib/server-api";

// LLM plan generation can take up to 90 s — raise the serverless timeout cap.
export const maxDuration = 120;
export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  try {
    let auth = await resolveBackendAuth(request);
    const body = await request.json();

    let data;
    try {
      data = await backendFetch("/api/v1/videos/plan", {
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
        data = await backendFetch("/api/v1/videos/plan", {
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
      // Surface the nested backend detail message when available
      const detail =
        (error.data as { detail?: string } | null)?.detail ||
        error.message ||
        "Failed to generate visual plan";
      return NextResponse.json({ detail }, { status: error.status });
    }
    const msg = error instanceof Error ? error.message : "Internal server error";
    return NextResponse.json({ detail: msg }, { status: 500 });
  }
}
