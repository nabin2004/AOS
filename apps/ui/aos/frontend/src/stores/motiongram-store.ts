"use client";

import { create } from "zustand";

export type MotionGramVoiceBackend = "edge-tts" | "pocket-tts" | "dsm" | "kitten";
export type MotionGramQuality = "l" | "m" | "h" | "k";
export type MotionGramStage =
  | "idle"
  | "storyboard"
  | "validating"
  | "compiling"
  | "rendering"
  | "completed"
  | "error";

export interface MotionGramVideoResult {
  video_id: string;
  playback_url: string;
  scene_name?: string;
  status: string;
}

interface MotionGramState {
  isOpen: boolean;
  prompt: string;
  voiceBackend: MotionGramVoiceBackend;
  voiceName: string;
  quality: MotionGramQuality;
  stage: MotionGramStage;
  yamlSpec: string;
  compiledCode: string;
  videoResult: MotionGramVideoResult | null;
  diagnostics: string[];
  repairAttempts: number;
  errorMessage: string | null;

  // Actions
  openVisual: (prompt?: string) => void;
  closeVisual: () => void;
  setPrompt: (prompt: string) => void;
  setVoiceBackend: (backend: MotionGramVoiceBackend) => void;
  setVoiceName: (name: string) => void;
  setQuality: (quality: MotionGramQuality) => void;
  setYamlSpec: (yaml: string) => void;
  setCompiledCode: (code: string) => void;
  setStage: (stage: MotionGramStage) => void;
  setVideoResult: (result: MotionGramVideoResult | null) => void;
  setDiagnostics: (diagnostics: string[]) => void;
  setRepairAttempts: (attempts: number) => void;
  setErrorMessage: (err: string | null) => void;
  resetSession: () => void;
}

export const useMotionGramStore = create<MotionGramState>((set) => ({
  isOpen: false,
  prompt: "",
  voiceBackend: "edge-tts",
  voiceName: "en-US-ChristopherNeural",
  quality: "m",
  stage: "idle",
  yamlSpec: "",
  compiledCode: "",
  videoResult: null,
  diagnostics: [],
  repairAttempts: 0,
  errorMessage: null,

  openVisual: (prompt?: string) =>
    set((state) => ({
      isOpen: true,
      prompt: prompt ?? state.prompt,
      stage: state.videoResult ? state.stage : "idle",
      errorMessage: null,
    })),

  closeVisual: () => set({ isOpen: false }),
  setPrompt: (prompt) => set({ prompt }),
  setVoiceBackend: (voiceBackend) => set({ voiceBackend }),
  setVoiceName: (voiceName) => set({ voiceName }),
  setQuality: (quality) => set({ quality }),
  setYamlSpec: (yamlSpec) => set({ yamlSpec }),
  setCompiledCode: (compiledCode) => set({ compiledCode }),
  setStage: (stage) => set({ stage }),
  setVideoResult: (videoResult) => set({ videoResult }),
  setDiagnostics: (diagnostics) => set({ diagnostics }),
  setRepairAttempts: (repairAttempts) => set({ repairAttempts }),
  setErrorMessage: (errorMessage) => set({ errorMessage }),
  resetSession: () =>
    set({
      stage: "idle",
      yamlSpec: "",
      compiledCode: "",
      videoResult: null,
      diagnostics: [],
      repairAttempts: 0,
      errorMessage: null,
    }),
}));
