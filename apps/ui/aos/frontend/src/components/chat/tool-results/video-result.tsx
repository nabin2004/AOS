"use client";

import { useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clapperboard,
  RotateCcw,
  AlertTriangle,
} from "lucide-react";

import { AppVideoPlayer } from "@/components/media/video-player";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { GenerationStageEvent, VideoToolResult } from "@/types";
import {
  PromptViewer,
  GenerationTimeline,
  ManimCodeViewer,
  SelfHealingBanner,
  ColdStartBanner,
  DiagnosticDrawer,
} from "@/components/chat/generation";
import { accumulateGenerationEvent } from "@/lib/generation-events";

export type { VideoToolResult };

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

interface VideoResultProps {
  data: VideoToolResult;
  onRetry?: (prompt: string) => void;
}

export function VideoResult({ data, onRetry }: VideoResultProps) {
  const [selectedStage, setSelectedStage] = useState<GenerationStageEvent | null>(null);

  // Compute accumulated events from data.events or construct initial events
  const events: GenerationStageEvent[] =
    data.events && data.events.length > 0
      ? data.events
      : accumulateGenerationEvent([], {
          video_generation_id: data.video_generation_id,
          status: data.status,
          stage: data.stage,
          message: data.message,
          error: data.error,
          prompt: data.prompt,
          mode: data.mode,
          celery_task_id: data.celery_task_id,
          code: data.code,
          run_dir: data.run_dir,
        });

  const isColdStart =
    data.stage === "LLM_COLD_START" ||
    data.stage === "WAITING_FOR_LLM" ||
    data.stage === "LLM_RETRYING";

  const isRepairing =
    data.stage === "CODE_REPAIRING" ||
    data.stage === "RENDER_RETRYING" ||
    (data.repair_attempts != null && data.repair_attempts > 0);

  const isContextOverflow =
    data.error_category === "CONTEXT_LENGTH_ERROR" ||
    (data.error && /context length|maximum context length|32768/i.test(data.error));

  const handleRetry = () => {
    if (data.prompt) {
      if (onRetry) {
        onRetry(data.prompt);
      } else {
        window.dispatchEvent(
          new CustomEvent("aos:retry-prompt", { detail: { prompt: data.prompt } }),
        );
      }
    }
  };

  // ─────────────────────────────────────────────────────────────
  // 1. Terminal Failure State
  // ─────────────────────────────────────────────────────────────
  if (data.status === "failed") {
    const friendlyReason =
      isContextOverflow
        ? "The request exceeded the AI model's context window. AOS could not complete rendering."
        : data.error_category === "AUTHENTICATION_ERROR"
        ? "AI service credentials are invalid or expired."
        : data.error_category === "RATE_LIMIT"
        ? "The AI model is currently at maximum capacity."
        : data.error_category === "CODE_VALIDATION_ERROR"
        ? "The generated Manim code could not be validated after automated repair attempts."
        : data.error_category === "MANIM_RENDER_ERROR"
        ? "Manim could not render the animation scene."
        : data.error_category === "VIDEO_VALIDATION_ERROR"
        ? "The rendered video did not pass playability verification."
        : data.message || "Generation could not complete after automated recovery attempts.";

    return (
      <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-4 space-y-3.5 shadow-sm">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="rounded-full bg-destructive/10 p-2 text-destructive shrink-0 mt-0.5">
              <AlertCircle className="h-5 w-5" />
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <span>Generation Could Not Complete</span>
              </h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {friendlyReason}
              </p>
            </div>
          </div>

          <Badge variant="destructive" className="text-[10px] uppercase font-mono tracking-wider shrink-0">
            Failed
          </Badge>
        </div>

        {/* Context overflow alert banner if applicable */}
        {isContextOverflow && (
          <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-xs flex items-start gap-2.5 text-amber-700 dark:text-amber-300">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
            <div className="space-y-0.5 flex-1 leading-relaxed">
              <div className="font-semibold">Generation context is too large</div>
              <p className="text-[11px] text-muted-foreground">
                AOS could not send this request to the model because the generated context exceeded the model&apos;s context limit.
              </p>
            </div>
          </div>
        )}

        {/* Preserved User Prompt */}
        <PromptViewer prompt={data.prompt} defaultExpanded={true} />

        {/* Action Controls */}
        <div className="flex items-center gap-2 pt-1">
          <Button
            type="button"
            variant="default"
            size="sm"
            onClick={handleRetry}
            className="h-8 px-3 text-xs gap-1.5 font-medium shadow-sm"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Try Again</span>
          </Button>
        </div>

        {/* Timeline preserving all stages executed before failure */}
        <GenerationTimeline
          events={events}
          currentStatus="failed"
          onSelectStage={setSelectedStage}
          selectedStageId={selectedStage?.id}
        />

        {/* Failed Manim Code Viewer if code was produced */}
        {(data.code || data.error) && (
          <ManimCodeViewer
            code={data.code}
            videoGenerationId={data.video_generation_id}
            validationFailed={true}
            validationError={data.error}
            repairAttempt={data.repair_attempts}
            maxRepairAttempts={data.max_repair_attempts ?? 3}
          />
        )}

        {/* Collapsible Developer / Diagnostic Details */}
        <DiagnosticDrawer
          jobId={data.video_generation_id}
          taskId={data.celery_task_id}
          stage={data.stage}
          mode={data.mode}
          runDir={data.run_dir}
          rawError={data.error}
          errorCategory={data.error_category}
          durationSeconds={data.duration_seconds}
          retryCount={data.repair_attempts}
          contextUsage={data.context_usage}
        />
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────
  // 2. In-Flight Running / Pending State
  // ─────────────────────────────────────────────────────────────
  if (data.status && data.status !== "completed") {
    return (
      <div className="rounded-xl border border-border/70 bg-card/60 p-4 space-y-3.5 shadow-sm backdrop-blur-sm">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-foreground font-semibold text-sm">
            <Clapperboard className="h-4 w-4 text-primary animate-pulse" />
            <span>Generating Animation</span>
          </div>

          <div className="flex items-center gap-2">
            {data.mode && (
              <Badge variant="outline" className="text-[10px] uppercase font-mono tracking-wider">
                {data.mode}
              </Badge>
            )}
            <Badge variant="secondary" className="text-[10px] font-mono animate-pulse">
              In Progress
            </Badge>
          </div>
        </div>

        {/* Preserved Prompt (Collapsible) */}
        <PromptViewer prompt={data.prompt} defaultExpanded={false} />

        {/* Cold Start / Booting Banner */}
        <ColdStartBanner
          active={isColdStart}
          isRetry={data.stage === "LLM_RETRYING"}
          attempt={data.cold_start_attempts ?? 1}
        />

        {/* Self-Healing Repair Banner */}
        <SelfHealingBanner
          active={isRepairing}
          attempt={data.repair_attempts ?? 1}
          maxAttempts={data.max_repair_attempts ?? 3}
          errorDetails={data.error}
        />

        {/* Live Generation Timeline */}
        <GenerationTimeline
          events={events}
          currentStatus="running"
          onSelectStage={setSelectedStage}
          selectedStageId={selectedStage?.id}
        />

        {/* Code viewer (shows intermediate or synthesized code if available) */}
        {data.code && (
          <ManimCodeViewer
            code={data.code}
            videoGenerationId={data.video_generation_id}
            repaired={Boolean(data.repair_attempts && data.repair_attempts > 0)}
            repairAttempt={data.repair_attempts}
            maxRepairAttempts={data.max_repair_attempts ?? 3}
          />
        )}

        {/* Collapsible Diagnostic Drawer */}
        <DiagnosticDrawer
          jobId={data.video_generation_id}
          taskId={data.celery_task_id}
          stage={data.stage}
          mode={data.mode}
          runDir={data.run_dir}
          durationSeconds={data.duration_seconds}
          contextUsage={data.context_usage}
        />
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────
  // 3. Completed State: Playable Video & Comprehensive Details
  // ─────────────────────────────────────────────────────────────
  return (
    <div className="rounded-xl border border-border/70 bg-card/80 p-4 space-y-4 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 text-sm font-semibold">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>Animation Ready</span>
        </div>

        <div className="flex items-center gap-2">
          {data.duration_seconds ? (
            <span className="text-xs font-mono text-muted-foreground">
              {data.duration_seconds.toFixed(1)}s
            </span>
          ) : null}
          {data.mode && (
            <Badge variant="outline" className="text-[10px] uppercase font-mono tracking-wider">
              {data.mode}
            </Badge>
          )}
        </div>
      </div>

      {/* Preserved Prompt */}
      <PromptViewer prompt={data.prompt} defaultExpanded={false} />

      {/* Video Player */}
      <div className="overflow-hidden rounded-xl border border-border/60 shadow-sm bg-black/90">
        <AppVideoPlayer
          src={getVideoStreamUrl(data.video_generation_id)}
          className="overflow-hidden rounded-lg w-full aspect-video"
        />
      </div>

      {/* Full Generation Timeline (Completed) */}
      <GenerationTimeline
        events={events}
        currentStatus="completed"
        onSelectStage={setSelectedStage}
        selectedStageId={selectedStage?.id}
      />

      {/* Dedicated Collapsible Manim Code Viewer */}
      <ManimCodeViewer
        code={data.code}
        videoGenerationId={data.video_generation_id}
        repaired={Boolean(data.repair_attempts && data.repair_attempts > 0)}
        repairAttempt={data.repair_attempts}
        maxRepairAttempts={data.max_repair_attempts ?? 3}
      />

      {/* Developer / Diagnostic Details */}
      <DiagnosticDrawer
        jobId={data.video_generation_id}
        taskId={data.celery_task_id}
        stage={data.stage}
        mode={data.mode}
        runDir={data.run_dir}
        durationSeconds={data.duration_seconds}
        contextUsage={data.context_usage}
      />
    </div>
  );
}
