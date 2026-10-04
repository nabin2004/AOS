import { NextRequest, NextResponse } from "next/server";
import {
  backendFetch,
  BackendApiError,
  resolveBackendAuth,
  attachRefreshedCookies,
  getAuthHeaders,
} from "@/lib/server-api";

interface RouteParams {
  params: Promise<{ action: string }>;
}

const VALID_ACTIONS = new Set([
  "schema",
  "validate",
  "compile",
  "generate",
  "render",
  "generate-and-render",
]);

/** Proxy GET /api/v1/motiongram/{action} (e.g. /api/motiongram/schema) */
export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const { action } = await params;
    if (!VALID_ACTIONS.has(action)) {
      return NextResponse.json({ detail: "Action not supported" }, { status: 404 });
    }

    const data = await backendFetch(`/api/v1/motiongram/${action}`);
    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof BackendApiError) {
      return NextResponse.json(
        { detail: error.message || "Failed to fetch schema" },
        { status: error.status },
      );
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}

/** Proxy POST /api/v1/motiongram/{action} */
export async function POST(request: NextRequest, { params }: RouteParams) {
  try {
    const { action } = await params;
    if (!VALID_ACTIONS.has(action)) {
      return NextResponse.json({ detail: "Action not supported" }, { status: 404 });
    }

    let auth = await resolveBackendAuth(request);
    let body: unknown = {};
    try {
      body = await request.json();
    } catch {
      // Body may be empty
    }

    let data;
    try {
      data = await backendFetch(`/api/v1/motiongram/${action}`, {
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
        data = await backendFetch(`/api/v1/motiongram/${action}`, {
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
      return NextResponse.json(
        { detail: data?.detail || error.message || "MotionGram operation failed" },
        { status: error.status },
      );
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
