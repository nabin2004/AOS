import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";

export async function POST(request: NextRequest) {
  try {
    const accessToken = request.cookies.get("access_token")?.value;
    const authorization = request.headers.get("authorization");
    const body = await request.json();
    const data = await backendFetch("/api/v1/videos/render-custom", {
      method: "POST",
      headers: authorization ? { Authorization: authorization } : accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      body: JSON.stringify(body),
    });
    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof BackendApiError) {
      const data = error.data as { detail?: unknown } | null;
      const detail = typeof data?.detail === "string" && data.detail.trim()
        ? data.detail
        : error.message || "Failed to render custom scene";
      return NextResponse.json(
        // Preserve FastAPI's `detail`, including the Manim compiler stderr.
        { detail },
        { status: error.status },
      );
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
