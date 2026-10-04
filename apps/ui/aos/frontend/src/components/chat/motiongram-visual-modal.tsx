"use client";

import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import {
  Sparkles,
  Clapperboard,
  Code2,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  X,
  Volume2,
  FileCode,
  Sliders,
  Copy,
  Check,
  Download,
  BookOpen,
  ArrowRight,
  Layers,
  Wand2,
  RefreshCw,
  Bookmark,
  Activity,
  Mic,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AppVideoPlayer } from "@/components/media/video-player";
import { useAuthStore } from "@/stores";
import { useLlmProviderStore } from "@/stores/llm-provider-store";
import {
  useMotionGramStore,
  type MotionGramVoiceBackend,
  type MotionGramQuality,
} from "@/stores/motiongram-store";
import { toast } from "sonner";

const PRESET_TOPICS = [
  {
    title: "Transformer Self-Attention",
    prompt: "Show how input vector X projects into Query (Q), Key (K), and Value (V) matrices in self-attention.",
    voice: "en-US-ChristopherNeural",
  },
  {
    title: "Fourier Transform",
    prompt: "Deconstruct a square wave into its harmonic sine components with rotating epicycles.",
    voice: "en-US-JennyNeural",
  },
  {
    title: "Gradient Descent",
    prompt: "Visualize gradient descent finding the minimum on a 2D loss surface with step arrows.",
    voice: "en-US-ChristopherNeural",
  },
  {
    title: "Eigenvalues & Transformations",
    prompt: "Show a 2D coordinate grid stretching along eigenvectors during a 2x2 matrix transformation.",
    voice: "alba",
  },
  {
    title: "Harmonic Oscillator",
    prompt: "Demonstrate a mass on a spring oscillating alongside its sinusoidal position-time graph.",
    voice: "en-US-JennyNeural",
  },
];

type ActiveTab = "video" | "narration" | "yaml" | "code" | "diagnostics";

interface MotionGramVisualModalProps {
  conversationId?: string;
}

export function MotionGramVisualModal({ conversationId }: MotionGramVisualModalProps) {
  const isOpen = useMotionGramStore((s) => s.isOpen);
  const closeVisual = useMotionGramStore((s) => s.closeVisual);
  const prompt = useMotionGramStore((s) => s.prompt);
  const setPrompt = useMotionGramStore((s) => s.setPrompt);
  const voiceBackend = useMotionGramStore((s) => s.voiceBackend);
  const setVoiceBackend = useMotionGramStore((s) => s.setVoiceBackend);
  const voiceName = useMotionGramStore((s) => s.voiceName);
  const setVoiceName = useMotionGramStore((s) => s.setVoiceName);
  const quality = useMotionGramStore((s) => s.quality);
  const setQuality = useMotionGramStore((s) => s.setQuality);
  const stage = useMotionGramStore((s) => s.stage);
  const setStage = useMotionGramStore((s) => s.setStage);
  const yamlSpec = useMotionGramStore((s) => s.yamlSpec);
  const setYamlSpec = useMotionGramStore((s) => s.setYamlSpec);
  const compiledCode = useMotionGramStore((s) => s.compiledCode);
  const setCompiledCode = useMotionGramStore((s) => s.setCompiledCode);
  const videoResult = useMotionGramStore((s) => s.videoResult);
  const setVideoResult = useMotionGramStore((s) => s.setVideoResult);
  const diagnostics = useMotionGramStore((s) => s.diagnostics);
  const setDiagnostics = useMotionGramStore((s) => s.setDiagnostics);
  const repairAttempts = useMotionGramStore((s) => s.repairAttempts);
  const setRepairAttempts = useMotionGramStore((s) => s.setRepairAttempts);
  const errorMessage = useMotionGramStore((s) => s.errorMessage);
  const setErrorMessage = useMotionGramStore((s) => s.setErrorMessage);

  const modelId = useLlmProviderStore((s) => s.modelId);
  const baseUrl = useLlmProviderStore((s) => s.baseUrl);
  const apiKey = useLlmProviderStore((s) => s.apiKey);

  const [activeTab, setActiveTab] = useState<ActiveTab>("video");
  const [copiedType, setCopiedType] = useState<"yaml" | "code" | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isCompiling, setIsCompiling] = useState(false);

  const fetchWithAuth = useCallback(async (url: string, init: RequestInit) => {
    const doFetch = (token?: string | null) =>
      fetch(url, {
        ...init,
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...init.headers,
        },
      });

    const currentToken = useAuthStore.getState().accessToken;
    let res = await doFetch(currentToken);

    if (res.status === 401) {
      try {
        const refreshRes = await fetch("/api/auth/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });
        if (refreshRes.ok) {
          const { access_token } = await refreshRes.json();
          useAuthStore.getState().setAccessToken(access_token);
          res = await doFetch(access_token);
        }
      } catch {
        // Fall back to original response
      }
    }
    return res;
  }, []);

  // Parse bookmarks and narration blocks from YAML
  const narrationBlocks = useMemo(() => {
    if (!yamlSpec) return [];
    const blocks: { text: string; bookmarks: string[] }[] = [];
    const lines = yamlSpec.split("\n");
    let currentText = "";

    for (const line of lines) {
      const match = line.match(/^\s*(?:-\s+)?text:\s*["']?([\s\S]+?)["']?\s*$/);
      if (match && match[1]) {
        currentText = match[1];
        const bookmarkMatches = [...currentText.matchAll(/<bookmark\s+mark=['"](.*?)['"]\s*\/>/g)]
          .map((m) => m[1])
          .filter((bm): bm is string => typeof bm === "string");
        blocks.push({
          text: currentText,
          bookmarks: bookmarkMatches,
        });
      }
    }
    return blocks;
  }, [yamlSpec]);

  // Handle Generate & Render
  const handleGenerateAndRender = async () => {
    if (!prompt.trim()) {
      toast.error("Please enter a visual teaching topic or prompt.");
      return;
    }

    setErrorMessage(null);
    setStage("storyboard");
    toast.info("Generating MotionGram storyboard with self-healing reflection…");

    try {
      // Step 1: Generate & heal specification
      const genResp = await fetchWithAuth("/api/motiongram/generate", {
        method: "POST",
        body: JSON.stringify({
          prompt: prompt.trim(),
          voice_backend: voiceBackend,
          voice_name: voiceName,
          model_name: modelId || undefined,
          base_url: baseUrl || undefined,
          api_key: apiKey || undefined,
          max_attempts: 3,
        }),
      });

      if (!genResp.ok) {
        const errData = await genResp.json().catch(() => ({}));
        const msg = errData?.detail?.error || "MotionGram specification generation failed.";
        setErrorMessage(msg);
        setDiagnostics(errData?.detail?.diagnostics || []);
        setStage("error");
        toast.error(msg);
        return;
      }

      const genData = await genResp.json();
      setYamlSpec(genData.spec_yaml);
      setCompiledCode(genData.compiled_code || "");
      setRepairAttempts(genData.repair_attempts || 1);
      setDiagnostics(genData.diagnostics || []);

      // Step 2: Render video
      setStage("rendering");
      toast.info("Transpiling to ManimCE and rendering video…");

      const renderResp = await fetchWithAuth("/api/motiongram/render", {
        method: "POST",
        body: JSON.stringify({
          yaml_text: genData.spec_yaml,
          quality,
          conversation_id: conversationId,
          prompt: prompt.trim(),
        }),
      });

      if (!renderResp.ok) {
        const errData = await renderResp.json().catch(() => ({}));
        const msg = errData?.detail || "ManimCE render failed.";
        setErrorMessage(typeof msg === "string" ? msg : JSON.stringify(msg));
        setStage("error");
        toast.error("Render execution failed.");
        return;
      }

      const renderData = await renderResp.json();
      setVideoResult({
        video_id: renderData.video_id,
        playback_url: renderData.playback_url || `/api/videos/${renderData.video_id}/stream`,
        scene_name: renderData.scene_name,
        status: renderData.status || "completed",
      });
      setStage("completed");
      setActiveTab("video");
      toast.success("Animation rendered successfully!");
    } catch (err: any) {
      setErrorMessage(err?.message || "Unexpected failure occurred.");
      setStage("error");
      toast.error("Failed to generate animation.");
    }
  };

  // Live validate YAML
  const handleValidateYaml = async () => {
    if (!yamlSpec.trim()) return;
    setIsValidating(true);
    try {
      const resp = await fetchWithAuth("/api/motiongram/validate", {
        method: "POST",
        body: JSON.stringify({ yaml_text: yamlSpec }),
      });
      const data = await resp.json();
      if (data.valid) {
        toast.success("MotionGram YAML specification is valid!");
      } else {
        toast.error(`Validation error: ${data.message || "Invalid syntax"}`);
        setErrorMessage(data.repair_prompt || data.message);
      }
    } catch (err: any) {
      toast.error(err?.message || "Validation failed.");
    } finally {
      setIsValidating(false);
    }
  };

  // Re-compile YAML to ManimCE
  const handleCompileCode = async () => {
    if (!yamlSpec.trim()) return;
    setIsCompiling(true);
    try {
      const resp = await fetchWithAuth("/api/motiongram/compile", {
        method: "POST",
        body: JSON.stringify({ yaml_text: yamlSpec }),
      });
      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        toast.error(errData?.detail?.error || "Compilation failed.");
        return;
      }
      const data = await resp.json();
      setCompiledCode(data.code);
      setActiveTab("code");
      toast.success("Compiled to ManimCE Python script!");
    } catch (err: any) {
      toast.error(err?.message || "Failed to compile.");
    } finally {
      setIsCompiling(false);
    }
  };

  // Re-render edited YAML
  const handleRerenderYaml = async () => {
    if (!yamlSpec.trim()) return;
    setStage("rendering");
    setErrorMessage(null);
    toast.info("Re-rendering animation from current YAML specification…");
    try {
      const renderResp = await fetchWithAuth("/api/motiongram/render", {
        method: "POST",
        body: JSON.stringify({
          yaml_text: yamlSpec,
          quality,
          conversation_id: conversationId,
          prompt: prompt.trim() || "MotionGram Custom Scene",
        }),
      });

      if (!renderResp.ok) {
        const errData = await renderResp.json().catch(() => ({}));
        const msg = errData?.detail || "Re-render failed.";
        setErrorMessage(typeof msg === "string" ? msg : JSON.stringify(msg));
        setStage("error");
        toast.error("Re-render failed.");
        return;
      }

      const renderData = await renderResp.json();
      setVideoResult({
        video_id: renderData.video_id,
        playback_url: renderData.playback_url || `/api/videos/${renderData.video_id}/stream`,
        scene_name: renderData.scene_name,
        status: renderData.status || "completed",
      });
      setStage("completed");
      setActiveTab("video");
      toast.success("Re-render completed!");
    } catch (err: any) {
      setErrorMessage(err?.message || "Re-render failed.");
      setStage("error");
    }
  };

  const handleCopy = (text: string, type: "yaml" | "code") => {
    navigator.clipboard.writeText(text);
    setCopiedType(type);
    toast.success(`Copied ${type.toUpperCase()} to clipboard.`);
    setTimeout(() => setCopiedType(null), 2000);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 sm:p-6 overflow-hidden">
      <div className="relative flex flex-col w-full max-w-6xl max-h-[92vh] rounded-2xl border border-white/10 bg-zinc-950/95 shadow-2xl text-zinc-100 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/10 px-6 py-4 bg-zinc-900/50">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-500 text-white shadow-lg shadow-cyan-500/20">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold tracking-tight text-white">
                  MotionGram Visual Studio
                </h2>
                <Badge variant="outline" className="border-cyan-500/30 text-cyan-400 bg-cyan-950/40 text-[10px]">
                  /visual
                </Badge>
                <Badge variant="outline" className="border-indigo-500/30 text-indigo-400 bg-indigo-950/40 text-[10px]">
                  ManimCE Transpiler
                </Badge>
                <Badge variant="outline" className="border-emerald-500/30 text-emerald-400 bg-emerald-950/40 text-[10px]">
                  Kinetic Narration
                </Badge>
              </div>
              <p className="text-xs text-zinc-400">
                Deterministic mathematical explainer animations with bookmark-aligned speech
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              onClick={closeVisual}
              className="h-8 w-8 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Body Layout: Left Controls, Right Preview */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden">
          {/* Left Column: Input, Presets, Voice & Render Options */}
          <div className="lg:col-span-5 border-r border-white/10 p-5 flex flex-col gap-4 overflow-y-auto max-h-[calc(92vh-75px)]">
            <div>
              <label className="text-xs font-semibold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5 mb-1.5">
                <BookOpen className="h-3.5 w-3.5 text-cyan-400" />
                Teaching Concept / Prompt
              </label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="e.g. Explain Query, Key, and Value projection in Transformer Self-Attention with animated matrices..."
                rows={3}
                className="w-full resize-none rounded-xl border border-white/10 bg-zinc-900/80 px-3.5 py-2.5 text-xs text-white placeholder-zinc-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 transition-all leading-relaxed"
              />
            </div>

            {/* Presets */}
            <div>
              <p className="text-[11px] font-medium text-zinc-400 mb-1.5 flex items-center gap-1">
                <Wand2 className="h-3 w-3 text-indigo-400" />
                Curated Pedagogical Presets
              </p>
              <div className="flex flex-wrap gap-1.5">
                {PRESET_TOPICS.map((preset) => (
                  <button
                    key={preset.title}
                    type="button"
                    onClick={() => {
                      setPrompt(preset.prompt);
                      setVoiceName(preset.voice);
                    }}
                    className="rounded-lg border border-white/10 bg-zinc-900/60 px-2.5 py-1 text-[11px] text-zinc-300 hover:border-cyan-500/40 hover:bg-cyan-950/30 hover:text-cyan-200 transition-all text-left"
                  >
                    {preset.title}
                  </button>
                ))}
              </div>
            </div>

            {/* Narration & Voiceover Options */}
            <div className="rounded-xl border border-white/10 bg-zinc-900/40 p-3.5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5">
                  <Mic className="h-3.5 w-3.5 text-emerald-400" />
                  Voiceover Speech Backend
                </span>
                <span className="text-[10px] text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded-full border border-emerald-500/20">
                  Dytto Engine
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-zinc-400 block mb-1">Speech Model</label>
                  <select
                    value={voiceBackend}
                    onChange={(e) => setVoiceBackend(e.target.value as MotionGramVoiceBackend)}
                    className="w-full appearance-none rounded-lg border border-white/10 bg-zinc-800 px-2.5 py-1.5 text-xs text-white outline-none focus:border-cyan-500"
                  >
                    <option value="edge-tts">Edge-TTS (Neural Cloud)</option>
                    <option value="pocket-tts">Pocket TTS (Fast CPU)</option>
                    <option value="dsm">Kyutai DSM (Streaming)</option>
                    <option value="kitten">KittenTTS (Local)</option>
                  </select>
                </div>

                <div>
                  <label className="text-[10px] text-zinc-400 block mb-1">Voice Profile</label>
                  <select
                    value={voiceName}
                    onChange={(e) => setVoiceName(e.target.value)}
                    className="w-full appearance-none rounded-lg border border-white/10 bg-zinc-800 px-2.5 py-1.5 text-xs text-white outline-none focus:border-cyan-500"
                  >
                    <option value="en-US-ChristopherNeural">Christopher (Natural Explainer)</option>
                    <option value="en-US-JennyNeural">Jenny (Expressive & Clear)</option>
                    <option value="alba">Alba (Pocket TTS Default)</option>
                    <option value="en-GB-SoniaNeural">Sonia (British Academic)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-[10px] text-zinc-400 block mb-1">Render Resolution</label>
                <div className="flex gap-2">
                  {[
                    { id: "l", label: "Preview (480p)", desc: "Instant draft" },
                    { id: "m", label: "Medium (720p)", desc: "Recommended" },
                    { id: "h", label: "High (1080p)", desc: "Production HD" },
                  ].map((q) => (
                    <button
                      key={q.id}
                      type="button"
                      onClick={() => setQuality(q.id as MotionGramQuality)}
                      className={`flex-1 rounded-lg border px-2 py-1 text-left transition-all ${
                        quality === q.id
                          ? "border-cyan-500 bg-cyan-950/40 text-cyan-200"
                          : "border-white/10 bg-zinc-800/60 text-zinc-400 hover:border-white/20"
                      }`}
                    >
                      <p className="text-[11px] font-medium leading-tight">{q.label}</p>
                      <p className="text-[9px] text-zinc-500">{q.desc}</p>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Primary Action Button */}
            <Button
              onClick={handleGenerateAndRender}
              disabled={stage === "storyboard" || stage === "rendering" || !prompt.trim()}
              className="w-full py-5 rounded-xl bg-gradient-to-r from-cyan-600 via-indigo-600 to-purple-600 hover:from-cyan-500 hover:via-indigo-500 hover:to-purple-500 text-white font-semibold text-xs shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
            >
              {stage === "storyboard" ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Generating Storyboard & Self-Healing…
                </>
              ) : stage === "rendering" ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Transpiling & Rendering ManimCE Video…
                </>
              ) : (
                <>
                  <Clapperboard className="h-4 w-4" />
                  Generate & Render Animation
                </>
              )}
            </Button>

            {/* Secondary Controls: Live Validate & Re-render */}
            {yamlSpec && (
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleValidateYaml}
                  disabled={isValidating}
                  className="flex-1 text-[11px] border-white/15 bg-zinc-900 hover:bg-zinc-800 text-zinc-300"
                >
                  <CheckCircle2 className="h-3.5 w-3.5 mr-1.5 text-emerald-400" />
                  {isValidating ? "Validating…" : "Validate Syntax"}
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCompileCode}
                  disabled={isCompiling}
                  className="flex-1 text-[11px] border-white/15 bg-zinc-900 hover:bg-zinc-800 text-zinc-300"
                >
                  <FileCode className="h-3.5 w-3.5 mr-1.5 text-indigo-400" />
                  {isCompiling ? "Compiling…" : "Compile ManimCE"}
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRerenderYaml}
                  disabled={stage === "rendering"}
                  className="flex-1 text-[11px] border-white/15 bg-zinc-900 hover:bg-zinc-800 text-zinc-300"
                >
                  <Play className="h-3.5 w-3.5 mr-1.5 text-cyan-400" />
                  Re-Render
                </Button>
              </div>
            )}

            {/* Self-Healing Status Notification */}
            {repairAttempts > 1 && (
              <div className="rounded-lg border border-amber-500/20 bg-amber-950/30 p-2.5 flex items-start gap-2">
                <Activity className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                <div className="text-[11px] text-amber-200">
                  <span className="font-semibold">Self-Healing Resolved:</span> Corrected schema & LaTeX syntax across {repairAttempts} reflective iteration(s).
                </div>
              </div>
            )}

            {errorMessage && (
              <div className="rounded-lg border border-rose-500/20 bg-rose-950/30 p-3 flex items-start gap-2">
                <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                <div className="text-[11px] text-rose-200">
                  <p className="font-semibold mb-0.5">Execution Diagnostic</p>
                  <p className="font-mono text-[10px] leading-relaxed break-all">{errorMessage}</p>
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Video Player, Narration Transcripts, YAML, and Code */}
          <div className="lg:col-span-7 flex flex-col h-full bg-zinc-950 overflow-hidden">
            {/* Tab navigation */}
            <div className="flex items-center justify-between border-b border-white/10 px-4 py-2 bg-zinc-900/30">
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setActiveTab("video")}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    activeTab === "video"
                      ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/30"
                      : "text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  <Play className="h-3.5 w-3.5" />
                  Rendered Video
                </button>

                <button
                  type="button"
                  onClick={() => setActiveTab("narration")}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    activeTab === "narration"
                      ? "bg-indigo-500/15 text-indigo-300 border border-indigo-500/30"
                      : "text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  <Volume2 className="h-3.5 w-3.5" />
                  Narration & Bookmarks
                </button>

                <button
                  type="button"
                  onClick={() => setActiveTab("yaml")}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    activeTab === "yaml"
                      ? "bg-purple-500/15 text-purple-300 border border-purple-500/30"
                      : "text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  <FileCode className="h-3.5 w-3.5" />
                  MotionGram YAML
                </button>

                <button
                  type="button"
                  onClick={() => setActiveTab("code")}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    activeTab === "code"
                      ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                      : "text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  <Code2 className="h-3.5 w-3.5" />
                  ManimCE Code
                </button>

                {diagnostics.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setActiveTab("diagnostics")}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      activeTab === "diagnostics"
                        ? "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                        : "text-zinc-400 hover:text-zinc-200"
                    }`}
                  >
                    <Activity className="h-3.5 w-3.5" />
                    Diagnostics ({diagnostics.length})
                  </button>
                )}
              </div>

              {/* Copy actions */}
              <div className="flex items-center gap-2">
                {activeTab === "yaml" && yamlSpec && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleCopy(yamlSpec, "yaml")}
                    className="h-7 text-xs text-zinc-400 hover:text-white"
                  >
                    {copiedType === "yaml" ? <Check className="h-3.5 w-3.5 text-emerald-400 mr-1" /> : <Copy className="h-3.5 w-3.5 mr-1" />}
                    Copy YAML
                  </Button>
                )}
                {activeTab === "code" && compiledCode && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleCopy(compiledCode, "code")}
                    className="h-7 text-xs text-zinc-400 hover:text-white"
                  >
                    {copiedType === "code" ? <Check className="h-3.5 w-3.5 text-emerald-400 mr-1" /> : <Copy className="h-3.5 w-3.5 mr-1" />}
                    Copy Code
                  </Button>
                )}
              </div>
            </div>

            {/* Tab Contents */}
            <div className="flex-1 p-5 overflow-y-auto">
              {activeTab === "video" && (
                <div className="flex flex-col items-center justify-center h-full min-h-[360px]">
                  {videoResult?.playback_url ? (
                    <div className="w-full max-w-2xl space-y-3">
                      <div className="rounded-xl overflow-hidden border border-white/10 shadow-2xl bg-black aspect-video flex items-center justify-center">
                        <AppVideoPlayer
                          src={videoResult.playback_url}
                          className="w-full h-full object-contain"
                        />
                      </div>
                      <div className="flex items-center justify-between text-xs text-zinc-400 px-1">
                        <span className="flex items-center gap-1.5 text-emerald-400">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          Generated Scene: {videoResult.scene_name || "MotionGramScene"}
                        </span>
                        <a
                          href={videoResult.playback_url}
                          download={`motiongram_${videoResult.video_id}.mp4`}
                          className="inline-flex items-center gap-1 text-cyan-400 hover:underline"
                        >
                          <Download className="h-3 w-3" />
                          Download MP4
                        </a>
                      </div>
                    </div>
                  ) : stage === "rendering" || stage === "storyboard" ? (
                    <div className="text-center space-y-3">
                      <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-cyan-950/60 text-cyan-400 border border-cyan-500/20 animate-pulse">
                        <Clapperboard className="h-6 w-6" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-white">
                          {stage === "storyboard"
                            ? "Creating MotionGram Storyboard & Bookmarks…"
                            : "Rendering ManimCE Video…"}
                        </p>
                        <p className="text-xs text-zinc-400 mt-1 max-w-sm mx-auto">
                          Synchronizing voiceover audio with kinetic animations via AOSSpeechService.
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center space-y-3 text-zinc-500 max-w-sm">
                      <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-zinc-900 border border-white/5">
                        <Play className="h-5 w-5" />
                      </div>
                      <p className="text-xs">
                        Enter an educational topic on the left and click{" "}
                        <span className="text-cyan-400 font-medium">Generate & Render</span> to synthesize a short, narrated ManimCE explainer.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {activeTab === "narration" && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
                      <Volume2 className="h-3.5 w-3.5 text-emerald-400" />
                      Spoken Script & Kinetic Reveal Cues
                    </h3>
                    <Badge variant="outline" className="text-[10px] border-emerald-500/30 text-emerald-400">
                      {narrationBlocks.length} Voiceover Block(s)
                    </Badge>
                  </div>

                  {narrationBlocks.length > 0 ? (
                    <div className="space-y-3">
                      {narrationBlocks.map((block, idx) => (
                        <div
                          key={idx}
                          className="rounded-xl border border-white/10 bg-zinc-900/60 p-4 space-y-2.5"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider">
                              Block #{idx + 1}
                            </span>
                            <div className="flex items-center gap-1">
                              {block.bookmarks.map((bm) => (
                                <Badge
                                  key={bm}
                                  variant="secondary"
                                  className="text-[10px] bg-cyan-950/80 text-cyan-300 border border-cyan-500/30"
                                >
                                  <Bookmark className="h-2.5 w-2.5 mr-1 text-cyan-400" />
                                  {bm}
                                </Badge>
                              ))}
                            </div>
                          </div>
                          <p className="text-xs text-zinc-200 leading-relaxed font-sans">
                            {block.text}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-zinc-500">
                      No voiceover blocks found. Generate a MotionGram animation to view synced narration and bookmarks.
                    </p>
                  )}
                </div>
              )}

              {activeTab === "yaml" && (
                <div className="space-y-2 h-full flex flex-col">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-zinc-300">
                      Declarative Specification (Edit directly & re-render)
                    </span>
                  </div>
                  <textarea
                    value={yamlSpec}
                    onChange={(e) => setYamlSpec(e.target.value)}
                    placeholder="MotionGram YAML specification will appear here..."
                    className="flex-1 w-full min-h-[380px] rounded-xl border border-white/10 bg-zinc-900/90 p-4 font-mono text-xs text-cyan-200 placeholder-zinc-600 focus:outline-none focus:border-cyan-500 leading-relaxed resize-none"
                  />
                </div>
              )}

              {activeTab === "code" && (
                <div className="space-y-2 h-full flex flex-col">
                  <span className="text-xs font-semibold text-zinc-300">
                    Transpiled Python ManimCE Code (VoiceoverScene)
                  </span>
                  <pre className="flex-1 w-full min-h-[380px] rounded-xl border border-white/10 bg-zinc-900/90 p-4 font-mono text-xs text-emerald-300 overflow-auto leading-relaxed">
                    <code>{compiledCode || "# Compiled ManimCE code will be displayed here."}</code>
                  </pre>
                </div>
              )}

              {activeTab === "diagnostics" && (
                <div className="space-y-3">
                  <h3 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
                    Self-Healing Diagnostic Logs
                  </h3>
                  <div className="space-y-2">
                    {diagnostics.map((diag, i) => (
                      <div
                        key={i}
                        className="rounded-lg border border-white/10 bg-zinc-900/80 p-3 font-mono text-[11px] text-zinc-300 leading-relaxed"
                      >
                        {diag}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
