import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";

interface RouteParams {
  params: Promise<{ id: string }>;
}

const ACTION_ENDPOINTS = new Set(["classify", "plan", "code", "render-custom"]);

/** Proxy GET /api/v1/videos/{id} */
export async function GET(_request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params;
    if (ACTION_ENDPOINTS.has(id)) {
      return NextResponse.json({ detail: "Method not allowed" }, { status: 405 });
    }

    const accessToken = _request.cookies.get("access_token")?.value;
    if (!accessToken) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }

    const data = await backendFetch(`/api/v1/videos/${id}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    return NextResponse.json(data);
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
      const accessToken = request.cookies.get("access_token")?.value;
      const body = await request.json();
      const data = await backendFetch(`/api/v1/videos/${id}`, {
        method: "POST",
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        body: JSON.stringify(body),
      });
      return NextResponse.json(data);
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

