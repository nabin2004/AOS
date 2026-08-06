"use client";

import { AppVideoPlayer } from "@/components/media/video-player";

export interface VideoToolResult {
  kind: "video";
  video_generation_id: string;
  minio_key?: string | null;
  mode?: string;
  status?: string;
  error?: string | null;
}

/** Parse a `generate_video` tool result into a VideoToolResult, or null. */
export function parseVideoResult(result: unknown): VideoToolResult | null {
  if (result == null) return null;
  let payload: unknown = result;
  if (typeof result === "string") {
    try {
      payload = JSON.parse(result);
    } catch {
      return null;
    }
  }
  if (
    payload &&
    typeof payload === "object" &&
    (payload as { kind?: unknown }).kind === "video" &&
    typeof (payload as { video_generation_id?: unknown }).video_generation_id === "string"
  ) {
    return payload as VideoToolResult;
  }
  return null;
}

export function getVideoStreamUrl(videoGenerationId: string): string {
  return `/api/videos/${videoGenerationId}/stream`;
}

export function VideoResult({ data }: { data: VideoToolResult }) {
  if (data.status === "failed") {
    return (
      <div className="text-destructive text-sm">
        Video generation failed{data.error ? `: ${data.error}` : "."}
      </div>
    );
  }

  if (data.status && data.status !== "completed") {
    return (
      <div className="text-muted-foreground text-sm">
        Video status: {data.status}
        {data.mode ? ` (${data.mode})` : ""}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {data.mode ? (
        <p className="text-muted-foreground text-xs uppercase tracking-wide">{data.mode} video</p>
      ) : null}
      <AppVideoPlayer
        src={getVideoStreamUrl(data.video_generation_id)}
        className="overflow-hidden rounded-md"
      />
    </div>
  );
}
