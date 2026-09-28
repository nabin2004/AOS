"use client";

import { useEffect, useState, useMemo } from "react";
import { FormField, Input } from "@/components/ui";
import {
  useLlmProviderStore,
  OLLAMA_DEFAULT_BASE_URL,
  DEFAULT_RUNPOD_BASE_URL,
  DEFAULT_RUNPOD_MODEL_ID,
} from "@/stores";
import { Cpu, RotateCcw, Sparkles, Cloud, Wand2 } from "lucide-react";

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
  const setRunpod = useLlmProviderStore((s) => s.setRunpod);
  const reset = useLlmProviderStore((s) => s.reset);

  const [ollamaRunning, setOllamaRunning] = useState(false);
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [remoteModels, setRemoteModels] = useState<string[]>([]);
  const [remoteLoading, setRemoteLoading] = useState(false);

  // Fetch local Ollama models on mount
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
    !baseUrl.trim() ||
    baseUrl.includes("11434") ||
    baseUrl.includes("localhost") ||
    baseUrl.includes("127.0.0.1") ||
    baseUrl.includes("host.docker.internal");

  const isRunpodSelected =
    baseUrl.includes("runpod.ai") || baseUrl.includes("runpod");

  // Auto-probe remote endpoint models when baseUrl is a custom remote URL
  useEffect(() => {
    const trimmedBase = baseUrl.trim();
    if (!trimmedBase || isOllamaSelected) {
      setRemoteModels([]);
      return;
    }

    const timer = setTimeout(() => {
      setRemoteLoading(true);
      const query = new URLSearchParams({
        base_url: trimmedBase,
      });
      if (apiKey.trim()) {
        query.set("api_key", apiKey.trim());
      }
      fetch(`/api/v1/agent/models?${query.toString()}`, { credentials: "include" })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
          if (data?.remote_models && Array.isArray(data.remote_models)) {
            setRemoteModels(data.remote_models);
          } else {
            setRemoteModels([]);
          }
        })
        .catch(() => setRemoteModels([]))
        .finally(() => setRemoteLoading(false));
    }, 600);

    return () => clearTimeout(timer);
  }, [baseUrl, apiKey, isOllamaSelected]);

  // Detected invalid Ollama format on remote endpoint
  const needsRemoteCleaning = useMemo(() => {
    if (isOllamaSelected || !modelId) return false;
    return modelId.startsWith("hf.co/") || modelId.endsWith(":latest");
  }, [isOllamaSelected, modelId]);

  const cleanedModelId = useMemo(() => {
    let m = modelId.trim();
    if (m.startsWith("hf.co/")) m = m.slice(6);
    if (m.endsWith(":latest")) m = m.slice(0, -7);
    return m;
  }, [modelId]);

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
            isOllamaSelected && !baseUrl.includes("runpod")
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

        <button
          type="button"
          onClick={() => {
            setRunpod(DEFAULT_RUNPOD_BASE_URL, DEFAULT_RUNPOD_MODEL_ID);
          }}
          className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors ${
            isRunpodSelected
              ? "border-purple-500/50 bg-purple-500/10 text-purple-400 font-semibold"
              : "border-border bg-accent/40 text-foreground/80 hover:bg-accent hover:text-foreground"
          }`}
        >
          <Cloud className="h-3.5 w-3.5 text-purple-400" />
          <span>RunPod vLLM</span>
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

      {/* Detected Remote Models on Active Endpoint */}
      {!isOllamaSelected && remoteModels.length > 0 && (
        <div className="space-y-1.5 rounded-xl border border-purple-500/40 bg-purple-500/10 p-2.5">
          <div className="flex items-center justify-between text-[11px] font-medium text-purple-300">
            <span className="flex items-center gap-1">
              <Sparkles className="h-3 w-3 text-purple-400" />
              Detected vLLM / RunPod Models ({remoteModels.length})
            </span>
          </div>
          <div className="flex flex-wrap gap-1">
            {remoteModels.map((m) => {
              const active = modelId === m;
              return (
                <button
                  key={m}
                  type="button"
                  onClick={() => setModelId(m)}
                  className={`rounded-md px-2 py-0.5 text-[11px] font-mono transition-colors ${
                    active
                      ? "bg-purple-600 text-white font-semibold"
                      : "bg-background/80 text-foreground/80 border border-purple-500/30 hover:border-purple-400"
                  }`}
                >
                  {m}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Installed Ollama Models Quick-Select */}
      {isOllamaSelected && ollamaModels.length > 0 && (
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
            ? "OpenAI-compatible /v1 endpoint (e.g. http://localhost:11434/v1 or https://<id>.api.runpod.ai/v1)."
            : "OpenAI-compatible endpoint (e.g. http://localhost:11434/v1 for Ollama, or https://<id>.api.runpod.ai/v1 for RunPod)."
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
            ? "RunPod User API Key (or 'local' for local Ollama)."
            : "RunPod User API Key for remote vLLM, or leave blank/'local' for keyless local Ollama."
        }
      >
        <Input
          type="password"
          placeholder={baseUrl.trim() ? "local (or RunPod API key)" : "optional override"}
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
          !isOllamaSelected
            ? "Exact model name loaded on your remote vLLM server (e.g. nabin2004/qwen-Manimator-1-grpo-merged)."
            : compact
            ? "Exact Ollama or custom model tag (e.g. hf.co/Qwen/Qwen3-8B-GGUF:latest)."
            : "Model name as your endpoint expects it (e.g. hf.co/Qwen/Qwen3-8B-GGUF:latest or qwen-manimator-1)."
        }
      >
        <div className="space-y-1.5">
          <Input
            type="text"
            placeholder={
              !isOllamaSelected
                ? "nabin2004/qwen-Manimator-1-grpo-merged"
                : "hf.co/Qwen/Qwen3-8B-GGUF:latest"
            }
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
            className={inputClass}
            autoComplete="off"
          />

          {needsRemoteCleaning && (
            <button
              type="button"
              onClick={() => setModelId(cleanedModelId)}
              className="flex items-center gap-1 text-[11px] text-amber-400 hover:text-amber-300 underline font-medium"
            >
              <Wand2 className="h-3 w-3" />
              <span>
                vLLM endpoint requires standard model name without &apos;hf.co/&apos; or &apos;:latest&apos;. Click to fix:{" "}
                <strong>{cleanedModelId}</strong>
              </span>
            </button>
          )}
        </div>
      </FormField>
    </div>
  );
}
