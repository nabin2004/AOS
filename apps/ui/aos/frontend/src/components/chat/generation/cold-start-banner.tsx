"use client";

import { Sparkles, CheckCircle2, RotateCw, Bot } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface ColdStartBannerProps {
  active?: boolean;
  isRetry?: boolean;
  ready?: boolean;
  attempt?: number;
  maxAttempts?: number;
  className?: string;
}

export function ColdStartBanner({
  active = false,
  isRetry = false,
  ready = false,
  attempt = 1,
  maxAttempts = 6,
  className = "",
}: ColdStartBannerProps) {
  if (!active && !ready) return null;

  if (ready) {
    return (
      <div className={`rounded-xl border border-blue-500/30 bg-blue-500/10 p-3 text-xs flex items-center gap-2.5 text-blue-600 dark:text-blue-400 ${className}`}>
        <CheckCircle2 className="h-4 w-4 shrink-0" />
        <div className="flex-1 font-medium">
          AI model is ready. Continuing animation generation…
        </div>
      </div>
    );
  }

  return (
    <div className={`rounded-xl border border-blue-500/40 bg-blue-500/10 p-3.5 space-y-2 text-xs text-foreground ${className}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300 font-semibold">
          {isRetry ? (
            <RotateCw className="h-4 w-4 shrink-0 animate-spin text-blue-600 dark:text-blue-400" />
          ) : (
            <Bot className="h-4 w-4 shrink-0 text-blue-600 dark:text-blue-400" />
          )}
          <span>{isRetry ? "Retrying Model Request" : "Model Booting"}</span>
        </div>
        <Badge variant="outline" className="text-[10px] border-blue-500/40 text-blue-700 dark:text-blue-300 bg-blue-500/10 font-mono">
          Attempt {attempt} of {maxAttempts}
        </Badge>
      </div>

      <p className="text-muted-foreground text-[11px] leading-relaxed">
        The animation model was idle and is waking up in the cloud. This can take 15–30 seconds on the first request. The system is retrying automatically.
      </p>

      <div className="flex items-center gap-2 text-[11px] text-blue-600 dark:text-blue-400 font-mono font-medium pt-0.5">
        <Sparkles className="h-3 w-3 animate-pulse" />
        <span>Retrying automatically with exponential backoff…</span>
      </div>
    </div>
  );
}
