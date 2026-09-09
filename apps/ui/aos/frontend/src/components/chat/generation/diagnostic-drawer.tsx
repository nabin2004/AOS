"use client";

import { useState } from "react";
import { Terminal, Copy, Check, ChevronDown, ChevronRight, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { sanitizeDiagnostics } from "@/lib/generation-events";

interface DiagnosticDrawerProps {
  jobId: string;
  taskId?: string | null;
  model?: string | null;
  provider?: string | null;
  stage?: string | null;
  mode?: string | null;
  runDir?: string | null;
  videoPath?: string | null;
  rawError?: string | null;
  errorCategory?: string | null;
  durationSeconds?: number | null;
  retryCount?: number | null;
  contextUsage?: { used: number; max: number } | null;
  defaultExpanded?: boolean;
  className?: string;
}

export function DiagnosticDrawer({
  jobId,
  taskId,
  model,
  provider,
  stage,
  mode,
  runDir,
  videoPath,
  rawError,
  errorCategory,
  durationSeconds,
  retryCount,
  contextUsage,
  defaultExpanded = false,
  className = "",
}: DiagnosticDrawerProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [copied, setCopied] = useState(false);

  const cleanError = sanitizeDiagnostics(rawError);

  const diagnosticPayload = {
    job_id: jobId,
    task_id: taskId || null,
    model: model || null,
    provider: provider || null,
    stage: stage || null,
    mode: mode || "animate",
    run_dir: runDir || null,
    video_path: videoPath || null,
    error_category: errorCategory || null,
    duration_seconds: durationSeconds || null,
    retry_count: retryCount || 0,
    context_usage: contextUsage || null,
    error: cleanError || null,
  };

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(JSON.stringify(diagnosticPayload, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`rounded-xl border border-border/50 bg-muted/30 backdrop-blur-sm overflow-hidden text-xs ${className}`}>
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        className="w-full flex items-center justify-between px-3.5 py-2 text-left hover:bg-muted/40 transition-colors group select-none"
      >
        <div className="flex items-center gap-2 min-w-0 pr-2">
          {expanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          )}

          <div className="flex items-center gap-1.5 font-medium text-muted-foreground group-hover:text-foreground transition-colors">
            <Terminal className="h-3.5 w-3.5 shrink-0" />
            <span>Developer / Diagnostic Details</span>
          </div>
        </div>

        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          className="h-6 px-2 text-[11px] gap-1 text-muted-foreground hover:text-foreground shrink-0"
          title="Copy JSON diagnostics"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3 text-emerald-500" />
              <span className="text-emerald-500 font-medium">Copied</span>
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              <span>Copy Diagnostics</span>
            </>
          )}
        </Button>
      </button>

      {expanded && (
        <div className="px-3.5 pb-3 pt-1 border-t border-border/30 space-y-2 font-mono text-[11px] text-muted-foreground">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 py-1">
            <div>
              <span className="text-foreground/70 font-semibold">Job ID: </span>
              <span className="select-all">{jobId}</span>
            </div>
            {taskId ? (
              <div>
                <span className="text-foreground/70 font-semibold">Task ID: </span>
                <span className="select-all">{taskId}</span>
              </div>
            ) : null}
            {stage ? (
              <div>
                <span className="text-foreground/70 font-semibold">Stage: </span>
                <span>{stage}</span>
              </div>
            ) : null}
            {mode ? (
              <div>
                <span className="text-foreground/70 font-semibold">Mode: </span>
                <span>{mode}</span>
              </div>
            ) : null}
            {model ? (
              <div>
                <span className="text-foreground/70 font-semibold">Model: </span>
                <span>{model}</span>
              </div>
            ) : null}
            {provider ? (
              <div>
                <span className="text-foreground/70 font-semibold">Provider: </span>
                <span>{provider}</span>
              </div>
            ) : null}
            {durationSeconds ? (
              <div>
                <span className="text-foreground/70 font-semibold">Duration: </span>
                <span>{durationSeconds.toFixed(1)}s</span>
              </div>
            ) : null}
            {retryCount != null && retryCount > 0 ? (
              <div>
                <span className="text-foreground/70 font-semibold">Retries: </span>
                <span>{retryCount}</span>
              </div>
            ) : null}
            {contextUsage ? (
              <div>
                <span className="text-foreground/70 font-semibold">Context Budget: </span>
                <span>
                  {contextUsage.used.toLocaleString()} / {contextUsage.max.toLocaleString()} tokens
                </span>
              </div>
            ) : null}
            {runDir ? (
              <div className="col-span-full truncate">
                <span className="text-foreground/70 font-semibold">Run Dir: </span>
                <span className="select-all">{runDir}</span>
              </div>
            ) : null}
            {videoPath ? (
              <div className="col-span-full truncate">
                <span className="text-foreground/70 font-semibold">Video Path: </span>
                <span className="select-all">{videoPath}</span>
              </div>
            ) : null}
          </div>

          {cleanError ? (
            <div className="pt-1.5 space-y-1">
              <div className="flex items-center gap-1.5 text-foreground/80 font-semibold">
                <ShieldAlert className="h-3.5 w-3.5 text-amber-500" />
                <span>Raw Diagnostic Logs (Sanitized):</span>
              </div>
              <pre className="rounded bg-background/80 p-2.5 text-[10px] text-destructive/90 overflow-x-auto whitespace-pre-wrap max-h-52 border border-border/50">
                {cleanError}
              </pre>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
