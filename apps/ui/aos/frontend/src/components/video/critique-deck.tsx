"use client";

import React, { useState } from "react";
import {
  useCritiqueStore,
  type CritiqueCategory,
  type SeverityLevel,
} from "@/stores/critique-store";
import {
  CheckCircle2,
  Wand2,
  Clock,
  Eye,
  Move,
  Waves,
  FlaskConical,
  Lightbulb,
  Mic,
  AlertTriangle,
  Sparkles,
  Send,
  Clapperboard,
  Crosshair,
} from "lucide-react";
import { Button, Input, Textarea, Badge } from "@/components/ui";

interface CritiqueDeckProps {
  videoGenerationId: string;
  code?: string | null;
  onRepairRequested?: (category: string, feedback: string) => void;
}

interface FailureOption {
  id: CritiqueCategory;
  label: string;
  description: string;
  icon: React.ElementType;
  dimension: "visual" | "scientific";
}

const FAILURE_OPTIONS: FailureOption[] = [
  // Visual Correctness
  {
    id: "positioning",
    label: "Fix Positioning",
    description: "Objects overlapping, colliding labels, or clipping screen boundaries",
    icon: Move,
    dimension: "visual",
  },
  {
    id: "visual_drift",
    label: "Fix Visual Drift",
    description: "Animation trajectory deviates from initial plan/scene graph over time",
    icon: Waves,
    dimension: "visual",
  },
  {
    id: "visibility",
    label: "Improve Visibility",
    description: "Formulas or curves too small, thin strokes, or poor contrast",
    icon: Eye,
    dimension: "visual",
  },
  {
    id: "animation",
    label: "Fix Animation",
    description: "Motion dynamics, easing function, or transform transition is awkward",
    icon: Clapperboard,
    dimension: "visual",
  },
  {
    id: "timing",
    label: "Fix Timing & Sync",
    description: "Animation too fast/slow or visual beats out of sync with narration",
    icon: Clock,
    dimension: "visual",
  },

  // Scientific Correctness
  {
    id: "scientific_accuracy",
    label: "Scientific Accuracy",
    description: "Mathematical error, wrong formula, or invalid physical parameters",
    icon: FlaskConical,
    dimension: "scientific",
  },
  {
    id: "explanation",
    label: "Improve Explanation",
    description: "Technically present but confusing; needs better visual proof or arrows",
    icon: Lightbulb,
    dimension: "scientific",
  },
  {
    id: "narration",
    label: "Fix Narration",
    description: "Spoken voiceover phrasing incorrect or awkward pronunciation",
    icon: Mic,
    dimension: "scientific",
  },
];

export function CritiqueDeck({
  videoGenerationId,
  code,
  onRepairRequested,
}: CritiqueDeckProps) {
  const activeRevision = useCritiqueStore(
    (s) => s.activeRevision[videoGenerationId] || 1,
  );
  const selectedCategory = useCritiqueStore((s) => s.selectedCategory);
  const setSelectedCategory = useCritiqueStore((s) => s.setSelectedCategory);
  const feedbackText = useCritiqueStore((s) => s.feedbackText);
  const setFeedbackText = useCritiqueStore((s) => s.setFeedbackText);
  const targetObject = useCritiqueStore((s) => s.targetObject);
  const setTargetObject = useCritiqueStore((s) => s.setTargetObject);
  const severity = useCritiqueStore((s) => s.severity);
  const setSeverity = useCritiqueStore((s) => s.setSeverity);
  const currentTimestamp = useCritiqueStore((s) => s.currentTimestamp);
  const isSubmitting = useCritiqueStore((s) => s.isSubmitting);
  const submissionMessage = useCritiqueStore((s) => s.submissionMessage);
  const submitCritique = useCritiqueStore((s) => s.submitCritique);
  const acceptRevision = useCritiqueStore((s) => s.acceptRevision);
  const acceptedRevisions = useCritiqueStore(
    (s) => s.acceptedRevisions[videoGenerationId] || false,
  );
  const isCritiqueMode = useCritiqueStore(
    (s) => s.critiqueModeActive[videoGenerationId] || false,
  );
  const toggleCritiqueMode = useCritiqueStore((s) => s.toggleCritiqueMode);
  const spatialCorrection = useCritiqueStore((s) => s.spatialCorrection);

  const [activeTab, setActiveTab] = useState<"visual" | "scientific">("visual");

  const handleQuickCategoryClick = (cat: CritiqueCategory) => {
    if (selectedCategory === cat) {
      setSelectedCategory(null);
    } else {
      setSelectedCategory(cat);
      // If user clicks a button and hasn't typed feedback, provide an intuitive seed
      if (!feedbackText.trim()) {
        const opt = FAILURE_OPTIONS.find((o) => o.id === cat);
        if (opt) {
          setFeedbackText(
            `Please review ${opt.label.toLowerCase()}: ${opt.description}.`,
          );
        }
      }
    }
  };

  const handleSubmit = async () => {
    const success = await submitCritique(
      videoGenerationId,
      activeRevision,
      code || undefined,
    );
    if (success && onRepairRequested && selectedCategory) {
      onRepairRequested(selectedCategory, feedbackText);
    }
  };

  const handleAccept = async () => {
    await acceptRevision(videoGenerationId, activeRevision);
  };

  const formatTimestamp = (s: number) => {
    const mins = Math.floor(s / 60);
    const secs = Math.floor(s % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="rounded-xl border border-border/80 bg-card/85 p-4 space-y-4 shadow-sm">
      {/* Reviewer Header & Acceptance Actions */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-foreground">
              Visual & Scientific Reviewer Deck
            </span>
            <Badge
              variant="outline"
              className="text-[10px] font-mono uppercase tracking-wider"
            >
              Revision {activeRevision}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            Inspect the animation. If anything drifts, collides, or lacks
            accuracy, critique and command an agent repair.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant={isCritiqueMode ? "default" : "outline"}
            onClick={() => toggleCritiqueMode(videoGenerationId)}
            className={`h-8 gap-1.5 text-xs font-medium ${
              isCritiqueMode
                ? "bg-amber-500 text-black hover:bg-amber-400 font-semibold"
                : "border-amber-500/40 text-amber-500 hover:bg-amber-500/10"
            }`}
          >
            <Crosshair className="h-3.5 w-3.5" />
            <span>{isCritiqueMode ? "Critique Mode On" : "Critique Mode"}</span>
          </Button>

          {acceptedRevisions ? (
            <div className="flex items-center gap-1.5 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-400">
              <CheckCircle2 className="h-4 w-4" />
              <span>Revision Accepted</span>
            </div>
          ) : (
            <Button
              size="sm"
              variant="outline"
              onClick={handleAccept}
              className="h-8 gap-1.5 border-emerald-500/40 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/10 hover:text-emerald-500 text-xs font-medium"
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>Looks Good (Accept)</span>
            </Button>
          )}
        </div>
      </div>

      {/* Active On-Canvas Spatial Correction Indicator */}
      {spatialCorrection && (
        <div className="flex items-center justify-between gap-2 px-3 py-1.5 rounded-lg bg-sky-500/10 border border-sky-500/30 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sky-400">Target Element:</span>
            <span className="font-mono text-foreground">{spatialCorrection.target_object}</span>
            <span className="text-muted-foreground">•</span>
            <span className="text-sky-300 font-medium">Action: {spatialCorrection.action}</span>
          </div>
          <button
            type="button"
            onClick={() => useCritiqueStore.getState().setSpatialCorrection(null)}
            className="text-[11px] text-muted-foreground hover:text-foreground font-mono"
          >
            Clear
          </button>
        </div>
      )}

      {/* Semantic Failure Categories Tabs */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setActiveTab("visual")}
              className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                activeTab === "visual"
                  ? "bg-primary/15 text-primary font-semibold border border-primary/30"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              👁️ Visual Correctness
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("scientific")}
              className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                activeTab === "scientific"
                  ? "bg-primary/15 text-primary font-semibold border border-primary/30"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              🔬 Scientific & Pedagogical
            </button>
          </div>

          <span className="text-[11px] text-muted-foreground font-mono">
            Click category to command repair
          </span>
        </div>

        {/* Buttons Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
          {FAILURE_OPTIONS.filter((opt) => opt.dimension === activeTab).map(
            (opt) => {
              const Icon = opt.icon;
              const isSelected = selectedCategory === opt.id;
              return (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => handleQuickCategoryClick(opt.id)}
                  className={`group relative flex flex-col justify-between rounded-xl border p-2.5 text-left transition-all ${
                    isSelected
                      ? "border-primary bg-primary/10 shadow-xs ring-1 ring-primary/40"
                      : "border-border/70 bg-background/50 hover:border-foreground/30 hover:bg-accent/40"
                  }`}
                >
                  <div className="flex items-center justify-between w-full">
                    <div className="flex items-center gap-2">
                      <div
                        className={`rounded-md p-1 ${
                          isSelected
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted text-foreground/75 group-hover:text-primary"
                        }`}
                      >
                        <Icon className="h-3.5 w-3.5" />
                      </div>
                      <span className="text-xs font-medium text-foreground">
                        {opt.label}
                      </span>
                    </div>
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-1.5 leading-snug line-clamp-2">
                    {opt.description}
                  </p>
                </button>
              );
            },
          )}
        </div>
      </div>

      {/* Natural Language Critique & Timestamp Grabber */}
      <div className="space-y-2 rounded-xl border border-border/60 bg-accent/15 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-xs font-medium text-foreground">
            <Sparkles className="h-3.5 w-3.5 text-amber-400" />
            <span>Describe Your Issue (Human Reviewer Feedback)</span>
          </div>

          <div className="flex items-center gap-2">
            {currentTimestamp > 0 && (
              <Badge
                variant="secondary"
                className="text-[10px] font-mono gap-1 py-0.5"
              >
                <Clock className="h-2.5 w-2.5" />
                <span>At {formatTimestamp(currentTimestamp)}</span>
              </Badge>
            )}

            <div className="flex items-center gap-1">
              {(["low", "medium", "high", "critical"] as SeverityLevel[]).map(
                (sev) => (
                  <button
                    key={sev}
                    type="button"
                    onClick={() => setSeverity(sev)}
                    className={`rounded-md px-1.5 py-0.5 text-[10px] uppercase font-mono transition-colors ${
                      severity === sev
                        ? sev === "critical" || sev === "high"
                          ? "bg-rose-500 text-white font-bold"
                          : "bg-primary text-primary-foreground font-semibold"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {sev}
                  </button>
                ),
              )}
            </div>
          </div>
        </div>

        <Textarea
          placeholder="e.g. At 0:18, the trajectory expands beyond the safe frame and overlaps the sigma formula..."
          value={feedbackText}
          onChange={(e) => setFeedbackText(e.target.value)}
          rows={2}
          className="text-xs resize-none bg-background/80"
        />

        <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
          <div className="flex items-center gap-2 flex-1 max-w-xs">
            <span className="text-[11px] text-muted-foreground whitespace-nowrap">
              Target Element:
            </span>
            <Input
              type="text"
              placeholder="e.g. LorenzTrajectory, Equations"
              value={targetObject}
              onChange={(e) => setTargetObject(e.target.value)}
              className="h-7 text-xs bg-background/80"
            />
          </div>

          <Button
            size="sm"
            onClick={handleSubmit}
            disabled={
              isSubmitting || (!selectedCategory && !feedbackText.trim())
            }
            className="h-8 gap-1.5 text-xs font-semibold"
          >
            {isSubmitting ? (
              <>
                <Wand2 className="h-3.5 w-3.5 animate-spin" />
                <span>Dispatching Repair...</span>
              </>
            ) : (
              <>
                <Send className="h-3.5 w-3.5" />
                <span>Submit Critique & Repair</span>
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Status Notice */}
      {submissionMessage && (
        <div className="flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/10 p-2.5 text-xs text-foreground">
          <Sparkles className="h-4 w-4 text-primary shrink-0" />
          <span>{submissionMessage}</span>
        </div>
      )}
    </div>
  );
}
