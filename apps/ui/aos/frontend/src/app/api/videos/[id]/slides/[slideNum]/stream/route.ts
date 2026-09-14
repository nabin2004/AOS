import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string; slideNum: string }> },
) {
  try {
    const { id, slideNum } = await params;
    const accessToken =
      request.cookies.get("access_token")?.value ||
      request.nextUrl.searchParams.get("token") ||
      request.headers.get("authorization")?.replace(/^Bearer\s+/i, "");

    if (!accessToken) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }

    const url = `${BACKEND_URL}/api/v1/videos/${id}/slides/${slideNum}/stream`;
    const forwardHeaders: Record<string, string> = {
      Authorization: `Bearer ${accessToken}`,
    };

    const range = request.headers.get("range");
    if (range) {
      forwardHeaders["Range"] = range;
    }

    const response = await fetch(url, {
      headers: forwardHeaders,
    });

    if (!response.ok) {
      return NextResponse.json({ detail: "Slide video not found" }, { status: response.status });
    }

    const responseHeaders: Record<string, string> = {
      "Content-Type": response.headers.get("content-type") || "video/mp4",
      "Content-Disposition":
        response.headers.get("content-disposition") || `inline; filename="${id}_slide_${slideNum}.mp4"`,
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

    return new NextResponse(response.body, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
