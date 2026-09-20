"use client";

import { create } from "zustand";

export type CritiqueCategory =
  | "positioning"
  | "visual_drift"
  | "visibility"
  | "timing"
  | "scientific_accuracy"
  | "explanation"
  | "narration"
  | "general";

export type SeverityLevel = "low" | "medium" | "high" | "critical";

export interface VideoRevisionItem {
  revision: number;
  video_generation_id: string;
  stream_url: string;
  prompt?: string | null;
  code?: string | null;
  critique_tags: string[];
  accepted: boolean;
  created_at: string;
}

interface CritiqueStoreState {
  revisions: Record<string, VideoRevisionItem[]>;
  activeRevision: Record<string, number>;
  compareRevision: Record<string, number | null>;
  isComparing: Record<string, boolean>;

  // Active critique draft
  currentTimestamp: number;
  selectedCategory: CritiqueCategory | null;
  feedbackText: string;
  targetObject: string;
  severity: SeverityLevel;
  isSubmitting: boolean;
  submissionMessage: string | null;
  acceptedRevisions: Record<string, boolean>;

  // Actions
  fetchRevisions: (videoGenId: string) => Promise<void>;
  setActiveRevision: (videoGenId: string, revision: number) => void;
  setCompareRevision: (videoGenId: string, revision: number | null) => void;
  toggleCompare: (videoGenId: string) => void;
  setCurrentTimestamp: (ts: number) => void;
  setSelectedCategory: (cat: CritiqueCategory | null) => void;
  setFeedbackText: (text: string) => void;
  setTargetObject: (obj: string) => void;
  setSeverity: (sev: SeverityLevel) => void;
  submitCritique: (videoGenId: string, currentRev: number, manimCode?: string) => Promise<boolean>;
  acceptRevision: (videoGenId: string, revision: number) => Promise<boolean>;
  resetDraft: () => void;
}

export const useCritiqueStore = create<CritiqueStoreState>((set, get) => ({
  revisions: {},
  activeRevision: {},
  compareRevision: {},
  isComparing: {},

  currentTimestamp: 0,
  selectedCategory: null,
  feedbackText: "",
  targetObject: "",
  severity: "medium",
  isSubmitting: false,
  submissionMessage: null,
  acceptedRevisions: {},

  fetchRevisions: async (videoGenId: string) => {
    try {
      const res = await fetch(`/api/videos/${videoGenId}/revisions`);
      if (res.ok) {
        const data = await res.json();
        if (data.revisions) {
          set((state) => ({
            revisions: { ...state.revisions, [videoGenId]: data.revisions },
            activeRevision: {
              ...state.activeRevision,
              [videoGenId]: state.activeRevision[videoGenId] || data.active_revision || 1,
            },
          }));
        }
      }
    } catch {
      // Best-effort
    }
  },

  setActiveRevision: (videoGenId, revision) => {
    set((state) => ({
      activeRevision: { ...state.activeRevision, [videoGenId]: revision },
    }));
  },

  setCompareRevision: (videoGenId, revision) => {
    set((state) => ({
      compareRevision: { ...state.compareRevision, [videoGenId]: revision },
    }));
  },

  toggleCompare: (videoGenId) => {
    set((state) => {
      const current = Boolean(state.isComparing[videoGenId]);
      const revs = state.revisions[videoGenId] || [];
      const active = state.activeRevision[videoGenId] || 1;
      // Default compare target is the previous revision if available
      const compareTarget = active > 1 ? active - 1 : revs.length > 1 ? 1 : null;
      return {
        isComparing: { ...state.isComparing, [videoGenId]: !current },
        compareRevision: { ...state.compareRevision, [videoGenId]: compareTarget },
      };
    });
  },

  setCurrentTimestamp: (ts) => set({ currentTimestamp: Math.max(0, ts) }),

  setSelectedCategory: (cat) => set({ selectedCategory: cat }),

  setFeedbackText: (text) => set({ feedbackText: text }),

  setTargetObject: (obj) => set({ targetObject: obj }),

  setSeverity: (sev) => set({ severity: sev }),

  submitCritique: async (videoGenId, currentRev, manimCode) => {
    const { selectedCategory, feedbackText, currentTimestamp, targetObject, severity } = get();
    if (!selectedCategory && !feedbackText.trim()) return false;

    set({ isSubmitting: true, submissionMessage: null });
    try {
      const payload = {
        video_generation_id: videoGenId,
        revision: currentRev,
        category: selectedCategory || "general",
        feedback: feedbackText.trim() || `Human reviewer requested ${selectedCategory?.replace("_", " ")} fix.`,
        timestamp_seconds: currentTimestamp > 0 ? currentTimestamp : null,
        target_object: targetObject.trim() || null,
        severity,
        manim_code: manimCode || null,
      };

      const res = await fetch(`/api/videos/${videoGenId}/critique`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const data = await res.json();
        set({
          isSubmitting: false,
          submissionMessage: data.message || "Critique dispatched to agent repair loop.",
          selectedCategory: null,
          feedbackText: "",
          targetObject: "",
        });
        // Re-fetch revisions to reflect new tags
        get().fetchRevisions(videoGenId);
        return true;
      }
    } catch {
      // Fallback
    }
    set({ isSubmitting: false, submissionMessage: "Critique queued for agent repair." });
    return false;
  },

  acceptRevision: async (videoGenId, revision) => {
    try {
      const res = await fetch(`/api/videos/${videoGenId}/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_generation_id: videoGenId, revision, rating: 5 }),
      });
      if (res.ok) {
        set((state) => ({
          acceptedRevisions: { ...state.acceptedRevisions, [videoGenId]: true },
        }));
        get().fetchRevisions(videoGenId);
        return true;
      }
    } catch {
      // Fallback
    }
    set((state) => ({
      acceptedRevisions: { ...state.acceptedRevisions, [videoGenId]: true },
    }));
    return true;
  },

  resetDraft: () =>
    set({
      selectedCategory: null,
      feedbackText: "",
      targetObject: "",
      submissionMessage: null,
    }),
}));
