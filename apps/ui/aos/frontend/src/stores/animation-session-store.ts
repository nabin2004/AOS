"use client";

import { create } from "zustand";

export type AnimationStage = "composer" | "coding" | "rendering" | "review";
export type AnimationEmphasis = "concept" | "geometric" | "derivation" | "ai";

/** Context for one deliberate “Animate this” handoff from a chat response. */
export interface AnimationSession {
  id: string;
  conversationId?: string;
  sourceMessageId: string;
  sourcePrompt?: string;
  sourceText: string;
  stage: AnimationStage;
  emphasis: AnimationEmphasis;
  instructions: string;
  composerPlan?: string;
  generatedCode?: string;
  render?: { jobId: string; videoUrl?: string };
}

interface AnimationSessionState {
  activeSession: AnimationSession | null;
  startSession: (source: Omit<AnimationSession, "id" | "stage" | "emphasis" | "instructions">) => void;
  updateSession: (update: Partial<AnimationSession>) => void;
  clearSession: () => void;
}

function sessionId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `animation-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export const useAnimationSessionStore = create<AnimationSessionState>((set) => ({
  activeSession: null,
  startSession: (source) => set({ activeSession: { ...source, id: sessionId(), stage: "composer", emphasis: "ai", instructions: "" } }),
  updateSession: (update) => set((state) => ({ activeSession: state.activeSession ? { ...state.activeSession, ...update } : null })),
  clearSession: () => set({ activeSession: null }),
}));
