"use client";

import { useEffect, useState } from "react";
import {
  Code2,
  Copy,
  Check,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface ManimCodeViewerProps {
  code?: string | null;
  videoGenerationId?: string;
  defaultExpanded?: boolean;
  validationFailed?: boolean;
  validationError?: string | null;
  repaired?: boolean;
  repairAttempt?: number;
  maxRepairAttempts?: number;
  className?: string;
}

export function ManimCodeViewer({
  code: initialCode,
  videoGenerationId,
  defaultExpanded = false,
  validationFailed = false,
  validationError,
  repaired = false,
  repairAttempt,
  maxRepairAttempts = 3,
  className = "",
}: ManimCodeViewerProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [copied, setCopied] = useState(false);
  const [code, setCode] = useState<string | null>(initialCode ?? null);
  const [loading, setLoading] = useState(false);

  // Sync initialCode or fetch from `/api/videos/${id}/code` if missing
  useEffect(() => {
    if (initialCode) {
      setCode(initialCode);
      return;
    }
    if (expanded && !code && videoGenerationId) {
      setLoading(true);
      fetch(`/api/videos/${videoGenerationId}/code`)
        .then((res) => {
          if (res.ok) return res.text();
          return null;
        })
        .then((text) => {
          if (text) setCode(text);
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [initialCode, expanded, code, videoGenerationId]);

  if (!code && !loading && !validationFailed && !videoGenerationId) {
    return null;
  }

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (code) {
      navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const lines = code ? code.split("\n") : [];
  const lineCount = lines.length;
  const byteCount = code ? new Blob([code]).size : 0;
  const sizeText = byteCount > 1024 ? `${(byteCount / 1024).toFixed(1)} KB` : `${byteCount} B`;

  return (
    <div className={`rounded-xl border border-border/60 bg-card/60 backdrop-blur-sm transition-all overflow-hidden ${className}`}>
      {/* Collapsible header */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        className="w-full flex items-center justify-between px-3.5 py-2.5 text-left hover:bg-muted/30 transition-colors group select-none"
      >
        <div className="flex items-center gap-2 min-w-0 pr-2">
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
          )}

          <div className="flex items-center gap-1.5 font-semibold text-xs text-foreground">
            <Code2 className="h-4 w-4 text-primary shrink-0" />
            <span>Manim Code</span>
          </div>

          <Badge variant="secondary" className="text-[10px] font-mono px-1.5 py-0 h-4">
            Python
          </Badge>

          {validationFailed ? (
            <Badge variant="destructive" className="text-[10px] gap-1 px-1.5 py-0 h-4">
              <AlertTriangle className="h-2.5 w-2.5" />
              <span>Validation failed</span>
            </Badge>
          ) : repaired ? (
            <Badge variant="outline" className="text-[10px] gap-1 px-1.5 py-0 h-4 border-emerald-500/30 text-emerald-600 dark:text-emerald-400 bg-emerald-500/5">
              <CheckCircle2 className="h-2.5 w-2.5" />
              <span>Code repaired</span>
              {repairAttempt ? ` (${repairAttempt}/${maxRepairAttempts})` : ""}
            </Badge>
          ) : lineCount > 0 ? (
            <span className="text-[11px] text-muted-foreground font-mono">
              {lineCount} lines · {sizeText}
            </span>
          ) : null}
        </div>

        {code ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-6 px-2 text-[11px] gap-1 text-muted-foreground hover:text-foreground shrink-0"
            title="Copy Python code"
          >
            {copied ? (
              <>
                <Check className="h-3 w-3 text-emerald-500" />
                <span className="text-emerald-500 font-medium">Copied</span>
              </>
            ) : (
              <>
                <Copy className="h-3 w-3" />
                <span>Copy Code</span>
              </>
            )}
          </Button>
        ) : null}
      </button>

      {/* Expanded code body */}
      {expanded && (
        <div className="border-t border-border/40">
          {/* Validation error notice if failed */}
          {validationFailed && validationError ? (
            <div className="p-3 bg-destructive/10 border-b border-destructive/20 text-xs space-y-1 font-mono">
              <div className="flex items-center gap-1.5 text-destructive font-semibold">
                <AlertTriangle className="h-3.5 w-3.5" />
                <span>Compiler / Validation Error</span>
                {repairAttempt ? (
                  <span className="text-muted-foreground font-normal">
                    · Repair attempt {repairAttempt} of {maxRepairAttempts}
                  </span>
                ) : null}
              </div>
              <pre className="whitespace-pre-wrap text-[11px] text-destructive/90 overflow-x-auto p-2 rounded bg-background/50 border border-destructive/20">
                {validationError}
              </pre>
            </div>
          ) : null}

          {loading ? (
            <div className="flex items-center justify-center py-8 gap-2 text-xs text-muted-foreground font-mono">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <span>Loading scene source code…</span>
            </div>
          ) : code ? (
            <div className="relative max-h-80 overflow-y-auto overflow-x-auto bg-muted/20 font-mono text-[11px] leading-5 select-text p-2">
              <div className="flex min-w-full">
                {/* Line numbers column */}
                <div
                  className="select-none pr-3 pl-1 text-right text-muted-foreground/40 shrink-0 border-r border-border/40 font-mono"
                  aria-hidden="true"
                >
                  {lines.map((_, i) => (
                    <div key={`line-num-${i + 1}`}>{i + 1}</div>
                  ))}
                </div>

                {/* Code lines */}
                <div className="pl-3 pr-2 text-foreground/90 whitespace-pre overflow-x-auto font-mono flex-1">
                  {lines.map((line, i) => (
                    <div key={`line-content-${i + 1}`} className="hover:bg-muted/30 rounded px-0.5">
                      {line || " "}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-4 text-xs text-muted-foreground text-center font-mono">
              Code will appear here once synthesized by the coder agent.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
