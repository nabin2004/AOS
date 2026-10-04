import { NextRequest, NextResponse } from "next/server";
import { attachRefreshedCookies, getAuthHeaders, resolveBackendAuth } from "@/lib/server-api";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    let auth = await resolveBackendAuth(request);
    const url = BACKEND_URL + "/api/v1/videos/" + id + "/stream";
    const range = request.headers.get("range");
    const refreshToken = request.cookies.get("refresh_token")?.value;
    const forward = (authHeader: string | null) =>
      fetch(url, {
        headers: { ...getAuthHeaders(authHeader), ...(range ? { Range: range } : {}) },
      });
    let response = await forward(auth.authHeader);
    if (response.status === 401 && refreshToken) {
      const refreshed = await fetch(BACKEND_URL + "/api/v1/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (refreshed.ok) {
        const tokens = (await refreshed.json()) as { access_token: string; refresh_token?: string };
        auth = {
          ...auth,
          authHeader: "Bearer " + tokens.access_token,
          refreshedAccessToken: tokens.access_token,
          refreshedRefreshToken: tokens.refresh_token,
        };
        response = await forward(auth.authHeader);
      }
    }

    if (!response.ok) {
      return NextResponse.json({ detail: "Video stream unavailable" }, { status: response.status });
    }

    const responseHeaders: Record<string, string> = {
      "Content-Type": response.headers.get("content-type") || "video/mp4",
      "Content-Disposition":
        response.headers.get("content-disposition") || `inline; filename="${id}.mp4"`,
      "Cache-Control": "private, max-age=3600",
      "Accept-Ranges": "bytes",
    };

    const contentLength = response.headers.get("content-length");
    if (contentLength) {
      responseHeaders["Content-Length"] = contentLength;
    }

    const contentRange = response.headers.get("content-range");
    if (contentRange) {
      responseHeaders["Content-Range"] = contentRange;
    }

    // Stream through with original status (206 Partial Content or 200 OK)
    const result = new NextResponse(response.body, {
      status: response.status,
      headers: responseHeaders,
    });
    return attachRefreshedCookies(result, auth);
  } catch {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
