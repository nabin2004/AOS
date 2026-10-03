import { NextRequest, NextResponse } from "next/server";
import {
  BackendApiError,
  backendFetchStream,
  backendFetch,
  resolveBackendAuth,
  attachRefreshedCookies,
  getAuthHeaders,
} from "@/lib/server-api";

export const maxDuration = 300;
export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  try {
    let auth = await resolveBackendAuth(request);
    const bodyPayload = JSON.stringify(await request.json());

    let response: Response;
    try {
      response = await backendFetchStream("/api/v1/videos/code/stream", {
        method: "POST",
        headers: getAuthHeaders(auth.authHeader),
        body: bodyPayload,
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
        response = await backendFetchStream("/api/v1/videos/code/stream", {
          method: "POST",
          headers: getAuthHeaders(auth.authHeader),
          body: bodyPayload,
        });
      } else {
        throw err;
      }
    }

    const nextResponse = new NextResponse(response.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
      },
    });
    return attachRefreshedCookies(nextResponse, auth);
  } catch (error) {
    const detail =
      error instanceof BackendApiError
        ? (error.data as { detail?: string } | null)?.detail || error.message
        : error instanceof Error
          ? error.message
          : "Unable to start Coder stream";
    return NextResponse.json({ detail }, { status: error instanceof BackendApiError ? error.status : 500 });
  }
}
