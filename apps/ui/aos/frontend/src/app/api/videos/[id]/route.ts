import { NextRequest, NextResponse } from "next/server";
import {
  backendFetch,
  BackendApiError,
  resolveBackendAuth,
  attachRefreshedCookies,
  getAuthHeaders,
} from "@/lib/server-api";

interface RouteParams {
  params: Promise<{ id: string }>;
}

const ACTION_ENDPOINTS = new Set(["classify", "plan", "code", "render-custom", "repair"]);

/** Proxy GET /api/v1/videos/{id} */
export async function GET(_request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params;
    if (ACTION_ENDPOINTS.has(id)) {
      return NextResponse.json({ detail: "Method not allowed" }, { status: 405 });
    }

    let auth = await resolveBackendAuth(_request);
    if (!auth.authHeader) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }

    let data;
    try {
      data = await backendFetch(`/api/v1/videos/${id}`, {
        headers: getAuthHeaders(auth.authHeader),
      });
    } catch (err) {
      const refreshToken = _request.cookies.get("refresh_token")?.value;
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
        data = await backendFetch(`/api/v1/videos/${id}`, {
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
        { detail: error.message || "Video not found" },
        { status: error.status },
      );
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}

/** Proxy POST /api/v1/videos/{action} if caught by dynamic route matcher */
export async function POST(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params;
    if (ACTION_ENDPOINTS.has(id)) {
      let auth = await resolveBackendAuth(request);
      const body = await request.json();

      let data;
      try {
        data = await backendFetch(`/api/v1/videos/${id}`, {
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
          data = await backendFetch(`/api/v1/videos/${id}`, {
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
    }

    return NextResponse.json({ detail: "Method not allowed" }, { status: 405 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      return NextResponse.json(
        { detail: error.message || "Request failed" },
        { status: error.status },
      );
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}

