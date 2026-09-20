"use client";

import React, { useState } from "react";
import { useCritiqueStore } from "@/stores";
import { X, Split, GitBranch, ArrowLeftRight } from "lucide-react";
import { Button, Badge } from "@/components/ui";
import { AppVideoPlayer } from "@/components/media/video-player";

interface RevisionCompareModalProps {
  videoGenerationId: string;
}

export function RevisionCompareModal({ videoGenerationId }: RevisionCompareModalProps) {
  const revisions = useCritiqueStore((s) => s.revisions[videoGenerationId] || []);
  const activeRevision = useCritiqueStore((s) => s.activeRevision[videoGenerationId] || 1);
  const compareRevision = useCritiqueStore((s) => s.compareRevision[videoGenerationId] || 1);
  const isComparing = useCritiqueStore((s) => Boolean(s.isComparing[videoGenerationId]));
  const toggleCompare = useCritiqueStore((s) => s.toggleCompare);
  const setCompareRevision = useCritiqueStore((s) => s.setCompareRevision);

  if (!isComparing || revisions.length < 2) {
    return null;
  }

  const revA = revisions.find((r) => r.revision === compareRevision) || revisions[0];
  const revB = revisions.find((r) => r.revision === activeRevision) || revisions[revisions.length - 1];

  return (
    <div className="rounded-2xl border border-primary/40 bg-card/95 p-4 shadow-xl space-y-3">
      <div className="flex items-center justify-between border-b border-border/60 pb-2.5">
        <div className="flex items-center gap-2">
          <Split className="h-4 w-4 text-primary" />
          <span className="text-sm font-bold text-foreground">
            Revision Comparison Mode
          </span>
          <Badge variant="outline" className="text-[10px] font-mono">
            v{revA.revision} vs v{revB.revision}
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 text-xs">
            <span className="text-muted-foreground">Compare with:</span>
            <select
              value={revA.revision}
              onChange={(e) => setCompareRevision(videoGenerationId, parseInt(e.target.value, 10))}
              className="rounded-md border border-border bg-background px-2 py-1 text-xs font-mono"
            >
              {revisions.map((r) => (
                <option key={r.revision} value={r.revision} disabled={r.revision === revB.revision}>
                  Revision {r.revision}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            onClick={() => toggleCompare(videoGenerationId)}
            className="rounded-lg p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Side-by-Side Dual Players */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Revision A */}
        <div className="space-y-1.5 rounded-xl border border-border/70 bg-background/50 p-2.5">
          <div className="flex items-center justify-between text-xs font-semibold">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <GitBranch className="h-3.5 w-3.5" />
              <span>Earlier: Revision {revA.revision}</span>
            </span>
            {revA.critique_tags.length > 0 && (
              <span className="text-[10px] font-mono text-amber-400">
                {revA.critique_tags.join(", ")}
              </span>
            )}
          </div>
          <div className="overflow-hidden rounded-lg bg-black aspect-video">
            <AppVideoPlayer
              src={revA.stream_url}
              className="w-full h-full"
            />
          </div>
        </div>

        {/* Revision B */}
        <div className="space-y-1.5 rounded-xl border border-primary/40 bg-primary/5 p-2.5">
          <div className="flex items-center justify-between text-xs font-semibold">
            <span className="flex items-center gap-1.5 text-primary">
              <GitBranch className="h-3.5 w-3.5" />
              <span>Current: Revision {revB.revision}</span>
            </span>
            {revB.accepted ? (
              <span className="text-[10px] font-mono text-emerald-400">
                ✓ Verified Final
              </span>
            ) : (
              <span className="text-[10px] font-mono text-primary">
                Active Iteration
              </span>
            )}
          </div>
          <div className="overflow-hidden rounded-lg bg-black aspect-video border border-primary/30">
            <AppVideoPlayer
              src={revB.stream_url}
              className="w-full h-full"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
