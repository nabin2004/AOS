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
  isStudioOpen: boolean;
  startSession: (source: Omit<AnimationSession, "id" | "stage" | "emphasis" | "instructions">) => void;
  openStudio: (source?: Partial<Omit<AnimationSession, "id" | "stage" | "emphasis" | "instructions">>) => void;
  closeStudio: () => void;
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
  isStudioOpen: false,
  startSession: (source) =>
    set({
      activeSession: { ...source, id: sessionId(), stage: "composer", emphasis: "ai", instructions: "" },
    }),
  openStudio: (source) =>
    set((state) => {
      const sourcePrompt = source?.sourcePrompt ?? source?.sourceText ?? "";
      const sourceText = source?.sourceText ?? source?.sourcePrompt ?? "";
      const conversationId = source?.conversationId ?? state.activeSession?.conversationId;
      const sourceMessageId = source?.sourceMessageId ?? state.activeSession?.sourceMessageId ?? `prompt-${Date.now()}`;

      const activeSession: AnimationSession = {
        id: state.activeSession?.id ?? sessionId(),
        conversationId,
        sourceMessageId,
        sourcePrompt,
        sourceText,
        stage: state.activeSession?.stage ?? "composer",
        emphasis: state.activeSession?.emphasis ?? "ai",
        instructions: state.activeSession?.instructions ?? "",
        composerPlan: state.activeSession?.composerPlan,
        generatedCode: state.activeSession?.generatedCode,
        render: state.activeSession?.render,
      };

      return {
        isStudioOpen: true,
        activeSession,
      };
    }),
  closeStudio: () => set({ isStudioOpen: false }),
  updateSession: (update) => set((state) => ({ activeSession: state.activeSession ? { ...state.activeSession, ...update } : null })),
  clearSession: () => set({ activeSession: null, isStudioOpen: false }),
}));
