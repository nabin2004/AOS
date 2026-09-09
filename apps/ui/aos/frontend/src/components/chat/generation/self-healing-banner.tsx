"use client";

import { useState } from "react";
import {
  Wrench,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface SelfHealingBannerProps {
  active?: boolean;
  attempt?: number;
  maxAttempts?: number;
  errorDetails?: string | null;
  repaired?: boolean;
  exhausted?: boolean;
  className?: string;
}

export function SelfHealingBanner({
  active = false,
  attempt = 1,
  maxAttempts = 3,
  errorDetails,
  repaired = false,
  exhausted = false,
  className = "",
}: SelfHealingBannerProps) {
  const [errorOpen, setErrorOpen] = useState(false);

  if (!active && !repaired && !exhausted) return null;

  if (repaired) {
    return (
      <div className={`rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs flex items-center gap-2.5 text-emerald-600 dark:text-emerald-400 ${className}`}>
        <CheckCircle2 className="h-4 w-4 shrink-0" />
        <div className="flex-1 font-medium">
          Animation repaired successfully
        </div>
        <Badge variant="outline" className="text-[10px] border-emerald-500/30 text-emerald-600 dark:text-emerald-400">
          Self-Healed
        </Badge>
      </div>
    );
  }

  if (exhausted) {
    return (
      <div className={`rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs space-y-2 text-foreground ${className}`}>
        <div className="flex items-center gap-2 text-destructive font-semibold">
          <XCircle className="h-4 w-4 shrink-0" />
          <span>Automatic repair exhausted ({maxAttempts}/{maxAttempts} attempts)</span>
        </div>
        <p className="text-muted-foreground text-[11px]">
          The animation encountered complex rendering constraints that could not be automatically resolved. You can retry with a slightly modified prompt or inspect the diagnostic details below.
        </p>
      </div>
    );
  }

  return (
    <div className={`rounded-xl border border-amber-500/40 bg-amber-500/10 p-3.5 space-y-2.5 text-xs ${className}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 text-amber-700 dark:text-amber-300 font-semibold">
          <Wrench className="h-4 w-4 shrink-0 animate-pulse text-amber-600 dark:text-amber-400" />
          <span>Manim rendering issue detected</span>
        </div>
        <Badge variant="outline" className="text-[10px] border-amber-500/40 text-amber-700 dark:text-amber-300 bg-amber-500/10 font-mono">
          Repair attempt {attempt} of {maxAttempts}
        </Badge>
      </div>

      <p className="text-muted-foreground text-[11px]">
        AOS is analyzing the compiler traceback and automatically synthesizing a corrected animation script.
      </p>

      {/* Ticking active repair step */}
      <div className="flex items-center gap-2 text-[11px] text-amber-600 dark:text-amber-400 font-mono font-medium pt-0.5">
        <Loader2 className="h-3.5 w-3.5 animate-spin shrink-0" />
        <span>Validating and compiling repaired animation scene…</span>
      </div>

      {errorDetails ? (
        <div className="pt-1">
          <button
            type="button"
            onClick={() => setErrorOpen(!errorOpen)}
            className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors font-mono"
          >
            {errorOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
            <span>{errorOpen ? "Hide Error Details" : "Inspect Error Details"}</span>
          </button>
          {errorOpen && (
            <pre className="mt-1.5 p-2 rounded bg-background/80 border border-border/50 text-[10px] text-destructive/90 overflow-x-auto whitespace-pre-wrap font-mono">
              {errorDetails}
            </pre>
          )}
        </div>
      ) : null}
    </div>
  );
}
