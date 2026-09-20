"use client";

import { useEffect, useState } from "react";
import { FormField, Input } from "@/components/ui";
import { useLlmProviderStore, OLLAMA_DEFAULT_BASE_URL } from "@/stores";
import { Cpu, RotateCcw, Sparkles } from "lucide-react";

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
  const setOllama = useLlmProviderStore((s) => s.setOllama);
  const reset = useLlmProviderStore((s) => s.reset);

  const [ollamaRunning, setOllamaRunning] = useState(false);
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);

  useEffect(() => {
    fetch("/api/v1/agent/models", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.ollama_models && data.ollama_models.length > 0) {
          setOllamaRunning(true);
          setOllamaModels(data.ollama_models);
        } else if (data?.ollama_running) {
          setOllamaRunning(true);
        }
      })
      .catch(() => {});
  }, []);

  const inputClass = compact ? "h-8 text-xs" : undefined;
  const prefix = compact ? "chat-llm" : "settings-llm";

  const isOllamaSelected =
    baseUrl.includes("11434") ||
    baseUrl.includes("localhost") ||
    baseUrl.includes("host.docker.internal");

  return (
    <div className={compact ? "space-y-3" : "space-y-4"}>
      {/* Quick Presets */}
      <div className="flex flex-wrap items-center gap-1.5 pb-1">
        <button
          type="button"
          onClick={() => {
            const firstModel =
              ollamaModels[0] || "hf.co/Qwen/Qwen3-8B-GGUF:latest";
            setOllama(firstModel);
          }}
          className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors ${
            isOllamaSelected
              ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-400"
              : "border-border bg-accent/40 text-foreground/80 hover:bg-accent hover:text-foreground"
          }`}
        >
          <Cpu className="h-3.5 w-3.5" />
          <span>Local Ollama</span>
          {ollamaRunning && (
            <span className="ml-1 inline-block h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          )}
        </button>

        {(baseUrl || apiKey || modelId) && (
          <button
            type="button"
            onClick={() => reset()}
            className="inline-flex items-center gap-1 rounded-lg border border-border bg-accent/20 px-2 py-1 text-xs text-foreground/60 transition-colors hover:bg-accent hover:text-foreground"
            title="Reset to server default (OpenRouter)"
          >
            <RotateCcw className="h-3 w-3" />
            <span>Reset (Cloud OpenRouter)</span>
          </button>
        )}
      </div>

      {/* Installed Ollama Models Quick-Select */}
      {ollamaModels.length > 0 && (
        <div className="space-y-1.5 rounded-xl border border-border/70 bg-accent/20 p-2.5">
          <div className="flex items-center justify-between text-[11px] font-medium text-foreground/70">
            <span className="flex items-center gap-1">
              <Sparkles className="h-3 w-3 text-amber-400" />
              Detected Local Ollama Models ({ollamaModels.length})
            </span>
          </div>
          <div className="flex flex-wrap gap-1">
            {ollamaModels.map((m) => {
              const active = modelId === m;
              return (
                <button
                  key={m}
                  type="button"
                  onClick={() => {
                    if (!baseUrl.trim()) {
                      setBaseUrl(OLLAMA_DEFAULT_BASE_URL);
                    }
                    if (!apiKey.trim()) {
                      setApiKey("local");
                    }
                    setModelId(m);
                  }}
                  className={`rounded-md px-2 py-0.5 text-[11px] font-mono transition-colors ${
                    active
                      ? "bg-primary text-primary-foreground font-semibold"
                      : "bg-background/80 text-foreground/70 border border-border/60 hover:border-foreground/30 hover:text-foreground"
                  }`}
                >
                  {m.length > 28 ? m.replace(/^hf\.co\//, "") : m}
                </button>
              );
            })}
          </div>
        </div>
      )}

      <FormField
        label="API base URL"
        htmlFor={`${prefix}-base-url`}
        description={
          compact
            ? "OpenAI-compatible /v1 endpoint (e.g. http://localhost:11434/v1). Empty = server default."
            : "OpenAI-compatible endpoint (e.g. http://localhost:11434/v1 for Ollama, or https://openrouter.ai/api/v1). Automatically routed inside Docker."
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
            ? "Optional — leave blank or 'local' for keyless local servers."
            : "Optional. Leave blank or 'local' for keyless Ollama/localhost models."
        }
      >
        <Input
          type="password"
          placeholder={baseUrl.trim() ? "local (optional)" : "optional override"}
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
            ? "Exact Ollama or custom model tag (e.g. hf.co/Qwen/Qwen3-8B-GGUF:latest)."
            : "Model name as your endpoint expects it (e.g. hf.co/Qwen/Qwen3-8B-GGUF:latest or qwen-manimator-1)."
        }
      >
        <Input
          type="text"
          placeholder="hf.co/Qwen/Qwen3-8B-GGUF:latest"
          value={modelId}
          onChange={(e) => setModelId(e.target.value)}
          className={inputClass}
          autoComplete="off"
        />
      </FormField>
    </div>
  );
}

