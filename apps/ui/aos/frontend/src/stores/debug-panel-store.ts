"use client";

import { create } from "zustand";

export interface DebugEvent {
  id: string;
  timestamp: string;
  type: string;
  direction: "in" | "out";
  data: unknown;
}

export interface DebugLog {
  id: number;
  timestamp: string;
  level: string;
  logger: string;
  message: string;
  exc_info?: string | null;
  trace_id?: string | null;
  span_id?: string | null;
  extra?: Record<string, unknown>;
}

export interface EndpointDiagnostic {
  error_type?: string;
  category?: string;
  message?: string;
  raw_error?: string;
  endpoint?: string;
  model?: string;
  hint?: string;
}

interface DebugPanelState {
  isOpen: boolean;
  activeTab: "diagnostics" | "events" | "logs";
  events: DebugEvent[];
  logs: DebugLog[];
  lastDiagnostic: EndpointDiagnostic | null;
  targetEndpoint: string | null;
  targetModel: string | null;
  logfireUrl: string;

  setOpen: (open: boolean) => void;
  toggleOpen: () => void;
  setActiveTab: (tab: "diagnostics" | "events" | "logs") => void;
  addEvent: (type: string, direction: "in" | "out", data: unknown) => void;
  setLogs: (logs: DebugLog[]) => void;
  addLog: (log: DebugLog) => void;
  setLastDiagnostic: (diag: EndpointDiagnostic | null) => void;
  setTargetInfo: (endpoint: string | null, model: string | null) => void;
  clearEvents: () => void;
  clearLogs: () => void;
}

export const useDebugPanelStore = create<DebugPanelState>((set) => ({
  isOpen: false,
  activeTab: "diagnostics",
  events: [],
  logs: [],
  lastDiagnostic: null,
  targetEndpoint: null,
  targetModel: null,
  logfireUrl: "https://logfire-eu.pydantic.dev/nabinoli2004/aos",

  setOpen: (open) => set({ isOpen: open }),
  toggleOpen: () => set((s) => ({ isOpen: !s.isOpen })),
  setActiveTab: (tab) => set({ activeTab: tab }),

  addEvent: (type, direction, data) =>
    set((state) => ({
      events: [
        {
          id: `evt-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
          timestamp: new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            fractionalSecondDigits: 3,
          }),
          type,
          direction,
          data,
        },
        ...state.events.slice(0, 199),
      ],
    })),

  setLogs: (logs) => set({ logs }),

  addLog: (log) =>
    set((state) => ({
      logs: [log, ...state.logs.slice(0, 499)],
    })),

  setLastDiagnostic: (diag) =>
    set({
      lastDiagnostic: diag,
      ...(diag ? { activeTab: "diagnostics" } : {}),
    }),

  setTargetInfo: (endpoint, model) =>
    set({
      targetEndpoint: endpoint,
      targetModel: model,
    }),

  clearEvents: () => set({ events: [] }),
  clearLogs: () => set({ logs: [] }),
}));
