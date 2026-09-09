"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";

interface PromptViewerProps {
  prompt?: string | null;
  defaultExpanded?: boolean;
  className?: string;
}

export function PromptViewer({
  prompt,
  defaultExpanded = false,
  className = "",
}: PromptViewerProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [copied, setCopied] = useState(false);

  if (!prompt || !prompt.trim()) return null;

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={`rounded-lg border border-border/50 bg-background/60 backdrop-blur-sm transition-all text-xs ${className}`}
    >
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-muted/30 transition-colors rounded-lg group"
      >
        <div className="flex items-center gap-2 min-w-0 pr-2">
          {expanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          )}
          <span className="font-semibold text-foreground/80 shrink-0">Prompt</span>
          {!expanded && (
            <span className="text-muted-foreground truncate font-mono text-[11px]">
              &ldquo;{prompt}&rdquo;
            </span>
          )}
        </div>

        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          className="h-6 px-2 text-[11px] gap-1 text-muted-foreground hover:text-foreground shrink-0"
          title="Copy exact prompt"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3 text-emerald-500" />
              <span className="text-emerald-500 font-medium">Copied</span>
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              <span>Copy Prompt</span>
            </>
          )}
        </Button>
      </button>

      {expanded && (
        <div className="px-3 pb-3 pt-1 border-t border-border/30">
          <div className="rounded-md bg-muted/40 p-2.5 font-mono text-[11px] text-foreground/90 whitespace-pre-wrap leading-relaxed select-text border border-border/40">
            {prompt}
          </div>
        </div>
      )}
    </div>
  );
}
