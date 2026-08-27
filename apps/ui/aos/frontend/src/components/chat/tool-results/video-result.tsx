"use client";

import { Loader2 } from "lucide-react";

import { AppVideoPlayer } from "@/components/media/video-player";

export interface VideoToolResult {
  kind: "video";
  video_generation_id: string;
  minio_key?: string | null;
  mode?: string;
  prompt?: string | null;
  status?: string;
  stage?: string | null;
  message?: string | null;
  error?: string | null;
  celery_task_id?: string | null;
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
      <div className="space-y-2">
        {data.prompt ? (
          <p className="text-muted-foreground text-sm whitespace-pre-wrap">{data.prompt}</p>
        ) : null}
        <div className="text-destructive text-sm">
          Video generation failed{data.error ? `: ${data.error}` : "."}
        </div>
      </div>
    );
  }

  if (data.status && data.status !== "completed") {
    return (
      <div className="space-y-2">
        {data.prompt ? (
          <p className="text-muted-foreground text-sm whitespace-pre-wrap">{data.prompt}</p>
        ) : null}
        <div className="text-muted-foreground flex items-center gap-2 text-sm">
          <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" aria-hidden />
          <span>
            {data.message ||
              (data.stage ? `${data.stage}…` : `Video status: ${data.status}`)}
            {data.mode && !data.message ? ` (${data.mode})` : ""}
          </span>
        </div>
        {data.status === "pending" && data.celery_task_id ? (
          <p className="text-muted-foreground/80 font-mono text-xs break-all">
            Celery task {data.celery_task_id}
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {data.mode ? (
        <p className="text-muted-foreground text-xs uppercase tracking-wide">{data.mode} video</p>
      ) : null}
      {data.prompt ? (
        <p className="text-foreground/90 text-sm whitespace-pre-wrap">{data.prompt}</p>
      ) : null}
      <AppVideoPlayer
        src={getVideoStreamUrl(data.video_generation_id)}
        className="overflow-hidden rounded-md"
      />
    </div>
  );
}
