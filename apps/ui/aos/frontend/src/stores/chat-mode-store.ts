"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type VideoMode = "off" | "animate" | "lecture";
export type HarnessMode = "off" | "educlaw";

/**
 * Per-client chat-mode toggles:
 * - deepResearch: planner + parallel subagents
 * - videoMode: Manim video pipeline (off | animate | lecture)
 * - harnessMode: EduClaw sandboxed coding harness (off | educlaw)
 * - headless / autoApprove: automation options for tool executions
 *
 * Carried on the WS payload. Persisted so preferences survive a refresh.
 */
interface ChatModeState {
  deepResearch: boolean;
  setDeepResearch: (on: boolean) => void;
  toggleDeepResearch: () => void;
  videoMode: VideoMode;
  setVideoMode: (mode: VideoMode) => void;
  harnessMode: HarnessMode;
  setHarnessMode: (mode: HarnessMode) => void;
  headless: boolean;
  setHeadless: (val: boolean) => void;
  autoApprove: boolean;
  setAutoApprove: (val: boolean) => void;
}

export const useChatModeStore = create<ChatModeState>()(
  persist(
    (set) => ({
      deepResearch: false,
      setDeepResearch: (on) => set({ deepResearch: on }),
      toggleDeepResearch: () => set((s) => ({ deepResearch: !s.deepResearch })),
      videoMode: "off",
      setVideoMode: (mode) => set({ videoMode: mode }),
      harnessMode: "off",
      setHarnessMode: (mode) => set({ harnessMode: mode }),
      headless: true,
      setHeadless: (val) => set({ headless: val }),
      autoApprove: true,
      setAutoApprove: (val) => set({ autoApprove: val }),
    }),
    {
      name: "chat-mode",
      version: 3,
      migrate: (persisted, version) => {
        const state = (persisted ?? {}) as Partial<ChatModeState>;
        if (version < 3) {
          return {
            deepResearch: Boolean(state.deepResearch),
            videoMode: (state.videoMode || "off") as VideoMode,
            harnessMode: (state.harnessMode || "off") as HarnessMode,
            headless: state.headless ?? true,
            autoApprove: state.autoApprove ?? true,
          };
        }
        return state as ChatModeState;
      },
    },
  ),
);
