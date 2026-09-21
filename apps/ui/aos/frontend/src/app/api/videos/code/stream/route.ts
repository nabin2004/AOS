import { NextRequest, NextResponse } from "next/server";
import { BackendApiError, backendFetchStream } from "@/lib/server-api";

export const maxDuration = 300;
export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  try {
    const accessToken = request.cookies.get("access_token")?.value;
    const authorization = request.headers.get("authorization");
    const response = await backendFetchStream("/api/v1/videos/code/stream", {
      method: "POST",
      headers: authorization ? { Authorization: authorization } : accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      body: JSON.stringify(await request.json()),
    });
    return new NextResponse(response.body, {
      headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache, no-transform", Connection: "keep-alive" },
    });
  } catch (error) {
    const detail = error instanceof BackendApiError
      ? (error.data as { detail?: string } | null)?.detail || error.message
      : error instanceof Error ? error.message : "Unable to start Coder stream";
    return NextResponse.json({ detail }, { status: error instanceof BackendApiError ? error.status : 500 });
  }
}
