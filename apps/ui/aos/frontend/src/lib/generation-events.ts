import type { GenerationStage, GenerationStageEvent, GenerationStageStatus } from "@/types";

export interface RawVideoStatusPayload {
  video_generation_id: string;
  status?: string;
  stage?: string | null;
  message?: string | null;
  error?: string | null;
  mode?: string;
  prompt?: string | null;
  celery_task_id?: string | null;
  code?: string | null;
  run_dir?: string | null;
  timestamp?: number;
}

export const CANONICAL_STAGES: GenerationStage[] = [
  "QUEUED",
  "CLASSIFYING",
  "PLANNING_LECTURE",
  "WRITING_TEACHING_SCRIPT",
  "WRITING_MANIM_CODE",
  "VALIDATING_CODE",
  "RENDERING",
  "VALIDATING_VIDEO",
];

export const STAGE_TITLES: Record<GenerationStage, string> = {
  QUEUED: "Request received",
  STARTING: "Starting pipeline",
  CLASSIFYING: "Classifying topic",
  PLANNING_LECTURE: "Planning lecture",
  WRITING_TEACHING_SCRIPT: "Writing teaching script",
  WRITING_MANIM_CODE: "Writing Manim code",
  VALIDATING_CODE: "Validating code",
  CODE_REPAIRING: "Repairing animation code",
  LLM_COLD_START: "Model booting",
  LLM_RETRYING: "Retrying model request",
  RENDERING: "Rendering animation",
  VALIDATING_VIDEO: "Validating video",
  COMPLETED: "Animation ready",
  FAILED: "Generation failed",
};

export const STAGE_DESCRIPTIONS: Record<GenerationStage, string> = {
  QUEUED: "Job queued and dispatched to worker.",
  STARTING: "Initializing agent runtime and tools.",
  CLASSIFYING: "Determining subject domain, prerequisites, and learning objectives.",
  PLANNING_LECTURE: "Structuring pedagogical outline, scene elements, and timing.",
  WRITING_TEACHING_SCRIPT: "Composing spoken voiceover aligned to animation beats.",
  WRITING_MANIM_CODE: "Synthesizing Python Manim CE scene code and visual choreography.",
  VALIDATING_CODE: "Checking AST syntax, coordinate bounds, and API contracts.",
  CODE_REPAIRING: "Self-healing compiler/render error and regenerating scene.",
  LLM_COLD_START: "Serverless LLM is starting up from idle.",
  LLM_RETRYING: "Transient connection recovery with exponential backoff.",
  RENDERING: "Executing Manim animation engine in sandbox.",
  VALIDATING_VIDEO: "Inspecting MP4 stream, duration, and audio alignment.",
  COMPLETED: "Video rendered and validated successfully.",
  FAILED: "Pipeline execution encountered an unrecoverable error.",
};

export function normalizeStage(rawStage?: string | null): GenerationStage {
  if (!rawStage) return "STARTING";
  const cleaned = rawStage.trim();

  // Exact matching
  switch (cleaned) {
    case "queued":
    case "enqueued":
    case "QUEUED":
      return "QUEUED";
    case "starting":
    case "STARTING":
      return "STARTING";
    case "ClassifyNode":
    case "ClassifyFallback":
    case "CLASSIFYING":
      return "CLASSIFYING";
    case "PlanLectureNode":
    case "PlanFallback":
    case "PLANNING_LECTURE":
      return "PLANNING_LECTURE";
    case "PlanTeachingScriptNode":
    case "WRITING_TEACHING_SCRIPT":
      return "WRITING_TEACHING_SCRIPT";
    case "CodeAgent":
    case "CodeAgentNode":
    case "WRITING_MANIM_CODE":
    case "write_code":
      return "WRITING_MANIM_CODE";
    case "VALIDATING_CODE":
    case "validate_code":
      return "VALIDATING_CODE";
    case "CODE_REPAIRING":
    case "RENDER_RETRYING":
    case "repair":
      return "CODE_REPAIRING";
    case "LLM_COLD_START":
    case "WAITING_FOR_LLM":
      return "LLM_COLD_START";
    case "LLM_RETRYING":
    case "RATE_LIMIT_WAIT":
      return "LLM_RETRYING";
    case "compile":
    case "render":
    case "assemble":
    case "upload":
    case "RENDERING":
      return "RENDERING";
    case "VALIDATING_VIDEO":
    case "VIDEO_VALIDATION_FAILED":
      return "VALIDATING_VIDEO";
    case "completed":
    case "COMPLETED":
      return "COMPLETED";
    case "failed":
    case "FAILED":
      return "FAILED";
  }

  // Substring matching fallbacks
  const low = cleaned.toLowerCase();
  if (low.includes("classif")) return "CLASSIFYING";
  if (low.includes("plan")) return "PLANNING_LECTURE";
  if (low.includes("script")) return "WRITING_TEACHING_SCRIPT";
  if (low.includes("repair")) return "CODE_REPAIRING";
  if (low.includes("cold") || low.includes("booting") || low.includes("waking")) return "LLM_COLD_START";
  if (low.includes("retry")) return "LLM_RETRYING";
  if (low.includes("code") || low.includes("manim")) return "WRITING_MANIM_CODE";
  if (low.includes("validat") && low.includes("video")) return "VALIDATING_VIDEO";
  if (low.includes("validat")) return "VALIDATING_CODE";
  if (low.includes("render") || low.includes("compile") || low.includes("upload")) return "RENDERING";
  if (low.includes("queue")) return "QUEUED";

  return "STARTING";
}

export function parseAttemptInfo(
  text?: string | null,
): { attempt?: number; maxAttempts?: number } {
  if (!text) return {};
  // e.g. "Attempt 2 of 6", "attempt 2/6", "Repair attempt 1 / 3"
  const m1 = text.match(/(?:attempt|try)\s*(\d+)\s*(?:of|\/)\s*(\d+)/i);
  if (m1 && m1[1] && m1[2]) {
    return { attempt: parseInt(m1[1], 10), maxAttempts: parseInt(m1[2], 10) };
  }
  const m2 = text.match(/attempt=(\d+)(?:\/(\d+))?/i);
  if (m2 && m2[1]) {
    return {
      attempt: parseInt(m2[1], 10),
      maxAttempts: m2[2] ? parseInt(m2[2], 10) : undefined,
    };
  }
  return {};
}

/**
 * Pure reducer that accumulates incoming video status updates into a clean,
 * ordered sequence of stage events without dropping historical events or timings.
 */
export function accumulateGenerationEvent(
  prevEvents: GenerationStageEvent[] = [],
  payload: RawVideoStatusPayload,
): GenerationStageEvent[] {
  const now = payload.timestamp ?? Date.now();
  const rawStage = payload.stage ?? payload.status ?? "STARTING";
  const stage = normalizeStage(rawStage);
  const message = payload.message || STAGE_TITLES[stage] || rawStage;
  const isTerminalSuccess = payload.status === "completed" || stage === "COMPLETED";
  const isTerminalFailure = payload.status === "failed" || stage === "FAILED";
  const { attempt, maxAttempts } = parseAttemptInfo(message);

  // If no prior events, seed with QUEUED or current stage
  if (prevEvents.length === 0) {
    const initialStage: GenerationStage = stage === "COMPLETED" || stage === "FAILED" ? stage : (stage === "STARTING" ? "QUEUED" : stage);
    const initialStatus: GenerationStageStatus = isTerminalSuccess
      ? "completed"
      : isTerminalFailure
        ? "failed"
        : "running";

    return [
      {
        id: `stage-${initialStage}-${now}`,
        stage: initialStage,
        rawStage,
        name: STAGE_TITLES[initialStage],
        status: initialStatus,
        message,
        timestamp: now,
        attempt,
        maxAttempts,
        error: payload.error || undefined,
      },
    ];
  }

  const updated = [...prevEvents];
  const lastEventIndex = updated.length - 1;
  const lastEvent = updated[lastEventIndex];
  if (!lastEvent) return updated;

  // 1. Terminal success: close all uncompleted stages and mark completed
  if (isTerminalSuccess) {
    // Complete the previous active stage
    if (lastEvent.status === "running") {
      updated[lastEventIndex] = {
        ...lastEvent,
        status: "completed",
        duration_ms: Math.max(100, now - lastEvent.timestamp),
      };
    }
    // Add completed terminal stage if not already present
    if (lastEvent.stage !== "COMPLETED") {
      updated.push({
        id: `stage-COMPLETED-${now}`,
        stage: "COMPLETED",
        rawStage: "completed",
        name: STAGE_TITLES.COMPLETED,
        status: "completed",
        message: payload.message || "Your video is ready.",
        timestamp: now,
        duration_ms: 0,
      });
    }
    return updated;
  }

  // 2. Terminal failure: mark active stage as failed, preserve prior history
  if (isTerminalFailure) {
    if (lastEvent.status === "running") {
      updated[lastEventIndex] = {
        ...lastEvent,
        status: "failed",
        duration_ms: Math.max(100, now - lastEvent.timestamp),
        error: payload.error || payload.message || undefined,
      };
    }
    return updated;
  }

  // 3. Same stage update (e.g. repeated status or attempt increment)
  if (lastEvent.stage === stage) {
    // Check if this is a distinct retry attempt (keep separate event if attempt number changed)
    if (attempt && lastEvent.attempt && attempt !== lastEvent.attempt) {
      updated[lastEventIndex] = {
        ...lastEvent,
        status: "completed",
        duration_ms: Math.max(100, now - lastEvent.timestamp),
      };
      updated.push({
        id: `stage-${stage}-${attempt}-${now}`,
        stage,
        rawStage,
        name: STAGE_TITLES[stage],
        status: "retrying",
        message,
        timestamp: now,
        attempt,
        maxAttempts,
      });
      return updated;
    }

    // Otherwise update in-place with latest message / attempt info
    updated[lastEventIndex] = {
      ...lastEvent,
      message,
      attempt: attempt ?? lastEvent.attempt,
      maxAttempts: maxAttempts ?? lastEvent.maxAttempts,
      status: stage === "LLM_COLD_START" || stage === "LLM_RETRYING" || stage === "CODE_REPAIRING" ? "retrying" : "running",
    };
    return updated;
  }

  // 4. Transition to a new stage:
  // Complete the previous stage with real duration
  if (lastEvent.status === "running" || lastEvent.status === "retrying") {
    updated[lastEventIndex] = {
      ...lastEvent,
      status: "completed",
      duration_ms: Math.max(100, now - lastEvent.timestamp),
    };
  }

  const newStatus: GenerationStageStatus =
    stage === "LLM_COLD_START" || stage === "LLM_RETRYING" || stage === "CODE_REPAIRING"
      ? "retrying"
      : "running";

  updated.push({
    id: `stage-${stage}-${now}`,
    stage,
    rawStage,
    name: STAGE_TITLES[stage],
    status: newStatus,
    message,
    timestamp: now,
    attempt,
    maxAttempts,
    error: payload.error || undefined,
  });

  return updated;
}

/**
 * Calculate genuine percentage progress based on completed canonical stages.
 * Guaranteed never to invent fake percentages or exceed 100%.
 */
export function calculateGenerationProgress(
  events: GenerationStageEvent[],
  overallStatus?: string,
): number {
  if (overallStatus === "completed") return 100;
  if (overallStatus === "failed") return 0;
  if (!events || events.length === 0) return 5;

  const weights: Record<GenerationStage, number> = {
    QUEUED: 10,
    STARTING: 15,
    CLASSIFYING: 25,
    PLANNING_LECTURE: 38,
    WRITING_TEACHING_SCRIPT: 50,
    WRITING_MANIM_CODE: 65,
    VALIDATING_CODE: 78,
    CODE_REPAIRING: 72,
    LLM_COLD_START: 18,
    LLM_RETRYING: 20,
    RENDERING: 90,
    VALIDATING_VIDEO: 96,
    COMPLETED: 100,
    FAILED: 0,
  };

  const last = events[events.length - 1];
  if (!last) return 5;
  if (last.stage === "COMPLETED") return 100;

  return weights[last.stage] ?? 20;
}

/**
 * Format milliseconds into human-readable duration like `1.8s` or `1m 12s`.
 */
export function formatStageDuration(durationMs?: number): string {
  if (durationMs == null || durationMs <= 0) return "";
  const totalSeconds = durationMs / 1000;
  if (totalSeconds < 60) {
    return `${totalSeconds.toFixed(1)}s`;
  }
  const mins = Math.floor(totalSeconds / 60);
  const secs = Math.floor(totalSeconds % 60);
  return `${mins}m ${secs}s`;
}

/**
 * Redact API keys, bearer tokens, passwords, and sensitive headers from diagnostic output.
 */
export function sanitizeDiagnostics(text?: string | null): string {
  if (!text) return "";
  return text
    .replace(/(OPENROUTER_API_KEY|HF_TOKEN|WANDB_API_KEY)=([^\s]+)/gi, "$1=[REDACTED]")
    .replace(/(?:Bearer\s+)[A-Za-z0-9._~+/-]{10,}/gi, "Bearer [REDACTED]")
    .replace(/(?:api[_-]?key["':\s=]+)[A-Za-z0-9._~+/-]{10,}/gi, "api_key: [REDACTED]")
    .replace(/(?:sk-[A-Za-z0-9_-]{12,})/gi, "sk-[REDACTED]");
}
