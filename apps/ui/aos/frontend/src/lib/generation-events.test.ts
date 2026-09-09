import { describe, it, expect } from "vitest";
import {
  normalizeStage,
  parseAttemptInfo,
  accumulateGenerationEvent,
  calculateGenerationProgress,
  formatStageDuration,
  sanitizeDiagnostics,
} from "./generation-events";

describe("generation-events", () => {
  it("normalizes backend stage names accurately", () => {
    expect(normalizeStage("ClassifyNode")).toBe("CLASSIFYING");
    expect(normalizeStage("ClassifyFallback")).toBe("CLASSIFYING");
    expect(normalizeStage("PlanLectureNode")).toBe("PLANNING_LECTURE");
    expect(normalizeStage("PlanTeachingScriptNode")).toBe("WRITING_TEACHING_SCRIPT");
    expect(normalizeStage("CodeAgent")).toBe("WRITING_MANIM_CODE");
    expect(normalizeStage("CodeAgentNode")).toBe("WRITING_MANIM_CODE");
    expect(normalizeStage("VALIDATING_CODE")).toBe("VALIDATING_CODE");
    expect(normalizeStage("CODE_REPAIRING")).toBe("CODE_REPAIRING");
    expect(normalizeStage("LLM_COLD_START")).toBe("LLM_COLD_START");
    expect(normalizeStage("LLM_RETRYING")).toBe("LLM_RETRYING");
    expect(normalizeStage("render")).toBe("RENDERING");
    expect(normalizeStage("compile")).toBe("RENDERING");
    expect(normalizeStage("upload")).toBe("RENDERING");
    expect(normalizeStage("VALIDATING_VIDEO")).toBe("VALIDATING_VIDEO");
    expect(normalizeStage("completed")).toBe("COMPLETED");
    expect(normalizeStage("failed")).toBe("FAILED");
    expect(normalizeStage("unknown_custom_stage")).toBe("STARTING");
  });

  it("parses retry and repair attempts correctly", () => {
    expect(parseAttemptInfo("Attempt 2 of 6")).toEqual({ attempt: 2, maxAttempts: 6 });
    expect(parseAttemptInfo("Repair attempt 1 / 3")).toEqual({ attempt: 1, maxAttempts: 3 });
    expect(parseAttemptInfo("attempt=3/6")).toEqual({ attempt: 3, maxAttempts: 6 });
    expect(parseAttemptInfo("Classifying topic…")).toEqual({});
  });

  it("accumulates stage events and computes durations without losing history", () => {
    const t0 = 1000;
    const t1 = 2500;
    const t2 = 6000;

    // Event 1: Start Classify
    let events = accumulateGenerationEvent([], {
      video_generation_id: "gen-1",
      status: "running",
      stage: "ClassifyNode",
      message: "Classifying topic…",
      timestamp: t0,
    });

    expect(events).toHaveLength(1);
    expect(events[0]!.stage).toBe("CLASSIFYING");
    expect(events[0]!.status).toBe("running");

    // Event 2: Move to Plan
    events = accumulateGenerationEvent(events, {
      video_generation_id: "gen-1",
      status: "running",
      stage: "PlanLectureNode",
      message: "Planning lecture…",
      timestamp: t1,
    });

    expect(events).toHaveLength(2);
    // Previous event should now be completed with exact duration
    expect(events[0]!.status).toBe("completed");
    expect(events[0]!.duration_ms).toBe(1500);
    // New active event
    expect(events[1]!.stage).toBe("PLANNING_LECTURE");
    expect(events[1]!.status).toBe("running");

    // Event 3: Move to Script
    events = accumulateGenerationEvent(events, {
      video_generation_id: "gen-1",
      status: "running",
      stage: "PlanTeachingScriptNode",
      message: "Writing teaching script…",
      timestamp: t2,
    });

    expect(events).toHaveLength(3);
    expect(events[1]!.status).toBe("completed");
    expect(events[1]!.duration_ms).toBe(3500);
    expect(events[2]!.stage).toBe("WRITING_TEACHING_SCRIPT");
  });

  it("handles self-healing repair attempts distinctly", () => {
    let events = accumulateGenerationEvent([], {
      video_generation_id: "gen-2",
      status: "running",
      stage: "CodeAgent",
      message: "Writing Manim code…",
      timestamp: 1000,
    });

    // Repair attempt 1
    events = accumulateGenerationEvent(events, {
      video_generation_id: "gen-2",
      status: "running",
      stage: "CODE_REPAIRING",
      message: "Repair attempt 1 / 3",
      timestamp: 3000,
    });

    expect(events).toHaveLength(2);
    expect(events[1]!.stage).toBe("CODE_REPAIRING");
    expect(events[1]!.attempt).toBe(1);

    // Repair attempt 2
    events = accumulateGenerationEvent(events, {
      video_generation_id: "gen-2",
      status: "running",
      stage: "CODE_REPAIRING",
      message: "Repair attempt 2 / 3",
      timestamp: 6000,
    });

    expect(events).toHaveLength(3);
    expect(events[1]!.status).toBe("completed");
    expect(events[2]!.attempt).toBe(2);
    expect(events[2]!.status).toBe("retrying");
  });

  it("calculates realistic stage progress", () => {
    const events = accumulateGenerationEvent([], {
      video_generation_id: "gen-3",
      status: "running",
      stage: "CodeAgent",
      message: "Writing Manim code…",
      timestamp: 1000,
    });

    const progress = calculateGenerationProgress(events);
    expect(progress).toBe(65);

    expect(calculateGenerationProgress([], "completed")).toBe(100);
    expect(calculateGenerationProgress([], "failed")).toBe(0);
  });

  it("formats stage durations cleanly", () => {
    expect(formatStageDuration(1800)).toBe("1.8s");
    expect(formatStageDuration(12400)).toBe("12.4s");
    expect(formatStageDuration(65000)).toBe("1m 5s");
    expect(formatStageDuration(0)).toBe("");
  });

  it("sanitizes sensitive tokens from diagnostics", () => {
    const raw = "Error with Authorization: Bearer sk-ant-secret-key-1234567890 and OPENROUTER_API_KEY=sk-or-v1-abcdef123456";
    const cleaned = sanitizeDiagnostics(raw);
    expect(cleaned).not.toContain("sk-ant-secret-key-1234567890");
    expect(cleaned).not.toContain("sk-or-v1-abcdef123456");
    expect(cleaned).toContain("Bearer [REDACTED]");
    expect(cleaned).toContain("OPENROUTER_API_KEY=[REDACTED]");
  });
});
