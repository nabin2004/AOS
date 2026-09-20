"use client";

import React, { useState } from "react";
import {
  useCritiqueStore,
  type SpatialCorrection,
} from "@/stores/critique-store";
import {
  Move,
  Maximize2,
  Minimize2,
  EyeOff,
  AlertTriangle,
  Layers,
  Sparkles,
  X,
  Crosshair,
  ShieldAlert,
} from "lucide-react";
import { Badge, Button } from "@/components/ui";

interface DetectedAnchor {
  id: string;
  name: string;
  type: string;
  box: { top: string; left: string; width: string; height: string };
  warning?: string;
}

const DEFAULT_ANCHORS: DetectedAnchor[] = [
  {
    id: "anchor_trajectory",
    name: "Main Trajectory / Geometry",
    type: "VMobject",
    box: { top: "25%", left: "32%", width: "42%", height: "48%" },
    warning: "Possible expansion outside safe frame",
  },
  {
    id: "anchor_equations",
    name: "Governing Equations / MathTex",
    type: "MathTex",
    box: { top: "12%", left: "10%", width: "34%", height: "18%" },
    warning: "Spatial margin close to diagram boundary",
  },
  {
    id: "anchor_axes",
    name: "Coordinate Axes & Labels",
    type: "ThreeDAxes",
    box: { top: "68%", left: "15%", width: "30%", height: "20%" },
  },
];

interface CritiqueOverlayProps {
  videoGenerationId: string;
  className?: string;
}

export function CritiqueOverlay({
  videoGenerationId,
  className = "",
}: CritiqueOverlayProps) {
  const isCritiqueMode = useCritiqueStore(
    (s) => s.critiqueModeActive[videoGenerationId] || false,
  );
  const toggleCritiqueMode = useCritiqueStore((s) => s.toggleCritiqueMode);
  const setTargetObject = useCritiqueStore((s) => s.setTargetObject);
  const setSelectedCategory = useCritiqueStore((s) => s.setSelectedCategory);
  const setFeedbackText = useCritiqueStore((s) => s.setFeedbackText);
  const setSpatialCorrection = useCritiqueStore((s) => s.setSpatialCorrection);

  const [selectedAnchor, setSelectedAnchor] = useState<DetectedAnchor | null>(null);

  if (!isCritiqueMode) {
    return (
      <div className="absolute top-3 right-3 z-20">
        <Button
          size="sm"
          variant="secondary"
          onClick={() => toggleCritiqueMode(videoGenerationId)}
          className="h-8 gap-1.5 bg-black/60 backdrop-blur-md border border-white/20 text-white hover:bg-black/80 hover:border-white/40 text-xs shadow-md"
        >
          <Crosshair className="h-3.5 w-3.5 text-amber-400" />
          <span>Critique Mode</span>
        </Button>
      </div>
    );
  }

  const handleSelectAnchor = (anchor: DetectedAnchor) => {
    setSelectedAnchor(anchor);
    setTargetObject(anchor.name);
    setSelectedCategory("positioning");
  };

  const handleSpatialAction = (
    action: SpatialCorrection["action"],
    label: string,
  ) => {
    if (!selectedAnchor) return;

    const correction: SpatialCorrection = {
      action,
      target_object: selectedAnchor.name,
    };
    setSpatialCorrection(correction);
    setTargetObject(selectedAnchor.name);
    setSelectedCategory(action === "scale" || action === "make_larger" ? "visibility" : "positioning");
    setFeedbackText(
      `[Visual QA] ${label} for ${selectedAnchor.name}. Adjust spatial coordinates and bounding box in Manim.`,
    );
  };

  return (
    <div
      className={`absolute inset-0 pointer-events-none z-20 flex flex-col justify-between overflow-hidden ${className}`}
    >
      {/* Manim 16:9 Safe Frame Guide (85% boundary) */}
      <div className="absolute inset-[7.5%] border border-dashed border-amber-400/40 rounded-lg pointer-events-none">
        <div className="absolute top-1 left-2 flex items-center gap-1 text-[9px] font-mono uppercase tracking-wider text-amber-400/80 bg-black/60 px-1.5 py-0.5 rounded">
          <ShieldAlert className="h-2.5 w-2.5" />
          <span>16:9 Safe Frame Boundary</span>
        </div>
      </div>

      {/* Top Banner / HUD Header */}
      <div className="pointer-events-auto flex items-center justify-between p-3 bg-gradient-to-b from-black/80 via-black/40 to-transparent">
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className="gap-1 bg-amber-500/10 text-amber-400 border-amber-500/40 text-[11px] font-medium"
          >
            <Crosshair className="h-3 w-3 animate-pulse" />
            <span>Interactive Visual Review Active</span>
          </Badge>
          <span className="text-[11px] text-white/70 hidden sm:inline">
            Click any scene element to inspect & correct spatial layout
          </span>
        </div>

        <Button
          size="sm"
          variant="ghost"
          onClick={() => toggleCritiqueMode(videoGenerationId)}
          className="h-7 text-xs text-white/80 hover:text-white hover:bg-white/10 gap-1 px-2"
        >
          <X className="h-3.5 w-3.5" />
          <span>Exit Critique</span>
        </Button>
      </div>

      {/* Interactive Element Hotspots on the Video Canvas */}
      <div className="absolute inset-0 pointer-events-none">
        {DEFAULT_ANCHORS.map((anchor) => {
          const isSelected = selectedAnchor?.id === anchor.id;
          return (
            <div
              key={anchor.id}
              onClick={() => handleSelectAnchor(anchor)}
              style={{
                top: anchor.box.top,
                left: anchor.box.left,
                width: anchor.box.width,
                height: anchor.box.height,
              }}
              className={`absolute pointer-events-auto cursor-pointer rounded-lg transition-all duration-150 flex flex-col justify-between p-1.5 ${
                isSelected
                  ? "border-2 border-primary bg-primary/20 shadow-lg ring-2 ring-primary/50"
                  : "border border-sky-400/60 bg-sky-500/10 hover:border-sky-300 hover:bg-sky-500/20"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-medium font-mono text-white bg-black/70 px-1.5 py-0.5 rounded backdrop-blur-xs">
                  {anchor.name}
                </span>
                {anchor.warning && (
                  <div
                    title={anchor.warning}
                    className="flex items-center gap-1 text-[9px] text-amber-300 bg-amber-950/80 px-1.5 py-0.5 rounded border border-amber-500/40"
                  >
                    <AlertTriangle className="h-2.5 w-2.5" />
                    <span className="hidden sm:inline">Warning</span>
                  </div>
                )}
              </div>

              {isSelected && (
                <div className="text-[9px] font-mono text-primary-foreground bg-primary/90 px-1 py-0.5 rounded self-start">
                  Selected: {anchor.type}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Bottom Selected Element Control Card */}
      {selectedAnchor && (
        <div className="pointer-events-auto m-3 p-3 rounded-xl border border-white/20 bg-black/85 backdrop-blur-md shadow-2xl text-white space-y-2 max-w-lg self-center w-[92%]">
          <div className="flex items-center justify-between border-b border-white/10 pb-2">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-sky-400" />
              <div>
                <h5 className="text-xs font-semibold">{selectedAnchor.name}</h5>
                <span className="text-[10px] text-white/60 font-mono">
                  {selectedAnchor.type} • Coordinates & Scale Adjustment
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setSelectedAnchor(null)}
              className="text-white/60 hover:text-white text-xs p-1"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Quick Direct Actions */}
          <div className="flex flex-wrap items-center gap-1.5 pt-1">
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleSpatialAction("move", "Reposition / Center")}
              className="h-7 text-[11px] gap-1 bg-white/10 border-white/20 text-white hover:bg-white/20 hover:text-white"
            >
              <Move className="h-3 w-3 text-sky-400" />
              <span>Reposition</span>
            </Button>

            <Button
              size="sm"
              variant="outline"
              onClick={() => handleSpatialAction("make_larger", "Scale Up / Enlarge")}
              className="h-7 text-[11px] gap-1 bg-white/10 border-white/20 text-white hover:bg-white/20 hover:text-white"
            >
              <Maximize2 className="h-3 w-3 text-emerald-400" />
              <span>Make Larger</span>
            </Button>

            <Button
              size="sm"
              variant="outline"
              onClick={() => handleSpatialAction("scale", "Scale Down / Shrink")}
              className="h-7 text-[11px] gap-1 bg-white/10 border-white/20 text-white hover:bg-white/20 hover:text-white"
            >
              <Minimize2 className="h-3 w-3 text-amber-400" />
              <span>Make Smaller</span>
            </Button>

            <Button
              size="sm"
              variant="outline"
              onClick={() => handleSpatialAction("fix_overlap", "Fix Collision & Margins")}
              className="h-7 text-[11px] gap-1 bg-white/10 border-white/20 text-white hover:bg-white/20 hover:text-white"
            >
              <Sparkles className="h-3 w-3 text-purple-400" />
              <span>Fix Overlap</span>
            </Button>

            <Button
              size="sm"
              variant="outline"
              onClick={() => handleSpatialAction("hide", "Hide / Remove from Scene")}
              className="h-7 text-[11px] gap-1 bg-white/10 border-white/20 text-white hover:bg-white/20 hover:text-white"
            >
              <EyeOff className="h-3 w-3 text-rose-400" />
              <span>Hide</span>
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
