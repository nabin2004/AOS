"use client";

import { FormField, Input } from "@/components/ui";
import { useLlmProviderStore } from "@/stores";

/**
 * Shared Base URL / API key / model fields for Settings and Chat Controls.
 * Values persist in the browser (localStorage) and apply to chat + Manim.
 */
export function LlmProviderForm({ compact = false }: { compact?: boolean }) {
  const baseUrl = useLlmProviderStore((s) => s.baseUrl);
  const apiKey = useLlmProviderStore((s) => s.apiKey);
  const modelId = useLlmProviderStore((s) => s.modelId);
  const setBaseUrl = useLlmProviderStore((s) => s.setBaseUrl);
  const setApiKey = useLlmProviderStore((s) => s.setApiKey);
  const setModelId = useLlmProviderStore((s) => s.setModelId);
  const reset = useLlmProviderStore((s) => s.reset);

  const inputClass = compact ? "h-8 text-xs" : undefined;
  const prefix = compact ? "chat-llm" : "settings-llm";

  return (
    <div className={compact ? "space-y-3" : "space-y-4"}>
      <FormField
        label="API base URL"
        htmlFor={`${prefix}-base-url`}
        description={
          compact
            ? "OpenAI-compatible /v1 endpoint. Empty = server OpenRouter."
            : "OpenAI-compatible endpoint (e.g. https://openrouter.ai/api/v1 or http://localhost:11434/v1). Leave empty to use the server OpenRouter key."
        }
      >
        <Input
          type="url"
          placeholder="http://localhost:11434/v1"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          className={inputClass}
          autoComplete="off"
        />
      </FormField>

      <FormField
        label="API key"
        htmlFor={`${prefix}-api-key`}
        description={
          compact
            ? "Optional — leave blank for keyless local servers."
            : "Optional. Leave blank for keyless localhost models. With no base URL, this overrides the server OpenRouter key for chat/video."
        }
      >
        <Input
          type="password"
          placeholder={baseUrl.trim() ? "optional" : "optional override"}
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          className={inputClass}
          autoComplete="off"
        />
      </FormField>

      <FormField
        label="Model id"
        htmlFor={`${prefix}-model`}
        description={
          compact
            ? "Required for custom endpoints (e.g. llama3.2)."
            : "Model name as your endpoint expects it (e.g. openai/gpt-4o-mini or llama3.2). Used for chat and Manim when set."
        }
      >
        <Input
          type="text"
          placeholder="model-id"
          value={modelId}
          onChange={(e) => setModelId(e.target.value)}
          className={inputClass}
          autoComplete="off"
        />
      </FormField>

      {(baseUrl || apiKey || modelId) && (
        <button
          type="button"
          onClick={() => reset()}
          className="text-foreground/55 hover:text-foreground text-[11px] underline-offset-2 hover:underline"
        >
          Reset to server defaults
        </button>
      )}
    </div>
  );
}
