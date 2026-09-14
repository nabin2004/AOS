"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * Browser-local OpenAI-compatible provider config (BYOK).
 * Empty `baseUrl` → server default (OpenRouter + OPENROUTER_API_KEY).
 * Empty `apiKey` with a custom base URL → keyless local endpoints.
 *
 * Shape is intentionally API-friendly so a future per-user server sync can
 * replace localStorage without rewriting chat/WS callers.
 */
export interface LlmProviderConfig {
  baseUrl: string;
  apiKey: string;
  modelId: string;
}

export interface LlmProviderRequestPayload {
  llm_base_url?: string;
  llm_api_key?: string;
  model?: string;
}

interface LlmProviderState extends LlmProviderConfig {
  setBaseUrl: (baseUrl: string) => void;
  setApiKey: (apiKey: string) => void;
  setModelId: (modelId: string) => void;
  setConfig: (partial: Partial<LlmProviderConfig>) => void;
  reset: () => void;
  /** Fields to merge into the chat WebSocket send payload. */
  toRequestPayload: () => LlmProviderRequestPayload;
}

export const DEFAULT_MODAL_BASE_URL =
  "https://nabinoli2004--aosqwen-server.us-east.modal.direct/v1";
export const DEFAULT_MODAL_MODEL_ID = "nabin2004/AOS-qwen3-8b-grpo";

const EMPTY: LlmProviderConfig = {
  baseUrl: DEFAULT_MODAL_BASE_URL,
  apiKey: "local",
  modelId: DEFAULT_MODAL_MODEL_ID,
};

export function llmProviderToRequestPayload(
  config: LlmProviderConfig,
): LlmProviderRequestPayload {
  const baseUrl = (config.baseUrl || DEFAULT_MODAL_BASE_URL).trim();
  const apiKey = (config.apiKey || "local").trim();
  const modelId = (config.modelId || DEFAULT_MODAL_MODEL_ID).trim();
  const payload: LlmProviderRequestPayload = {};
  if (baseUrl) payload.llm_base_url = baseUrl;
  if (apiKey) payload.llm_api_key = apiKey;
  if (modelId) payload.model = modelId;
  return payload;
}

export const useLlmProviderStore = create<LlmProviderState>()(
  persist(
    (set, get) => ({
      ...EMPTY,
      setBaseUrl: (baseUrl) => set({ baseUrl }),
      setApiKey: (apiKey) => set({ apiKey }),
      setModelId: (modelId) => set({ modelId }),
      setConfig: (partial) => set(partial),
      reset: () => set({ ...EMPTY }),
      toRequestPayload: () => {
        const { baseUrl, apiKey, modelId } = get();
        return llmProviderToRequestPayload({ baseUrl, apiKey, modelId });
      },
    }),
    {
      name: "aos.llm-provider.v1",
      partialize: (state) => ({
        baseUrl: state.baseUrl,
        apiKey: state.apiKey,
        modelId: state.modelId,
      }),
    },
  ),
);
