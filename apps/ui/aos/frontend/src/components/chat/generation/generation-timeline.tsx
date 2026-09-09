"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle2,
  Circle,
  Clock,
  Loader2,
  Sparkles,
  Wrench,
  XCircle,
  ChevronRight,
} from "lucide-react";
import type { GenerationStage, GenerationStageEvent, GenerationStageStatus } from "@/types";
import {
  CANONICAL_STAGES,
  STAGE_DESCRIPTIONS,
  STAGE_TITLES,
  calculateGenerationProgress,
  formatStageDuration,
} from "@/lib/generation-events";
import { Badge } from "@/components/ui/badge";

interface GenerationTimelineProps {
  events?: GenerationStageEvent[];
  currentStatus?: string;
  className?: string;
  onSelectStage?: (event: GenerationStageEvent) => void;
  selectedStageId?: string | null;
}

export function GenerationTimeline({
  events = [],
  currentStatus,
  className = "",
  onSelectStage,
  selectedStageId,
}: GenerationTimelineProps) {
  // Ticking timer for currently running stage duration
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (currentStatus === "completed" || currentStatus === "failed") return;
    const interval = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(interval);
  }, [currentStatus]);

  const progressPct = calculateGenerationProgress(events, currentStatus);

  // Map executed events by stage
  const executedMap = new Map<GenerationStage, GenerationStageEvent>();
  events.forEach((ev) => {
    executedMap.set(ev.stage, ev);
  });

  // Find the highest reached canonical stage index
  let highestCanonicalIndex = -1;
  CANONICAL_STAGES.forEach((cs, idx) => {
    if (executedMap.has(cs)) {
      highestCanonicalIndex = Math.max(highestCanonicalIndex, idx);
    }
  });

  // Combine canonical stages with any active transient stages (like COLD_START or REPAIR)
  const transientEvents = events.filter(
    (ev) =>
      ev.stage === "LLM_COLD_START" ||
      ev.stage === "LLM_RETRYING" ||
      ev.stage === "CODE_REPAIRING",
  );

  // Build the rendered rows
  interface TimelineRowItem {
    key: string;
    stage: GenerationStage;
    title: string;
    description: string;
    status: GenerationStageStatus;
    durationText: string;
    event?: GenerationStageEvent;
    isTransient?: boolean;
    attempt?: number;
    maxAttempts?: number;
  }

  const rows: TimelineRowItem[] = [];

  // Add transient events first if in-progress or recently occurred
  transientEvents.forEach((tev, idx) => {
    const isRunning = tev.status === "running" || tev.status === "retrying";
    const durationMs = tev.duration_ms ?? (isRunning ? Math.max(100, now - tev.timestamp) : undefined);
    rows.push({
      key: `transient-${tev.stage}-${idx}`,
      stage: tev.stage,
      title: tev.name || STAGE_TITLES[tev.stage],
      description: tev.message || STAGE_DESCRIPTIONS[tev.stage],
      status: tev.status,
      durationText: formatStageDuration(durationMs),
      event: tev,
      isTransient: true,
      attempt: tev.attempt,
      maxAttempts: tev.maxAttempts,
    });
  });

  // Add canonical stages
  CANONICAL_STAGES.forEach((stage, idx) => {
    const executed = executedMap.get(stage);
    let status: GenerationStageStatus = "waiting";
    let durationMs: number | undefined;

    if (executed) {
      status = executed.status;
      durationMs =
        executed.duration_ms ??
        (status === "running" ? Math.max(100, now - executed.timestamp) : undefined);
    } else if (idx < highestCanonicalIndex) {
      status = "completed";
    }

    rows.push({
      key: `canonical-${stage}`,
      stage,
      title: STAGE_TITLES[stage],
      description: executed?.message || STAGE_DESCRIPTIONS[stage],
      status,
      durationText: formatStageDuration(durationMs),
      event: executed,
      isTransient: false,
      attempt: executed?.attempt,
      maxAttempts: executed?.maxAttempts,
    });
  });

  const getStatusIcon = (row: TimelineRowItem) => {
    switch (row.status) {
      case "completed":
        return <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-destructive shrink-0" />;
      case "retrying":
        if (row.stage === "CODE_REPAIRING") {
          return <Wrench className="h-4 w-4 text-amber-500 animate-pulse shrink-0" />;
        }
        return <Sparkles className="h-4 w-4 text-blue-500 animate-spin shrink-0" />;
      case "running":
        return <Loader2 className="h-4 w-4 text-primary animate-spin shrink-0" />;
      case "waiting":
      default:
        return <Circle className="h-3.5 w-3.5 text-muted-foreground/40 shrink-0" />;
    }
  };

  return (
    <div className={`rounded-xl border border-border/60 bg-card/50 backdrop-blur-sm p-3.5 space-y-3 ${className}`}>
      {/* Header with real percentage */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="font-semibold text-xs text-foreground tracking-wide flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-muted-foreground" />
            <span>Generation Activity</span>
          </div>
          {currentStatus === "running" && (
            <Badge variant="outline" className="text-[10px] py-0 px-1.5 font-normal animate-pulse border-primary/40 text-primary">
              Live
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2 text-xs font-mono font-medium text-foreground/80">
          <span>{progressPct}%</span>
        </div>
      </div>

      {/* Progress track */}
      <div className="w-full bg-muted/60 rounded-full h-1.5 overflow-hidden">
        <div
          className={`h-full transition-all duration-300 rounded-full ${
            currentStatus === "failed"
              ? "bg-destructive"
              : currentStatus === "completed"
              ? "bg-emerald-500"
              : "bg-primary"
          }`}
          style={{ width: `${Math.min(100, Math.max(5, progressPct))}%` }}
        />
      </div>

      {/* Stage Timeline List */}
      <div className="space-y-1.5 pt-1">
        {rows.map((row) => {
          const isSelected = Boolean(selectedStageId && row.event && row.event.id === selectedStageId);
          const isInteractive = Boolean(onSelectStage && row.event && (row.event.output || row.event.input));

          const rowContent = (
            <>
              <div className="flex items-center gap-2.5 min-w-0 pr-2">
                {getStatusIcon(row)}
                <span className={`truncate ${row.status === "running" ? "text-foreground font-semibold" : ""}`}>
                  {row.title}
                </span>

                {row.attempt && row.maxAttempts ? (
                  <Badge variant="outline" className="text-[9px] px-1 py-0 h-4 border-amber-500/30 text-amber-600 dark:text-amber-400 font-mono">
                    Attempt {row.attempt}/{row.maxAttempts}
                  </Badge>
                ) : null}
              </div>

              <div className="flex items-center gap-2 shrink-0 text-[11px] font-mono">
                {row.status === "running" && (
                  <span className="text-primary font-medium">Running · {row.durationText}</span>
                )}
                {row.status === "retrying" && (
                  <span className="text-amber-500 font-medium">Retrying · {row.durationText}</span>
                )}
                {row.status === "completed" && row.durationText && (
                  <span className="text-muted-foreground">{row.durationText}</span>
                )}
                {row.status === "waiting" && (
                  <span className="text-muted-foreground/40">Waiting</span>
                )}
                {row.status === "failed" && (
                  <span className="text-destructive font-medium">Failed</span>
                )}

                {isInteractive && (
                  <ChevronRight className={`h-3 w-3 text-muted-foreground transition-transform ${isSelected ? "rotate-90 text-primary" : ""}`} />
                )}
              </div>
            </>
          );

          const className = `w-full flex items-center justify-between px-2 py-1.5 rounded-lg text-xs transition-colors text-left ${
            row.status === "running" || row.status === "retrying"
              ? "bg-primary/5 border border-primary/15 font-medium"
              : row.status === "completed"
              ? "text-foreground/90"
              : "text-muted-foreground/60"
          } ${isInteractive ? "cursor-pointer hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary" : ""} ${
            isSelected ? "ring-1 ring-primary/40 bg-muted/40" : ""
          }`;

          return isInteractive ? (
            <button
              key={row.key}
              type="button"
              onClick={() => {
                if (onSelectStage && row.event) {
                  onSelectStage(row.event);
                }
              }}
              className={className}
            >
              {rowContent}
            </button>
          ) : (
            <div key={row.key} className={className}>
              {rowContent}
            </div>
          );
        })}
      </div>
    </div>
  );
}
