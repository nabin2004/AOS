"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  Sparkles,
  Clapperboard,
  Code2,
  Play,
  RotateCcw,
  CheckCircle2,
  Edit3,
  Eye,
  Sliders,
  AlertCircle,
  X,
  ExternalLink,
  ChevronRight,
  Terminal,
  Loader2,
  Wand2,
  Layers,
  Palette,
  Clock,
  Compass,
  FileText,
  Layout,
  Plus,
  ArrowRight,
  Lightbulb,
  Box,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MarkdownContent } from "./markdown-content";
import { AppVideoPlayer } from "@/components/media/video-player";
import { CritiqueDeck } from "@/components/video/critique-deck";
import { CritiqueOverlay } from "@/components/video/critique-overlay";
import { useCritiqueStore } from "@/stores";
import { useLlmProviderStore } from "@/stores/llm-provider-store";

interface PlannedMobject {
  type: string;
  name: string;
  detail: string;
}

interface PlannedScene {
  number: number;
  title: string;
  duration: string;
  purpose: string;
  mobjects: PlannedMobject[];
  actions: string[];
}

function parseScenesPlan(markdown: string) {
  const titleMatch = markdown.match(/^#\s+(.+)$/m);
  const title = titleMatch ? titleMatch[1].trim() : "Pedagogical Animation";

  const hookMatch = markdown.match(/\*\*Hook\*\*:\s*([^\n]+)/i);
  const hook = hookMatch ? hookMatch[1].trim() : "";

  const insightMatch = markdown.match(/\*\*Key Insight\*\*:\s*([^\n]+)/i);
  const keyInsight = insightMatch ? insightMatch[1].trim() : "";

  const sceneBlocks = markdown.split(/##\s+Scene\s+(\d+)[:\s]+([^\n]+)/i);
  const scenes: PlannedScene[] = [];

  for (let i = 1; i < sceneBlocks.length; i += 3) {
    const num = parseInt(sceneBlocks[i], 10) || Math.floor(i / 3) + 1;
    const sceneTitle = sceneBlocks[i + 1]?.trim() || `Scene ${num}`;
    const content = sceneBlocks[i + 2] || "";

    const durationMatch = content.match(/\*\*Duration\*\*:\s*([^\n]+)/i);
    const purposeMatch = content.match(/\*\*Purpose\*\*:\s*([^\n]+)/i);

    const visualElementsMatch = content.match(/###\s+Visual Elements([\s\S]+?)(?=###|$)/i);
    const mobjects: PlannedMobject[] = [];
    if (visualElementsMatch) {
      const lines = visualElementsMatch[1].split("\n").filter((l) => l.trim().startsWith("-") || l.trim().startsWith("*"));
      for (const line of lines) {
        const clean = line.replace(/^[-*]\s*/, "").trim();
        let type = "Mobject";
        if (/mathtex|formula|equation|\$|\\frac/i.test(clean)) type = "MathTex";
        else if (/text|title|label|header/i.test(clean)) type = "Text";
        else if (/axes|plane|coordinate|grid/i.test(clean)) type = "CoordinateAxes";
        else if (/surroundingrectangle|box|rectangle|circle/i.test(clean)) type = "Geometry";
        else if (/vgroup|group/i.test(clean)) type = "VGroup";
        else if (/arrow|vector|line/i.test(clean)) type = "Vector";

        mobjects.push({
          type,
          name: clean.split(":")[0] || clean,
          detail: clean,
        });
      }
    }

    const actionsMatch = content.match(/###\s+Content([\s\S]+?)(?=###|$)/i);
    const actions: string[] = [];
    if (actionsMatch) {
      const lines = actionsMatch[1].split("\n").filter((l) => /^\d+\.|\-|\*/.test(l.trim()));
      for (const line of lines) {
        actions.push(line.replace(/^\d+\.\s*|[-*]\s*/, "").trim());
      }
    }

    scenes.push({
      number: num,
      title: sceneTitle,
      duration: durationMatch ? durationMatch[1].trim() : "~10s",
      purpose: purposeMatch ? purposeMatch[1].trim() : "Conceptual demonstration",
      mobjects: mobjects.length > 0 ? mobjects : [
        { type: "Text", name: "Scene Title", detail: `Text("${sceneTitle}")` },
        { type: "MathTex", name: "Core Equation", detail: "MathTex(r'...')" },
      ],
      actions: actions.length > 0 ? actions : ["Introduce visual elements", "Transform equation", "Conclude scene"],
    });
  }

  const palette = [
    { name: "Primary", token: "BLUE_C", color: "#58C4DD" },
    { name: "Secondary", token: "YELLOW", color: "#FFFF00" },
    { name: "Accent", token: "TEAL", color: "#49B78A" },
    { name: "Background", token: "DARK", color: "#0F172A" },
  ];

  return { title, hook, keyInsight, scenes, palette };
}

interface ManimStudioModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialKnowledge: string;
  conversationId?: string;
}

type StudioStage = "plan" | "code" | "render" | "review";
type RenderQuality = "l" | "m" | "h" | "k";

const QUALITY_OPTIONS: { id: RenderQuality; label: string; desc: string; res: string }[] = [
  { id: "l", label: "Low Quality (-ql)", desc: "Fast preview, 15fps", res: "480p" },
  { id: "m", label: "Medium (-qm)", desc: "Standard presentation, 30fps", res: "720p" },
  { id: "h", label: "High Quality (-qh)", desc: "Full HD presentation, 60fps", res: "1080p" },
  { id: "k", label: "4K Ultra (-qk)", desc: "Cinematic quality, 60fps", res: "2160p" },
];

export function ManimStudioModal({
  isOpen,
  onClose,
  initialKnowledge,
  conversationId,
}: ManimStudioModalProps) {
  const [currentStage, setCurrentStage] = useState<StudioStage>("plan");
  
  // Knowledge state
  const [knowledgeText, setKnowledgeText] = useState(initialKnowledge);

  // Stage 1: Plan
  const [planMarkdown, setPlanMarkdown] = useState("");
  const [isGeneratingPlan, setIsGeneratingPlan] = useState(false);
  const [isEditingPlan, setIsEditingPlan] = useState(false);

  const [planViewMode, setPlanViewMode] = useState<"visual" | "markdown">("visual");

  const parsedPlan = useMemo(() => {
    return parseScenesPlan(planMarkdown);
  }, [planMarkdown]);

  const handleAddMobjectSnippet = (type: "mathtex" | "text" | "rectangle" | "axes") => {
    let snippet = "";
    if (type === "mathtex") {
      snippet = "Equation: `MathTex(r\"\\frac{df}{dx} = \\lim_{h \\to 0} \\frac{f(x+h) - f(x)}{h}\", font_size=32).set_color(YELLOW)`";
    } else if (type === "text") {
      snippet = "Annotation: `Text(\"Visual Intuition & Rate of Change\", font_size=24, color=BLUE_C)`";
    } else if (type === "rectangle") {
      snippet = "Highlight: `SurroundingRectangle(formula, color=YELLOW, buff=0.15)`";
    } else if (type === "axes") {
      snippet = "Coordinate Grid: `Axes(x_range=[-4, 4, 1], y_range=[-3, 3, 1], x_length=6, y_length=4)`";
    }
    setPlanMarkdown((prev) => {
      if (prev.includes("### Visual Elements")) {
        return prev.replace("### Visual Elements", `### Visual Elements\n- ${snippet}`);
      }
      return prev + `\n\n### Visual Elements\n- ${snippet}`;
    });
  };

  // Stage 2: Code
  const [sceneCode, setSceneCode] = useState("");
  const [sceneName, setSceneName] = useState("TaylorFormulaScene");
  const [isSynthesizingCode, setIsSynthesizingCode] = useState(false);
  const [isEditingCode, setIsEditingCode] = useState(false);

  // Stage 3: Render
  const [quality, setQuality] = useState<RenderQuality>("l");
  const [isRendering, setIsRendering] = useState(false);
  const [renderProgressMsg, setRenderProgressMsg] = useState("");
  const [renderError, setRenderError] = useState<string | null>(null);

  // Stage 4: Video
  const [videoGenerationId, setVideoGenerationId] = useState<string | null>(null);
  const [videoStreamUrl, setVideoStreamUrl] = useState<string | null>(null);

  const { baseUrl, apiKey, modelId } = useLlmProviderStore();
  const critiqueModeActive = useCritiqueStore((s) => s.critiqueModeActive);

  // Track the last knowledge we generated a plan for so we can detect a new query
  const lastKnowledgeRef = useRef<string>("");

  // Reset or initialize when opened, or when initialKnowledge changes
  useEffect(() => {
    if (!isOpen) return;

    const isNewKnowledge = initialKnowledge !== lastKnowledgeRef.current;

    if (isNewKnowledge) {
      // Reset the full pipeline state for the new query
      lastKnowledgeRef.current = initialKnowledge;
      setKnowledgeText(initialKnowledge);
      setPlanMarkdown("");
      setSceneCode("");
      setSceneName("GeneratedScene");
      setCurrentStage("plan");
      setRenderError(null);
      setVideoGenerationId(null);
      setVideoStreamUrl(null);
      setIsEditingPlan(false);
      setIsEditingCode(false);
      handleGeneratePlan(initialKnowledge);
    }
  }, [isOpen, initialKnowledge]);

  const handleGeneratePlan = async (sourceText: string) => {
    setIsGeneratingPlan(true);
    setRenderError(null);
    try {
      const resp = await fetch("/api/videos/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: sourceText,
          model_name: modelId,
          base_url: baseUrl,
          api_key: apiKey,
        }),
      });
      if (resp.ok) {
        const data = await resp.json();
        setPlanMarkdown(data.plan || "");
      } else {
        const err = await resp.text();
        setRenderError(`Plan generation error: ${err}`);
      }
    } catch (e: any) {
      setRenderError(`Network error while generating plan: ${e.message}`);
    } finally {
      setIsGeneratingPlan(false);
    }
  };

  const handleSynthesizeCode = async () => {
    setIsSynthesizingCode(true);
    setRenderError(null);
    try {
      const resp = await fetch("/api/videos/code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plan: planMarkdown,
          knowledge_text: knowledgeText,
          model_name: modelId,
          base_url: baseUrl,
          api_key: apiKey,
        }),
      });
      if (resp.ok) {
        const data = await resp.json();
        setSceneCode(data.code || "");
        if (data.scene_name) setSceneName(data.scene_name);
        setCurrentStage("code");
      } else {
        const err = await resp.text();
        setRenderError(`Code synthesis error: ${err}`);
      }
    } catch (e: any) {
      setRenderError(`Network error while generating code: ${e.message}`);
    } finally {
      setIsSynthesizingCode(false);
    }
  };

  const handleRenderVideo = async () => {
    setIsRendering(true);
    setRenderError(null);
    setRenderProgressMsg("Initiating Docker Manim compiler container...");
    try {
      const resp = await fetch("/api/videos/render-custom", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: sceneCode,
          scene_name: sceneName,
          quality: quality,
          conversation_id: conversationId,
          prompt: `Manim Studio: ${sceneName}`,
        }),
      });
      if (resp.ok) {
        const data = await resp.json();
        setVideoGenerationId(data.video_generation_id);
        setVideoStreamUrl(data.stream_url);
        setCurrentStage("review");
      } else {
        const err = await resp.json().catch(() => ({ detail: "Unknown error" }));
        setRenderError(err.detail || "Rendering failed");
      }
    } catch (e: any) {
      setRenderError(`Failed to compile & render: ${e.message}`);
    } finally {
      setIsRendering(false);
    }
  };

  const handleRepairFromCritique = async (category: string, feedback: string) => {
    // Return to code stage with repair instructions
    setIsSynthesizingCode(true);
    setCurrentStage("code");
    setRenderError(null);
    try {
      const resp = await fetch("/api/videos/code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plan: `${planMarkdown}\n\n### REPAIR DIRECTIVE (${category.toUpperCase()}):\n${feedback}`,
          knowledge_text: knowledgeText,
          scene_name: sceneName,
          model_name: modelId,
          base_url: baseUrl,
          api_key: apiKey,
        }),
      });
      if (resp.ok) {
        const data = await resp.json();
        setSceneCode(data.code || "");
      }
    } catch (e: any) {
      setRenderError(`Repair code generation failed: ${e.message}`);
    } finally {
      setIsSynthesizingCode(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-md p-2 sm:p-4 md:p-6 animate-in fade-in duration-200">
      <div className="relative flex flex-col w-full max-w-5xl h-[92vh] rounded-2xl border border-border/80 bg-card shadow-2xl overflow-hidden">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-border/60 px-5 py-3.5 bg-muted/30">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Clapperboard className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-semibold text-sm sm:text-base text-foreground">
                  Interactive Manim Animation Studio
                </h2>
                <Badge variant="outline" className="text-[10px] uppercase font-mono tracking-wider border-primary/30 text-primary bg-primary/5">
                  Human-In-The-Loop
                </Badge>
              </div>
              <p className="text-[11px] text-muted-foreground">
                Progressive pipeline: Plan with Composer → Synthesize Code → Compile & Render → Inspect & Repair
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Stepper Navigation */}
        <div className="grid grid-cols-4 border-b border-border/40 bg-muted/10 text-xs font-medium">
          <button
            type="button"
            onClick={() => setCurrentStage("plan")}
            className={`flex items-center justify-center gap-2 py-2.5 px-3 border-r border-border/30 transition-colors ${
              currentStage === "plan"
                ? "bg-background text-primary font-semibold border-b-2 border-b-primary shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/30"
            }`}
          >
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-primary/20 text-[10px] font-mono">1</span>
            <span>Composer Plan</span>
          </button>

          <button
            type="button"
            onClick={() => setCurrentStage("code")}
            disabled={!sceneCode && isSynthesizingCode}
            className={`flex items-center justify-center gap-2 py-2.5 px-3 border-r border-border/30 transition-colors ${
              currentStage === "code"
                ? "bg-background text-primary font-semibold border-b-2 border-b-primary shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/30 disabled:opacity-40"
            }`}
          >
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-primary/20 text-[10px] font-mono">2</span>
            <span>Coder Agent</span>
          </button>

          <button
            type="button"
            onClick={() => setCurrentStage("render")}
            disabled={!sceneCode}
            className={`flex items-center justify-center gap-2 py-2.5 px-3 border-r border-border/30 transition-colors ${
              currentStage === "render"
                ? "bg-background text-primary font-semibold border-b-2 border-b-primary shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/30 disabled:opacity-40"
            }`}
          >
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-primary/20 text-[10px] font-mono">3</span>
            <span>Compile & Render</span>
          </button>

          <button
            type="button"
            onClick={() => setCurrentStage("review")}
            disabled={!videoStreamUrl}
            className={`flex items-center justify-center gap-2 py-2.5 px-3 transition-colors ${
              currentStage === "review"
                ? "bg-background text-primary font-semibold border-b-2 border-b-primary shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/30 disabled:opacity-40"
            }`}
          >
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-primary/20 text-[10px] font-mono">4</span>
            <span>Review & Repair</span>
          </button>
        </div>

        {/* Global Error Banner if any */}
        {renderError && (
          <div className="flex items-center gap-2 bg-red-500/10 border-b border-red-500/20 px-4 py-2 text-xs text-red-400">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span className="flex-1 font-mono">{renderError}</span>
            <button
              type="button"
              onClick={() => setRenderError(null)}
              className="text-red-400 hover:text-red-300"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        )}

        {/* Main Stage Content */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          
          {/* STAGE 1: PLAN (Composer) */}
          {currentStage === "plan" && (
            <div className="space-y-4 max-w-4xl mx-auto">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border/40">
                <div>
                  <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-primary" />
                    Manim Composer Visual Plan
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Plan pedagogical scenes, mobjects (LaTeX formulas, shapes, text), and visual pacing.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex rounded-lg border border-border/60 bg-muted/30 p-0.5">
                    <button
                      type="button"
                      onClick={() => { setPlanViewMode("visual"); setIsEditingPlan(false); }}
                      className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs transition-colors ${
                        planViewMode === "visual" && !isEditingPlan
                          ? "bg-background text-primary font-medium shadow-xs"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      <Layout className="h-3.5 w-3.5" />
                      Visual Mobjects
                    </button>
                    <button
                      type="button"
                      onClick={() => setPlanViewMode("markdown")}
                      className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs transition-colors ${
                        planViewMode === "markdown" || isEditingPlan
                          ? "bg-background text-primary font-medium shadow-xs"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      <FileText className="h-3.5 w-3.5" />
                      scenes.md
                    </button>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setIsEditingPlan(!isEditingPlan);
                      if (!isEditingPlan) setPlanViewMode("markdown");
                    }}
                    className="h-8 text-xs gap-1.5"
                  >
                    {isEditingPlan ? <Eye className="h-3.5 w-3.5" /> : <Edit3 className="h-3.5 w-3.5" />}
                    {isEditingPlan ? "View Preview" : "Edit Markdown"}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleGeneratePlan(knowledgeText)}
                    disabled={isGeneratingPlan}
                    className="h-8 text-xs gap-1 text-muted-foreground hover:text-foreground"
                    title="Regenerate Plan with Composer"
                  >
                    <RotateCcw className={`h-3.5 w-3.5 ${isGeneratingPlan ? "animate-spin" : ""}`} />
                    Regenerate
                  </Button>
                </div>
              </div>

              {/* Quick Add Mobject Toolbar */}
              <div className="flex flex-wrap items-center gap-2 p-2.5 rounded-xl border border-primary/20 bg-primary/5 text-xs">
                <span className="text-[11px] font-medium text-primary flex items-center gap-1 shrink-0">
                  <Plus className="h-3.5 w-3.5" />
                  Add to Scene:
                </span>
                <button
                  type="button"
                  onClick={() => handleAddMobjectSnippet("mathtex")}
                  className="px-2.5 py-1 rounded-lg bg-background hover:bg-muted text-foreground border border-border/60 text-[11px] font-mono transition-colors"
                >
                  + MathTex Formula
                </button>
                <button
                  type="button"
                  onClick={() => handleAddMobjectSnippet("text")}
                  className="px-2.5 py-1 rounded-lg bg-background hover:bg-muted text-foreground border border-border/60 text-[11px] font-mono transition-colors"
                >
                  + Text Label
                </button>
                <button
                  type="button"
                  onClick={() => handleAddMobjectSnippet("rectangle")}
                  className="px-2.5 py-1 rounded-lg bg-background hover:bg-muted text-foreground border border-border/60 text-[11px] font-mono transition-colors"
                >
                  + Highlight Box
                </button>
                <button
                  type="button"
                  onClick={() => handleAddMobjectSnippet("axes")}
                  className="px-2.5 py-1 rounded-lg bg-background hover:bg-muted text-foreground border border-border/60 text-[11px] font-mono transition-colors"
                >
                  + Coordinate Axes
                </button>
              </div>

              {isGeneratingPlan ? (
                <div className="flex flex-col items-center justify-center py-20 gap-3 text-muted-foreground">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  <p className="text-sm font-medium">Invoking Manim Composer Agent…</p>
                  <p className="text-xs text-muted-foreground/80">
                    Drafting scenes.md according to pedagogical animation best practices.
                  </p>
                </div>
              ) : isEditingPlan ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Markdown Plan Editor:</span>
                    <span>Supports GitHub Markdown and LaTeX math notation</span>
                  </div>
                  <textarea
                    value={planMarkdown}
                    onChange={(e) => setPlanMarkdown(e.target.value)}
                    rows={16}
                    className="w-full rounded-xl border border-input bg-muted/20 p-4 font-mono text-xs leading-relaxed focus:outline-none focus:ring-1 focus:ring-primary shadow-inner"
                    placeholder="Enter or customize your visual scenes plan..."
                  />
                </div>
              ) : planViewMode === "visual" ? (
                <div className="space-y-4">
                  {/* Overview Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {parsedPlan.hook ? (
                      <div className="rounded-xl border border-border/60 bg-muted/20 p-3.5 space-y-1">
                        <div className="text-[11px] font-semibold text-primary flex items-center gap-1.5 uppercase tracking-wider">
                          <Compass className="h-3.5 w-3.5" />
                          Narrative Hook
                        </div>
                        <p className="text-xs text-foreground/90 leading-relaxed italic">
                          &ldquo;{parsedPlan.hook}&rdquo;
                        </p>
                      </div>
                    ) : null}
                    {parsedPlan.keyInsight ? (
                      <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-3.5 space-y-1">
                        <div className="text-[11px] font-semibold text-amber-500 flex items-center gap-1.5 uppercase tracking-wider">
                          <Lightbulb className="h-3.5 w-3.5" />
                          The &ldquo;Aha Moment&rdquo;
                        </div>
                        <p className="text-xs text-foreground/90 leading-relaxed">
                          {parsedPlan.keyInsight}
                        </p>
                      </div>
                    ) : null}
                    <div className="rounded-xl border border-border/60 bg-muted/20 p-3.5 space-y-1.5">
                      <div className="text-[11px] font-semibold text-muted-foreground flex items-center gap-1.5 uppercase tracking-wider">
                        <Palette className="h-3.5 w-3.5" />
                        Color Palette
                      </div>
                      <div className="flex flex-wrap items-center gap-2 pt-0.5">
                        {parsedPlan.palette.map((p) => (
                          <div key={p.name} className="flex items-center gap-1.5 text-[10px] font-mono bg-background/80 px-2 py-1 rounded-md border border-border/50">
                            <span className="h-2.5 w-2.5 rounded-full border border-black/20" style={{ backgroundColor: p.color }} />
                            <span>{p.token}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Planned Scene Cards */}
                  <div className="space-y-3 pt-1">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                      <Layers className="h-3.5 w-3.5 text-primary" />
                      Scene-by-Scene Animation Architecture
                    </h4>

                    {parsedPlan.scenes.map((sc) => (
                      <div key={sc.number} className="rounded-xl border border-border/70 bg-card p-4 space-y-3 shadow-xs hover:border-primary/40 transition-colors">
                        <div className="flex items-start justify-between gap-2">
                          <div className="space-y-0.5">
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="text-[10px] font-mono border-primary/30 text-primary">
                                Scene {sc.number}
                              </Badge>
                              <h5 className="font-semibold text-sm text-foreground">{sc.title}</h5>
                            </div>
                            <p className="text-xs text-muted-foreground">{sc.purpose}</p>
                          </div>
                          <Badge variant="secondary" className="text-[10px] font-mono flex items-center gap-1 shrink-0">
                            <Clock className="h-3 w-3" />
                            {sc.duration}
                          </Badge>
                        </div>

                        {/* Planned Mobjects */}
                        <div className="space-y-1.5 pt-1">
                          <div className="text-[11px] font-medium text-foreground/80 flex items-center gap-1">
                            <Box className="h-3.5 w-3.5 text-primary" />
                            Planned Mobjects & Visual Entities:
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            {sc.mobjects.map((mob, idx) => (
                              <div
                                key={idx}
                                className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs border font-mono ${
                                  mob.type === "MathTex"
                                    ? "bg-purple-500/10 border-purple-500/30 text-purple-700 dark:text-purple-300"
                                    : mob.type === "Text"
                                    ? "bg-blue-500/10 border-blue-500/30 text-blue-700 dark:text-blue-300"
                                    : mob.type === "Geometry"
                                    ? "bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-300"
                                    : mob.type === "CoordinateAxes"
                                    ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
                                    : "bg-muted border-border/70 text-foreground"
                                }`}
                              >
                                <span className="text-[10px] uppercase font-bold opacity-75">{mob.type}:</span>
                                <span className="text-[11px] truncate max-w-xs">{mob.detail}</span>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Choreography Sequence */}
                        {sc.actions.length > 0 && (
                          <div className="space-y-1.5 pt-1 border-t border-border/40">
                            <div className="text-[11px] font-medium text-foreground/80">Animation Choreography:</div>
                            <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                              {sc.actions.map((act, idx) => (
                                <React.Fragment key={idx}>
                                  <span className="bg-muted/40 px-2 py-0.5 rounded text-[11px] font-mono text-foreground/90">
                                    {act}
                                  </span>
                                  {idx < sc.actions.length - 1 && (
                                    <ArrowRight className="h-3 w-3 text-muted-foreground/60 shrink-0" />
                                  )}
                                </React.Fragment>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="rounded-xl border border-border/60 bg-muted/10 p-5 shadow-sm">
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <MarkdownContent content={planMarkdown || "No plan generated yet."} />
                  </div>
                </div>
              )}

              {/* Action Bar */}
              <div className="flex items-center justify-between pt-4 border-t border-border/40">
                <div className="text-xs text-muted-foreground">
                  Review the visual plan and mobjects. You can tweak elements or synthesize the Python code.
                </div>
                <Button
                  onClick={handleSynthesizeCode}
                  disabled={isGeneratingPlan || !planMarkdown || isSynthesizingCode}
                  className="gap-2 bg-primary text-primary-foreground hover:bg-primary/90 shadow-md font-medium text-xs sm:text-sm px-5"
                >
                  {isSynthesizingCode ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Synthesizing Manim Code…
                    </>
                  ) : (
                    <>
                      <Code2 className="h-4 w-4" />
                      Synthesize Manim Code with Coder Agent
                      <ChevronRight className="h-4 w-4" />
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}

          {/* STAGE 2: CODE (Coder Agent) */}
          {currentStage === "code" && (
            <div className="space-y-4 max-w-4xl mx-auto">
              <div className="flex items-center justify-between pb-2 border-b border-border/40">
                <div>
                  <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
                    <Code2 className="h-4 w-4 text-primary" />
                    Synthesized Manim Community Code
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Generated using <span className="font-mono text-primary">manimce-best-practices</span> (VGroup, MathTex, layout bounds, safe positioning).
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setIsEditingCode(!isEditingCode)}
                    className="h-8 text-xs gap-1.5"
                  >
                    {isEditingCode ? <Eye className="h-3.5 w-3.5" /> : <Edit3 className="h-3.5 w-3.5" />}
                    {isEditingCode ? "Lock View" : "Edit Code"}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleSynthesizeCode}
                    disabled={isSynthesizingCode}
                    className="h-8 text-xs gap-1 text-muted-foreground hover:text-foreground"
                    title="Regenerate Manim Code"
                  >
                    <RotateCcw className={`h-3.5 w-3.5 ${isSynthesizingCode ? "animate-spin" : ""}`} />
                    Regenerate
                  </Button>
                </div>
              </div>

              {isSynthesizingCode ? (
                <div className="flex flex-col items-center justify-center py-20 gap-3 text-muted-foreground">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  <p className="text-sm font-medium">Coder Agent is generating Manim scene…</p>
                  <p className="text-xs text-muted-foreground/80">
                    Structuring construct() methods, MathTex LaTeX alignments, and animations.
                  </p>
                </div>
              ) : isEditingCode ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Python Code Editor:</span>
                    <span className="font-mono text-[10px]">Scene Class: {sceneName}</span>
                  </div>
                  <textarea
                    value={sceneCode}
                    onChange={(e) => setSceneCode(e.target.value)}
                    rows={18}
                    className="w-full rounded-xl border border-input bg-zinc-950 p-4 font-mono text-xs leading-relaxed text-zinc-200 focus:outline-none focus:ring-1 focus:ring-primary shadow-inner"
                    placeholder="from manim import * ..."
                  />
                </div>
              ) : (
                <div className="rounded-xl border border-zinc-800 bg-zinc-950 overflow-hidden shadow-lg">
                  <div className="flex items-center justify-between bg-zinc-900/80 px-4 py-2 border-b border-zinc-800 text-[11px] text-zinc-400 font-mono">
                    <span className="flex items-center gap-1.5">
                      <Terminal className="h-3 w-3 text-emerald-400" />
                      scene.py — {sceneName}
                    </span>
                    <span>Manim Community Edition</span>
                  </div>
                  <pre className="p-4 text-xs font-mono text-zinc-200 overflow-x-auto leading-relaxed max-h-[480px]">
                    <code>{sceneCode || "# No code generated yet."}</code>
                  </pre>
                </div>
              )}

              {/* Action Bar */}
              <div className="flex items-center justify-between pt-4 border-t border-border/40">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setCurrentStage("plan")}
                  className="text-xs text-muted-foreground hover:text-foreground"
                >
                  ← Back to Plan
                </Button>
                <Button
                  onClick={() => setCurrentStage("render")}
                  disabled={!sceneCode || isSynthesizingCode}
                  className="gap-2 bg-primary text-primary-foreground hover:bg-primary/90 shadow-md font-medium text-xs sm:text-sm px-5"
                >
                  Proceed to Quality & Render Options
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          {/* STAGE 3: COMPILE & RENDER */}
          {currentStage === "render" && (
            <div className="space-y-6 max-w-3xl mx-auto py-2">
              <div className="text-center space-y-1">
                <h3 className="text-lg font-semibold text-foreground flex items-center justify-center gap-2">
                  <Sliders className="h-5 w-5 text-primary" />
                  Compile & Render Video
                </h3>
                <p className="text-xs text-muted-foreground">
                  Select your target video quality and dispatch execution to the Docker Manim rendering engine.
                </p>
              </div>

              {/* Quality Selection Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                {QUALITY_OPTIONS.map((opt) => (
                  <div
                    key={opt.id}
                    onClick={() => setQuality(opt.id)}
                    className={`cursor-pointer rounded-xl border p-4 transition-all ${
                      quality === opt.id
                        ? "border-primary bg-primary/5 ring-1 ring-primary shadow-sm"
                        : "border-border/60 bg-card hover:border-border hover:bg-muted/20"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-sm text-foreground">{opt.label}</span>
                      <Badge variant={quality === opt.id ? "default" : "outline"} className="text-[10px] font-mono">
                        {opt.res}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{opt.desc}</p>
                  </div>
                ))}
              </div>

              {/* Compiler Error Box with One-Click Code Fix */}
              {renderError && !isRendering && (
                <div className="rounded-2xl border border-red-500/30 bg-red-500/5 p-4 space-y-3 text-left shadow-sm">
                  <div className="flex items-start gap-2.5 text-red-500 font-semibold text-xs">
                    <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                    <div>
                      <div>Manim Compilation / Render Error</div>
                      <p className="text-[11px] text-muted-foreground font-normal mt-0.5">
                        The Manim compiler reported an issue. Inspect the error log below and jump to Coder Agent to fix it.
                      </p>
                    </div>
                  </div>
                  <pre className="p-3 rounded-lg bg-black/60 border border-red-500/20 text-red-300 font-mono text-[11px] overflow-x-auto max-h-44 whitespace-pre-wrap leading-relaxed">
                    {renderError}
                  </pre>
                  <div className="flex items-center gap-2 pt-1">
                    <Button
                      size="sm"
                      onClick={() => {
                        setIsEditingCode(true);
                        setCurrentStage("code");
                      }}
                      className="h-8 text-xs bg-red-600 hover:bg-red-700 text-white gap-1.5 font-medium shadow-sm"
                    >
                      <Edit3 className="h-3.5 w-3.5" />
                      Fix Code in Coder Agent
                    </Button>
                  </div>
                </div>
              )}

              {/* Rendering Status / Trigger Box */}
              <div className="rounded-2xl border border-border/80 bg-muted/20 p-6 text-center space-y-4 shadow-sm">
                {isRendering ? (
                  <div className="space-y-3 py-4">
                    <Loader2 className="h-10 w-10 animate-spin text-primary mx-auto" />
                    <div className="space-y-1">
                      <p className="text-sm font-semibold text-foreground">
                        Compiling and Rendering Scene ({quality.toUpperCase()})…
                      </p>
                      <p className="text-xs text-muted-foreground font-mono">
                        {renderProgressMsg || "Processing LaTeX equations and rendering frames via Manim engine…"}
                      </p>
                    </div>
                    <div className="w-full max-w-xs mx-auto bg-muted h-1.5 rounded-full overflow-hidden">
                      <div className="bg-primary h-full w-2/3 animate-pulse rounded-full" />
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary mx-auto">
                      <Play className="h-6 w-6 ml-0.5" />
                    </div>
                    <div>
                      <h4 className="font-medium text-sm text-foreground">Ready to Render</h4>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Scene <code className="font-mono text-primary font-semibold">{sceneName}</code> will be rendered at {QUALITY_OPTIONS.find(q => q.id === quality)?.res} resolution.
                      </p>
                    </div>
                    <Button
                      size="lg"
                      onClick={handleRenderVideo}
                      className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-lg px-8 gap-2 font-semibold"
                    >
                      <Play className="h-4 w-4" />
                      Start Manim Render
                    </Button>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between pt-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setCurrentStage("code")}
                  disabled={isRendering}
                  className="text-xs text-muted-foreground hover:text-foreground"
                >
                  ← Back to Code
                </Button>
                {videoStreamUrl && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentStage("review")}
                    className="text-xs gap-1.5 text-primary"
                  >
                    View Last Rendered Video →
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* STAGE 4: REVIEW & REPAIR (Video.js Player & Critique Deck) */}
          {currentStage === "review" && (
            <div className="space-y-6 max-w-4xl mx-auto">
              <div className="flex items-center justify-between pb-2 border-b border-border/40">
                <div>
                  <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
                    <Clapperboard className="h-4 w-4 text-primary" />
                    Inspect & Critique Mode
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Video rendered successfully. Verify layout, animations, and typography.
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentStage("code")}
                  className="h-8 text-xs gap-1.5"
                >
                  <Code2 className="h-3.5 w-3.5" />
                  View/Edit Code
                </Button>
              </div>

              {/* Video Player Card */}
              {videoStreamUrl ? (
                <div className="relative rounded-2xl border border-border/80 bg-black overflow-hidden shadow-2xl">
                  <div className="relative aspect-video w-full">
                    <AppVideoPlayer
                      src={videoStreamUrl}
                      poster={undefined}
                      controls
                      autoPlay={false}
                      className="h-full w-full"
                    />
                    {critiqueModeActive && videoGenerationId && (
                      <CritiqueOverlay videoGenerationId={videoGenerationId} />
                    )}
                  </div>
                </div>
              ) : (
                <div className="p-10 text-center text-muted-foreground bg-muted/10 rounded-xl border border-dashed">
                  No video rendered yet.
                </div>
              )}

              {/* Repair Deck: "Does video need repair?" */}
              {videoGenerationId && (
                <div className="pt-2">
                  <CritiqueDeck
                    videoGenerationId={videoGenerationId}
                    code={sceneCode}
                    onRepairRequested={handleRepairFromCritique}
                  />
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
