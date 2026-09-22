import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";

// Source-preserving repair calls can need model startup time, but are bounded
// by the backend repair service.
export const maxDuration = 120;
export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  try {
    const accessToken = request.cookies.get("access_token")?.value;
    const authorization = request.headers.get("authorization");
    const body = await request.json();
    const data = await backendFetch("/api/v1/videos/repair", {
      method: "POST",
      headers: authorization
        ? { Authorization: authorization }
        : accessToken
          ? { Authorization: `Bearer ${accessToken}` }
          : {},
      body: JSON.stringify(body),
    });
    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof BackendApiError) {
      const data = error.data as { detail?: unknown } | null;
      const detail = typeof data?.detail === "string" && data.detail.trim()
        ? data.detail
        : error.message || "Manim repair failed";
      return NextResponse.json({ detail }, { status: error.status });
    }
    const msg = error instanceof Error ? error.message : "Internal server error";
    return NextResponse.json({ detail: msg }, { status: 500 });
  }
}
