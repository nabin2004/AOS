"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type VideoMode = "off" | "animate" | "lecture";

/**
 * Per-client chat-mode toggles:
 * - deepResearch: planner + parallel subagents
 * - videoMode: Manim video pipeline (off | animate | lecture)
 *
 * Carried on the WS payload. Persisted so preferences survive a refresh.
 */
interface ChatModeState {
  deepResearch: boolean;
  setDeepResearch: (on: boolean) => void;
  toggleDeepResearch: () => void;
  videoMode: VideoMode;
  setVideoMode: (mode: VideoMode) => void;
}

export const useChatModeStore = create<ChatModeState>()(
  persist(
    (set) => ({
      deepResearch: false,
      setDeepResearch: (on) => set({ deepResearch: on }),
      toggleDeepResearch: () => set((s) => ({ deepResearch: !s.deepResearch })),
      videoMode: "off",
      setVideoMode: (mode) => set({ videoMode: mode }),
    }),
    {
      name: "chat-mode",
      version: 2,
      migrate: (persisted, version) => {
        const state = (persisted ?? {}) as Partial<ChatModeState>;
        if (version < 2) {
          return {
            deepResearch: Boolean(state.deepResearch),
            videoMode: "off" as VideoMode,
          };
        }
        return state as ChatModeState;
      },
    },
  ),
);
