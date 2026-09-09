"use client";

import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Layers,
  CheckCircle2,
  Clock,
  Cpu,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { formatStageDuration } from "@/lib/generation-events";

interface StageDetailPanelProps {
  title: string;
  stageName?: string;
  input?: unknown;
  output?: unknown;
  metadata?: {
    model?: string | null;
    durationMs?: number | null;
    status?: string | null;
    tokens?: number | null;
  };
  defaultExpanded?: boolean;
  className?: string;
}

export function StageDetailPanel({
  title,
  stageName,
  input,
  output,
  metadata,
  defaultExpanded = false,
  className = "",
}: StageDetailPanelProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  if (!input && !output && !metadata) return null;

  const formatJson = (val: unknown): string => {
    if (typeof val === "string") return val;
    try {
      return JSON.stringify(val, null, 2);
    } catch {
      return String(val);
    }
  };

  return (
    <div className={`rounded-xl border border-border/60 bg-card/40 backdrop-blur-sm overflow-hidden text-xs ${className}`}>
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        className="w-full flex items-center justify-between px-3.5 py-2 text-left hover:bg-muted/30 transition-colors group select-none"
      >
        <div className="flex items-center gap-2 min-w-0 pr-2">
          {expanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          )}

          <div className="flex items-center gap-1.5 font-semibold text-foreground/90">
            <Layers className="h-3.5 w-3.5 text-primary shrink-0" />
            <span>{title}</span>
          </div>

          {stageName && (
            <Badge variant="outline" className="text-[9px] font-mono px-1.5 py-0 h-4 text-muted-foreground">
              {stageName}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0 text-[11px] font-mono text-muted-foreground">
          {metadata?.durationMs ? (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatStageDuration(metadata.durationMs)}
            </span>
          ) : null}
          {metadata?.status === "completed" && (
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-3.5 pb-3 pt-1 border-t border-border/30 space-y-3">
          {/* Metadata Bar */}
          {metadata && (
            <div className="flex flex-wrap items-center gap-3 text-[11px] font-mono text-muted-foreground py-1 bg-muted/20 px-2.5 rounded border border-border/40">
              {metadata.model && (
                <div className="flex items-center gap-1">
                  <Cpu className="h-3 w-3 text-primary" />
                  <span>Model: </span>
                  <span className="text-foreground/80">{metadata.model}</span>
                </div>
              )}
              {metadata.durationMs ? (
                <div>
                  <span>Duration: </span>
                  <span className="text-foreground/80">{formatStageDuration(metadata.durationMs)}</span>
                </div>
              ) : null}
              {metadata.status && (
                <div>
                  <span>Status: </span>
                  <span className="text-foreground/80">{metadata.status}</span>
                </div>
              )}
              {metadata.tokens ? (
                <div>
                  <span>Tokens: </span>
                  <span className="text-foreground/80">{metadata.tokens}</span>
                </div>
              ) : null}
            </div>
          )}

          {/* Input Section */}
          {input ? (
            <div className="space-y-1">
              <div className="font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
                Input
              </div>
              <pre className="rounded bg-background/60 p-2.5 font-mono text-[11px] text-foreground/85 whitespace-pre-wrap max-h-40 overflow-y-auto border border-border/40">
                {formatJson(input)}
              </pre>
            </div>
          ) : null}

          {/* Output Section */}
          {output ? (
            <div className="space-y-1">
              <div className="font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
                Output
              </div>
              <pre className="rounded bg-background/60 p-2.5 font-mono text-[11px] text-foreground/85 whitespace-pre-wrap max-h-52 overflow-y-auto border border-border/40">
                {formatJson(output)}
              </pre>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
