"use client";

import { useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  Copy,
  Check,
  Loader2,
  Sparkles,
  Terminal,
  Wrench,
} from "lucide-react";

import { AppVideoPlayer } from "@/components/media/video-player";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

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
  error_category?: string | null;
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
  const [copied, setCopied] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);

  const handleCopyPrompt = () => {
    if (data.prompt) {
      navigator.clipboard.writeText(data.prompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // 1. Terminal Failure State
  if (data.status === "failed") {
    return (
      <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-4 space-y-3">
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-destructive/10 p-2 text-destructive shrink-0 mt-0.5">
            <AlertCircle className="h-4 w-4" />
          </div>
          <div className="space-y-1 flex-1">
            <h4 className="text-sm font-semibold text-foreground">
              Generation Could Not Complete
            </h4>
            <p className="text-sm text-muted-foreground">
              {data.message ||
                "We couldn't generate the animation after multiple automated recovery attempts. Your prompt has been preserved."}
            </p>
          </div>
        </div>

        {data.prompt ? (
          <div className="rounded-lg bg-background/80 border p-3 space-y-1.5">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span className="font-medium">Preserved Prompt</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs gap-1"
                onClick={handleCopyPrompt}
              >
                {copied ? (
                  <>
                    <Check className="h-3 w-3 text-emerald-500" />
                    <span>Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3" />
                    <span>Copy</span>
                  </>
                )}
              </Button>
            </div>
            <p className="text-sm text-foreground/90 font-mono whitespace-pre-wrap">
              {data.prompt}
            </p>
          </div>
        ) : null}

        {/* Collapsible Technical / Developer Details */}
        <div className="pt-1">
          <button
            type="button"
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors font-medium"
            onClick={() => setDetailsOpen(!detailsOpen)}
          >
            <Terminal className="h-3.5 w-3.5" />
            <span>Developer / Diagnostic Details</span>
            <ChevronDown
              className={`h-3 w-3 transition-transform ${
                detailsOpen ? "rotate-180" : ""
              }`}
            />
          </button>

          {detailsOpen ? (
            <div className="mt-2 rounded-md bg-muted/60 border p-3 space-y-1.5 text-xs font-mono text-muted-foreground overflow-x-auto">
              <div>
                <span className="text-foreground/70 font-semibold">Job ID: </span>
                {data.video_generation_id}
              </div>
              {data.stage ? (
                <div>
                  <span className="text-foreground/70 font-semibold">Failed Stage: </span>
                  {data.stage}
                </div>
              ) : null}
              {data.celery_task_id ? (
                <div>
                  <span className="text-foreground/70 font-semibold">Task ID: </span>
                  {data.celery_task_id}
                </div>
              ) : null}
              {data.error ? (
                <div className="pt-1">
                  <span className="text-foreground/70 font-semibold">Raw Diagnostics: </span>
                  <pre className="mt-1 whitespace-pre-wrap text-destructive/90 bg-background/50 p-2 rounded border border-border/50">
                    {data.error}
                  </pre>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    );
  }

  // 2. In-Flight Running / Pending State
  if (data.status && data.status !== "completed") {
    const isColdStart =
      data.stage === "LLM_COLD_START" ||
      data.stage === "WAITING_FOR_LLM" ||
      data.stage === "LLM_RETRYING";
    const isRepairing =
      data.stage === "CODE_REPAIRING" || data.stage === "RENDER_RETRYING";

    return (
      <div className="rounded-xl border bg-card/60 p-4 space-y-3 shadow-sm backdrop-blur-sm">
        {data.prompt ? (
          <p className="text-xs text-muted-foreground font-mono truncate">
            Prompt: &quot;{data.prompt}&quot;
          </p>
        ) : null}

        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center">
            <Loader2 className="h-5 w-5 animate-spin text-primary shrink-0" />
            {isRepairing ? (
              <Wrench className="h-2.5 w-2.5 absolute text-amber-500" />
            ) : isColdStart ? (
              <Sparkles className="h-2.5 w-2.5 absolute text-blue-500" />
            ) : null}
          </div>

          <div className="space-y-0.5 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-foreground">
                {data.message ||
                  (data.stage ? `${data.stage}…` : "Generating your animation…")}
              </span>
              {isColdStart ? (
                <Badge variant="secondary" className="text-[10px] px-1.5 py-0 bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20">
                  Model Booting
                </Badge>
              ) : isRepairing ? (
                <Badge variant="secondary" className="text-[10px] px-1.5 py-0 bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20">
                  Self-Healing
                </Badge>
              ) : null}
            </div>
            <p className="text-xs text-muted-foreground">
              {isColdStart
                ? "The model is waking up from sleep. Your generation will proceed automatically."
                : isRepairing
                ? "Fixing code and re-verifying animation scene."
                : "Rendering mathematics and visual elements into high-definition video."}
            </p>
          </div>
        </div>

        {/* Collapsible details for in-flight debug info */}
        <div className="pt-1 border-t border-border/40">
          <button
            type="button"
            className="flex items-center gap-1 text-[11px] text-muted-foreground/70 hover:text-muted-foreground transition-colors"
            onClick={() => setDetailsOpen(!detailsOpen)}
          >
            <span>Job: {data.video_generation_id.slice(0, 8)}…</span>
            <ChevronDown
              className={`h-2.5 w-2.5 transition-transform ${
                detailsOpen ? "rotate-180" : ""
              }`}
            />
          </button>
          {detailsOpen ? (
            <div className="mt-1 text-[11px] font-mono text-muted-foreground/80 space-y-0.5">
              <div>Stage: {data.stage || "initializing"}</div>
              <div>Mode: {data.mode || "animate"}</div>
              <div>Full ID: {data.video_generation_id}</div>
            </div>
          ) : null}
        </div>
      </div>
    );
  }

  // 3. Completed Playable Video
  return (
    <div className="rounded-xl border bg-card/80 p-3.5 space-y-2.5 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 text-xs font-medium">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>Animation Ready</span>
        </div>
        {data.mode ? (
          <Badge variant="outline" className="text-[10px] uppercase font-mono tracking-wider">
            {data.mode}
          </Badge>
        ) : null}
      </div>

      {data.prompt ? (
        <p className="text-foreground/90 text-sm font-medium">{data.prompt}</p>
      ) : null}

      <AppVideoPlayer
        src={getVideoStreamUrl(data.video_generation_id)}
        className="overflow-hidden rounded-lg shadow-sm"
      />
    </div>
  );
}
