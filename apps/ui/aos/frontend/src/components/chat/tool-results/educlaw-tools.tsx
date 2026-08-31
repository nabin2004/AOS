"use client";

import React, { useState } from "react";
import { CheckCircle2, XCircle, Terminal, FileCode, Play, AlertCircle, Copy, Check } from "lucide-react";
import { Button } from "@/components/ui";

interface EduClawToolProps {
  name: string;
  args?: Record<string, any>;
  result?: string | Record<string, any>;
  status?: "pending" | "running" | "completed" | "error";
}

export function EduClawToolResult({ name, args, result, status }: EduClawToolProps) {
  const [copied, setCopied] = useState(false);

  const rawResult = typeof result === "string" ? result : JSON.stringify(result, null, 2) || "";
  const isError = status === "error" || rawResult.toLowerCase().includes("error:") || rawResult.toLowerCase().includes("failed");

  const handleCopy = () => {
    navigator.clipboard.writeText(rawResult);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (name === "sandbox_write" || name === "sandbox_read") {
    const path = args?.path || "file";
    const content = args?.content || rawResult;
    return (
      <div className="flex flex-col gap-2 rounded-lg border border-border/50 bg-background/50 p-3 text-xs">
        <div className="flex items-center justify-between border-b border-border/40 pb-2">
          <div className="flex items-center gap-2 font-mono font-medium text-foreground">
            <FileCode className="h-4 w-4 text-sky-400" />
            <span>{path}</span>
            <span className="rounded bg-sky-500/10 px-1.5 py-0.5 text-[10px] text-sky-400">
              {name === "sandbox_write" ? "Wrote File" : "Read File"}
            </span>
          </div>
          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={handleCopy}>
            {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
          </Button>
        </div>
        <pre className="max-h-60 overflow-x-auto rounded bg-muted/40 p-2 font-mono text-[11px] text-muted-foreground">
          {content}
        </pre>
        {name === "sandbox_write" && rawResult && (
          <div className="text-[11px] text-muted-foreground/80 font-mono">
            {rawResult}
          </div>
        )}
      </div>
    );
  }

  if (name === "sandbox_bash") {
    const cmd = args?.command || "";
    return (
      <div className="flex flex-col gap-2 rounded-lg border border-border/50 bg-black/70 p-3 text-xs font-mono">
        <div className="flex items-center justify-between border-b border-border/40 pb-2">
          <div className="flex items-center gap-2 text-emerald-400 font-medium">
            <Terminal className="h-4 w-4" />
            <span>Docker Sandbox</span>
          </div>
          <span className="text-[10px] text-muted-foreground">$ {cmd}</span>
        </div>
        <pre className="max-h-60 overflow-x-auto whitespace-pre-wrap text-[11px] text-emerald-300">
          {rawResult || "(command executing in container...)"}
        </pre>
      </div>
    );
  }

  if (name === "manim_render") {
    const scene = `${args?.scene_file || ""}::${args?.scene_name || ""}`;
    return (
      <div className="flex flex-col gap-2 rounded-lg border border-border/50 bg-background/50 p-3 text-xs">
        <div className="flex items-center justify-between border-b border-border/40 pb-2">
          <div className="flex items-center gap-2 font-medium">
            <Play className="h-4 w-4 text-purple-400" />
            <span>Render Scene: {scene}</span>
          </div>
          <div className="flex items-center gap-1.5">
            {isError ? (
              <span className="flex items-center gap-1 text-red-400">
                <XCircle className="h-3.5 w-3.5" /> Render Failed
              </span>
            ) : status === "completed" ? (
              <span className="flex items-center gap-1 text-emerald-400">
                <CheckCircle2 className="h-3.5 w-3.5" /> Render OK
              </span>
            ) : (
              <span className="text-muted-foreground animate-pulse">Rendering...</span>
            )}
          </div>
        </div>
        <pre className="max-h-48 overflow-x-auto rounded bg-muted/40 p-2 font-mono text-[11px] text-muted-foreground">
          {rawResult}
        </pre>
      </div>
    );
  }

  if (name === "syntax_check" || name === "lsp_diagnostics") {
    const path = args?.path || "";
    return (
      <div className="flex flex-col gap-2 rounded-lg border border-border/50 bg-background/50 p-3 text-xs font-mono">
        <div className="flex items-center justify-between border-b border-border/40 pb-2">
          <div className="flex items-center gap-2 font-medium">
            <AlertCircle className="h-4 w-4 text-amber-400" />
            <span>Diagnostics: {path}</span>
          </div>
          {isError ? (
            <span className="text-red-400 font-sans">Syntax / Type Error</span>
          ) : (
            <span className="text-emerald-400 font-sans">Clean</span>
          )}
        </div>
        <pre className="max-h-48 overflow-x-auto whitespace-pre-wrap text-[11px] text-muted-foreground">
          {rawResult || "No diagnostic issues reported."}
        </pre>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border/50 bg-background/50 p-3 text-xs font-mono">
      <div className="font-medium text-foreground mb-1">Tool: {name}</div>
      <pre className="max-h-40 overflow-x-auto text-[11px] text-muted-foreground">
        {rawResult}
      </pre>
    </div>
  );
}
