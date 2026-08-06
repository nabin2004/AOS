import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;
    const accessToken = request.cookies.get("access_token")?.value;
    if (!accessToken) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }

    const url = `${BACKEND_URL}/api/v1/videos/${id}/stream`;
    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      return NextResponse.json({ detail: "Video not found" }, { status: response.status });
    }

    // Stream through so large MP4s are not buffered entirely in the BFF.
    return new NextResponse(response.body, {
      headers: {
        "Content-Type": response.headers.get("content-type") || "video/mp4",
        "Content-Disposition":
          response.headers.get("content-disposition") || `inline; filename="${id}.mp4"`,
        "Cache-Control": "private, max-age=3600",
        "Accept-Ranges": response.headers.get("accept-ranges") || "bytes",
      },
    });
  } catch {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
