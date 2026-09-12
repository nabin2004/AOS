"use client";

import { useState } from "react";
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  Layers,
  Play,
  Volume2,
  Sparkles,
  Code2,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { TeachingSlideInfo } from "@/types";

interface TeachingSegmentsExplorerProps {
  slides: TeachingSlideInfo[];
  videoGenerationId: string;
}

export function TeachingSegmentsExplorer({
  slides,
  videoGenerationId,
}: TeachingSegmentsExplorerProps) {
  const [activeSlideNum, setActiveSlideNum] = useState<number>(slides[0]?.slide_num ?? 1);
  const [showCode, setShowCode] = useState<boolean>(false);
  const [playingSlideNum, setPlayingSlideNum] = useState<number | null>(null);

  if (!slides || slides.length === 0) return null;

  const currentSlide = slides.find((s) => s.slide_num === activeSlideNum) ?? slides[0];
  if (!currentSlide) return null;

  const slideStreamUrl = `/api/videos/${videoGenerationId}/slides/${currentSlide.slide_num}/stream`;

  const totalVisualDuration = slides.reduce((acc, s) => acc + (s.visual_duration || 0), 0);
  const totalLessonDuration = slides.reduce((acc, s) => acc + (s.total_duration || s.narration_duration || 0), 0);

  return (
    <div className="rounded-xl border border-border/80 bg-card/70 p-4 space-y-4 shadow-sm backdrop-blur-sm">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/40 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
            <BookOpen className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
              Teaching Segments & Visual Anchors
            </h4>
            <p className="text-[11px] text-muted-foreground">
              Rich Manim visual anchors paired with in-depth pedagogical narration
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 font-mono text-[11px]">
          <Badge variant="secondary" className="gap-1 font-normal">
            <Layers className="h-3 w-3" />
            <span>{slides.length} Segments</span>
          </Badge>
          <Badge variant="outline" className="gap-1 font-normal border-primary/30 text-primary">
            <Sparkles className="h-3 w-3" />
            <span>{totalLessonDuration.toFixed(1)}s Lesson</span>
          </Badge>
        </div>
      </div>

      {/* Segment Navigation Tabs */}
      <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none">
        {slides.map((s) => {
          const isActive = s.slide_num === activeSlideNum;
          return (
            <button
              key={s.slide_num}
              type="button"
              onClick={() => {
                setActiveSlideNum(s.slide_num);
                setShowCode(false);
              }}
              className={cn(
                "flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap border",
                isActive
                  ? "bg-primary text-primary-foreground border-primary shadow-sm"
                  : "bg-muted/40 text-muted-foreground hover:bg-muted/70 hover:text-foreground border-border/50"
              )}
            >
              <span>Segment {s.slide_num}</span>
              {s.total_duration ? (
                <span className={cn("font-mono text-[10px]", isActive ? "opacity-90" : "text-muted-foreground")}>
                  {s.total_duration.toFixed(0)}s
                </span>
              ) : null}
            </button>
          );
        })}
      </div>

      {/* Current Segment Card */}
      <div className="space-y-3.5 rounded-lg border border-border/60 bg-background/50 p-3.5">
        {/* Timing Breakdown Banner */}
        <div className="flex flex-wrap items-center justify-between gap-2 bg-muted/30 p-2.5 rounded-md border border-border/40 text-xs">
          <div className="flex items-center gap-3">
            <span className="font-semibold text-foreground">
              Segment {currentSlide.slide_num}
            </span>
            {currentSlide.layout_type && (
              <Badge variant="outline" className="text-[10px] uppercase tracking-wide">
                {currentSlide.layout_type.replace(/_/g, " ")}
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-2 font-mono text-[11px] text-muted-foreground">
            <span>Visual: <strong className="text-foreground">{currentSlide.visual_duration?.toFixed(1) ?? "—"}s</strong></span>
            <span>·</span>
            <span>Hold: <strong className="text-foreground">+{currentSlide.hold_duration?.toFixed(1) ?? "0"}s</strong></span>
            <span>·</span>
            <span>Total: <strong className="text-primary font-bold">{currentSlide.total_duration?.toFixed(1) ?? "—"}s</strong></span>
          </div>
        </div>

        {/* Slide Visual Anchor Preview / Inline Player */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-foreground/90 flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              Visual Anchor Segment
            </span>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() =>
                setPlayingSlideNum(playingSlideNum === currentSlide.slide_num ? null : currentSlide.slide_num)
              }
              className="h-7 px-2 text-[11px] gap-1 text-primary hover:text-primary"
            >
              <Play className="h-3 w-3" />
              <span>{playingSlideNum === currentSlide.slide_num ? "Hide Preview" : "Play Slide Anchor"}</span>
            </Button>
          </div>

          {playingSlideNum === currentSlide.slide_num && (
            <div className="overflow-hidden rounded-lg border border-border/70 bg-black aspect-video">
              <video
                src={slideStreamUrl}
                controls
                autoPlay
                className="w-full h-full object-contain"
              />
            </div>
          )}
        </div>

        {/* Mathematical Definitions / Symbol Breakdown */}
        {currentSlide.key_definitions && Object.keys(currentSlide.key_definitions).length > 0 && (
          <div className="space-y-2 pt-1">
            <span className="text-xs font-semibold text-foreground/90">
              Symbol Breakdown & Definitions
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {Object.entries(currentSlide.key_definitions).map(([sym, def]) => (
                <div
                  key={sym}
                  className="flex items-start gap-2 rounded-md border border-border/50 bg-muted/20 p-2 text-xs"
                >
                  <code className="px-1.5 py-0.5 rounded bg-primary/10 text-primary font-mono font-bold text-xs shrink-0">
                    {sym}
                  </code>
                  <span className="text-muted-foreground text-[11px] leading-relaxed flex-1">
                    {def}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Pedagogical Narration */}
        {currentSlide.narration && (
          <div className="space-y-1.5 pt-1">
            <span className="text-xs font-semibold text-foreground/90 flex items-center gap-1.5">
              <Volume2 className="h-3.5 w-3.5 text-muted-foreground" />
              Comprehensive Teaching Narration
            </span>
            <blockquote className="rounded-md border-l-2 border-primary/60 bg-muted/20 p-3 text-xs text-foreground/85 leading-relaxed italic">
              &ldquo;{currentSlide.narration}&rdquo;
            </blockquote>
          </div>
        )}

        {/* Per-Slide Manim Code Viewer Toggle */}
        {currentSlide.code && (
          <div className="pt-1">
            <button
              type="button"
              onClick={() => setShowCode(!showCode)}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors font-mono"
            >
              <Code2 className="h-3.5 w-3.5" />
              <span>{showCode ? "Hide Segment Code" : "View Segment Code"}</span>
              {showCode ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>

            {showCode && (
              <pre className="mt-2 p-3 rounded-lg bg-black/90 border border-border/60 text-emerald-400 font-mono text-[11px] overflow-x-auto max-h-52">
                <code>{currentSlide.code}</code>
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
