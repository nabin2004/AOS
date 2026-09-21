import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";

// LLM plan generation can take up to 90 s — raise the serverless timeout cap.
export const maxDuration = 120;
export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  try {
    const accessToken = request.cookies.get("access_token")?.value;
    const authorization = request.headers.get("authorization");
    const body = await request.json();
    const data = await backendFetch("/api/v1/videos/plan", {
      method: "POST",
      headers: authorization ? { Authorization: authorization } : accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      body: JSON.stringify(body),
    });
    return NextResponse.json(data);
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
