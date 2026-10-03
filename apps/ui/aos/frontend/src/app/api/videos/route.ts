import { NextRequest, NextResponse } from "next/server";
import {
  backendFetch,
  BackendApiError,
  resolveBackendAuth,
  attachRefreshedCookies,
  getAuthHeaders,
} from "@/lib/server-api";

/** Proxy GET /api/v1/videos?conversation_id=&skip=&limit= */
export async function GET(request: NextRequest) {
  try {
    let auth = await resolveBackendAuth(request);
    if (!auth.authHeader) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }

    const qs = request.nextUrl.searchParams.toString();
    const path = qs ? `/api/v1/videos?${qs}` : "/api/v1/videos";

    let data;
    try {
      data = await backendFetch(path, {
        headers: getAuthHeaders(auth.authHeader),
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
        data = await backendFetch(path, {
          headers: getAuthHeaders(auth.authHeader),
        });
      } else {
        throw err;
      }
    }

    const response = NextResponse.json(data);
    return attachRefreshedCookies(response, auth);
  } catch (error) {
    if (error instanceof BackendApiError) {
      return NextResponse.json(
        { detail: error.message || "Failed to list videos" },
        { status: error.status },
      );
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
