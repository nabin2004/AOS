"use client";

import React from "react";
import { useCritiqueStore } from "@/stores";
import { CheckCircle2, GitBranch, Split, History, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui";

interface RevisionHistoryBarProps {
  videoGenerationId: string;
}

export function RevisionHistoryBar({ videoGenerationId }: RevisionHistoryBarProps) {
  const revisions = useCritiqueStore((s) => s.revisions[videoGenerationId] || []);
  const activeRevision = useCritiqueStore((s) => s.activeRevision[videoGenerationId] || 1);
  const isComparing = useCritiqueStore((s) => Boolean(s.isComparing[videoGenerationId]));
  const setActiveRevision = useCritiqueStore((s) => s.setActiveRevision);
  const toggleCompare = useCritiqueStore((s) => s.toggleCompare);

  if (!revisions || revisions.length === 0) {
    return null;
  }

  const activeRevObj = revisions.find((r) => r.revision === activeRevision);
  const hasAccepted = revisions.some((r) => r.accepted);

  return (
    <div className="rounded-xl border border-border/70 bg-card/60 p-3 space-y-2.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <History className="h-4 w-4 text-primary" />
          <span className="text-xs font-semibold text-foreground">
            Revision History ({revisions.length} version{revisions.length === 1 ? "" : "s"})
          </span>
          {hasAccepted && (
            <Badge variant="outline" className="border-emerald-500/40 bg-emerald-500/10 text-emerald-400 text-[10px] gap-1 py-0">
              <CheckCircle2 className="h-3 w-3" />
              Verified Final
            </Badge>
          )}
        </div>

        {revisions.length > 1 && (
          <button
            type="button"
            onClick={() => toggleCompare(videoGenerationId)}
            className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors ${
              isComparing
                ? "border-primary bg-primary/10 text-primary"
                : "border-border bg-accent/40 text-foreground/75 hover:bg-accent hover:text-foreground"
            }`}
          >
            <Split className="h-3.5 w-3.5" />
            <span>{isComparing ? "Exit Compare Mode" : "Compare Revisions"}</span>
          </button>
        )}
      </div>

      {/* Revision Pills */}
      <div className="flex flex-wrap gap-2">
        {revisions.map((rev) => {
          const isActive = rev.revision === activeRevision;
          return (
            <button
              key={rev.revision}
              type="button"
              onClick={() => setActiveRevision(videoGenerationId, rev.revision)}
              className={`group flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs transition-all ${
                isActive
                  ? "border-primary bg-primary/15 text-foreground shadow-xs font-medium"
                  : "border-border/70 bg-background/50 text-foreground/70 hover:border-foreground/30 hover:bg-accent/50 hover:text-foreground"
              }`}
            >
              <GitBranch className={`h-3.5 w-3.5 ${isActive ? "text-primary" : "text-muted-foreground"}`} />
              <span>Revision {rev.revision}</span>
              {rev.accepted && (
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
              )}
              {rev.critique_tags.length > 0 && !rev.accepted && (
                <span className="text-[10px] font-mono text-muted-foreground">
                  ({rev.critique_tags.length} issue{rev.critique_tags.length === 1 ? "" : "s"})
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Current Revision Tags & Critique Summary */}
      {activeRevObj && activeRevObj.critique_tags.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-1 text-[11px]">
          <span className="text-muted-foreground font-mono text-[10px]">Identified issues:</span>
          {activeRevObj.critique_tags.map((tag, idx) => (
            <span
              key={idx}
              className={`rounded-md px-2 py-0.5 font-mono text-[10px] border ${
                tag.startsWith("✓")
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                  : "border-amber-500/30 bg-amber-500/10 text-amber-300"
              }`}
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
