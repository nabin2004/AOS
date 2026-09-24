"use client";

import React, { useState, useMemo } from "react";
import {
  AlertTriangle,
  AlertOctagon,
  Wand2,
  Edit3,
  Play,
  CheckCircle2,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Terminal,
  Lightbulb,
  Loader2,
  Sparkles,
  Code2,
  X,
  FileCode,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export interface PreflightIssue {
  type: string;
  severity: "error" | "warning" | "info";
  blocking: boolean;
  line?: number;
  column?: number;
  message: string;
  suggestion?: string | null;
  name?: string;
  index?: number;
  definition?: string;
  definition_line?: number;
  text?: string;
}

export interface ParsedDiagnostic {
  isStructuredPreflight: boolean;
  isTraceback: boolean;
  isRepairExhausted: boolean;
  status: "safe" | "warning" | "failed";
  blocking: boolean;
  issues: PreflightIssue[];
  repairAttemptsNotice?: string;
  // Compiler traceback specific
  exceptionType?: string;
  exceptionMessage?: string;
  crashedLineNumber?: number;
  crashedFunctionName?: string;
  crashedSnippet?: string;
  rawDetails: string;
}

/**
 * Intelligent error parser for Manim HITL pipeline.
 * Dissects raw JSON strings, HTTP 422 diagnostic bundles, Python stack traces, and repair exhaustion notices.
 */
function parseHitlDiagnostic(errorRaw: string, code: string): ParsedDiagnostic {
  const codeLines = code.split("\n");

  const getCodeSnippet = (lineNum?: number, context = 1) => {
    if (!lineNum || lineNum < 1 || lineNum > codeLines.length) return "";
    const start = Math.max(0, lineNum - 1 - context);
    const end = Math.min(codeLines.length, lineNum + context);
    return codeLines
      .slice(start, end)
      .map((line, idx) => {
        const currentLineNum = start + idx + 1;
        const isTarget = currentLineNum === lineNum;
        return `${isTarget ? "▶ " : "  "}${currentLineNum.toString().padStart(3, " ")} | ${line}`;
      })
      .join("\n");
  };

  // 1. Detect and strip repair exhaustion prefix
  let remainingText = errorRaw.trim();
  let repairAttemptsNotice: string | undefined;
  if (/Automatic repair exhausted after/i.test(remainingText)) {
    const splitIndex = remainingText.indexOf("\n\n");
    if (splitIndex !== -1) {
      repairAttemptsNotice = remainingText.slice(0, splitIndex).trim();
      remainingText = remainingText.slice(splitIndex + 2).trim();
    } else {
      repairAttemptsNotice = remainingText;
    }
  }

  // 2. Try parsing structured JSON diagnostic bundle
  let jsonCandidate = remainingText;
  const jsonMatch = remainingText.match(/\{[\s\S]*\}/);
  if (jsonMatch) {
    jsonCandidate = jsonMatch[0];
  }

  try {
    const parsed = JSON.parse(jsonCandidate);
    if (
      parsed &&
      (parsed.stage === "preflight" ||
        parsed.stage === "repair_preflight" ||
        Array.isArray(parsed.errors) ||
        Array.isArray(parsed.issues))
    ) {
      const rawIssues: Array<Record<string, unknown>> = Array.isArray(parsed.issues)
        ? parsed.issues
        : Array.isArray(parsed.errors)
        ? parsed.errors
        : [];

      const issues: PreflightIssue[] = rawIssues.map((item) => {
        const sev = (item.severity as string) || "error";
        const isWarning = sev === "warning" || item.type === "BrittleMobjectIndex" || item.type === "NonRawTexString" || item.type === "MobjectIndexShapeCheck";
        const blocking = typeof item.blocking === "boolean" ? item.blocking : !isWarning;
        return {
          type: String(item.type || "ValidationWarning"),
          severity: isWarning ? "warning" : "error",
          blocking: blocking,
          line: typeof item.line === "number" ? item.line : undefined,
          column: typeof item.column === "number" ? item.column : undefined,
          message: String(item.message || "Potential static compatibility concern"),
          suggestion: item.suggestion ? String(item.suggestion) : null,
          name: item.name ? String(item.name) : undefined,
          index: typeof item.index === "number" ? item.index : undefined,
          definition: item.definition ? String(item.definition) : undefined,
          definition_line: typeof item.definition_line === "number" ? item.definition_line : undefined,
          text: item.text ? String(item.text) : undefined,
        };
      });

      const hasBlocking = issues.some((i) => i.blocking);
      return {
        isStructuredPreflight: true,
        isTraceback: false,
        isRepairExhausted: Boolean(repairAttemptsNotice),
        status: hasBlocking ? "failed" : issues.length > 0 ? "warning" : "safe",
        blocking: hasBlocking,
        issues,
        repairAttemptsNotice,
        rawDetails: remainingText,
      };
    }
  } catch {
    // Not valid JSON, proceed to stack trace / compiler log parsing
  }

  // 3. Try parsing Python / Manim compiler traceback
  const isTraceback =
    remainingText.includes("Traceback (most recent call last):") ||
    /([A-Za-z0-9_]+Error|[A-Za-z0-9_]+Exception|LaTeX Error)/.test(remainingText);

  if (isTraceback) {
    // Find exception name and message (usually the last non-empty line)
    const lines = remainingText.split("\n").map((l) => l.trim()).filter(Boolean);
    let exceptionType = "ManimExecutionError";
    let exceptionMessage = "Runtime error during scene execution";

    for (let i = lines.length - 1; i >= 0; i--) {
      const line = lines[i]!;
      const match = line.match(/^([A-Za-z0-9_]+(?:Error|Exception)):\s*(.*)$/);
      if (match && match[1]) {
        exceptionType = match[1];
        exceptionMessage = match[2] || "Error executing scene";
        break;
      }
      if (/LaTeX Error/i.test(line)) {
        exceptionType = "LaTeXCompilationError";
        exceptionMessage = line;
        break;
      }
    }

    // Find failing line in user scene code (match file path or construct method)
    const fileLineMatch = remainingText.match(/File\s+["'][^"']*["'],\s+line\s+(\d+),\s+in\s+([A-Za-z0-9_]+)/i);
    let crashedLineNumber: number | undefined;
    let crashedFunctionName: string | undefined;
    if (fileLineMatch && fileLineMatch[1]) {
      crashedLineNumber = parseInt(fileLineMatch[1], 10);
      crashedFunctionName = fileLineMatch[2];
    }

    const crashedSnippet = crashedLineNumber ? getCodeSnippet(crashedLineNumber, 2) : undefined;

    return {
      isStructuredPreflight: false,
      isTraceback: true,
      isRepairExhausted: Boolean(repairAttemptsNotice),
      status: "failed",
      blocking: true,
      issues: [],
      repairAttemptsNotice,
      exceptionType,
      exceptionMessage,
      crashedLineNumber,
      crashedFunctionName,
      crashedSnippet,
      rawDetails: remainingText,
    };
  }

  // 4. Fallback for generic errors
  return {
    isStructuredPreflight: false,
    isTraceback: false,
    isRepairExhausted: Boolean(repairAttemptsNotice),
    status: "failed",
    blocking: true,
    issues: [],
    repairAttemptsNotice,
    exceptionType: "CompilationFailure",
    exceptionMessage: remainingText || "Unknown rendering error",
    rawDetails: remainingText,
  };
}

interface ManimHitlErrorInspectorProps {
  error: string | null;
  sceneCode: string;
  isFixing?: boolean;
  onContinueAnyway?: () => void;
  onFixAutomatically: (errorText: string) => void;
  onEditCode: (targetLine?: number) => void;
  onDismiss?: () => void;
}

export function ManimHitlErrorInspector({
  error,
  sceneCode,
  isFixing = false,
  onContinueAnyway,
  onFixAutomatically,
  onEditCode,
  onDismiss,
}: ManimHitlErrorInspectorProps) {
  const [showRawDetails, setShowRawDetails] = useState(false);
  const [copied, setCopied] = useState(false);

  const diag = useMemo(() => {
    if (!error) return null;
    return parseHitlDiagnostic(error, sceneCode);
  }, [error, sceneCode]);

  if (!diag || !error) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(diag.rawDetails || error);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  const isWarningOnly = diag.status === "warning" && !diag.blocking;

  return (
    <div
      className={cn(
        "rounded-2xl border transition-all duration-200 overflow-hidden shadow-xl backdrop-blur-md",
        isWarningOnly
          ? "border-amber-500/40 bg-gradient-to-b from-amber-500/[0.08] via-zinc-950/90 to-zinc-950 text-amber-200"
          : "border-rose-500/40 bg-gradient-to-b from-rose-500/[0.09] via-zinc-950/90 to-zinc-950 text-rose-200"
      )}
    >
      {/* ── Status Header ── */}
      <div className="p-4 sm:p-5 border-b border-border/40">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div
              className={cn(
                "flex h-9 w-9 items-center justify-center rounded-xl shrink-0 shadow-inner",
                isWarningOnly
                  ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                  : "bg-rose-500/20 text-rose-400 border border-rose-500/30"
              )}
            >
              {isWarningOnly ? (
                <AlertTriangle className="h-5 w-5" />
              ) : (
                <AlertOctagon className="h-5 w-5" />
              )}
            </div>

            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <h4 className="font-semibold text-sm sm:text-base text-foreground tracking-tight">
                  {isWarningOnly
                    ? "Preflight Static Advisory — Review Requested"
                    : diag.isTraceback
                    ? "Manim Execution / Compilation Failed"
                    : "Preflight Check Failed"}
                </h4>
                <Badge
                  variant="outline"
                  className={cn(
                    "text-[10px] font-mono uppercase font-bold tracking-wider px-2 py-0.5",
                    isWarningOnly
                      ? "border-amber-500/50 bg-amber-500/15 text-amber-300"
                      : "border-rose-500/50 bg-rose-500/15 text-rose-300"
                  )}
                >
                  {isWarningOnly ? "Non-Blocking Warning" : "Blocking Error"}
                </Badge>
                {diag.issues.length > 0 && (
                  <Badge variant="secondary" className="text-[10px] font-mono">
                    {diag.issues.length} {diag.issues.length === 1 ? "Issue" : "Issues"}
                  </Badge>
                )}
              </div>

              <p className="text-xs text-muted-foreground leading-relaxed">
                {isWarningOnly
                  ? "Static analysis detected potentially brittle constructs. The code may still execute cleanly in Manim—choose whether to continue anyway, fix automatically, or edit."
                  : diag.isTraceback
                  ? "The Docker Manim compiler halted with a runtime exception. Inspect the root cause below to patch it."
                  : "Syntax or fatal structure errors must be resolved before Manim can render the scene."}
              </p>
            </div>
          </div>

          {onDismiss && (
            <button
              onClick={onDismiss}
              className="text-muted-foreground hover:text-foreground rounded-lg p-1 transition-colors"
              title="Dismiss Notice"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Repair Budget / Timeout Callout */}
        {diag.isRepairExhausted && (
          <div className="mt-3.5 flex items-center gap-2.5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3.5 py-2 text-xs text-amber-200">
            <Sparkles className="h-4 w-4 shrink-0 text-amber-400" />
            <div className="leading-snug">
              <span className="font-semibold">Self-correction loop completed:</span>{" "}
              {diag.repairAttemptsNotice || "Maximum automatic repair budget reached. Human intervention recommended."}
            </div>
          </div>
        )}
      </div>

      {/* ── Body: Structured Preflight Issues or Traceback Summary ── */}
      <div className="p-4 sm:p-5 space-y-3.5 bg-black/30">
        {/* Branch A: Structured Preflight Issues */}
        {diag.isStructuredPreflight && diag.issues.length > 0 ? (
          <div className="space-y-2.5">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center justify-between">
              <span>Diagnostic Findings & Source Context:</span>
              <span className="font-mono text-[10px]">AST Preflight Analyzer</span>
            </div>

            <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
              {diag.issues.map((issue, idx) => {
                const issueIsWarning = issue.severity === "warning";
                const lineContent =
                  issue.line && sceneCode
                    ? sceneCode.split("\n")[issue.line - 1]?.trim()
                    : null;

                return (
                  <div
                    key={idx}
                    className={cn(
                      "rounded-xl border p-3.5 text-xs transition-colors space-y-2 shadow-xs",
                      issueIsWarning
                        ? "border-amber-500/25 bg-amber-500/[0.04] hover:border-amber-500/40"
                        : "border-rose-500/25 bg-rose-500/[0.04] hover:border-rose-500/40"
                    )}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-[10px] font-mono uppercase font-semibold",
                            issueIsWarning
                              ? "border-amber-500/40 text-amber-400 bg-amber-500/10"
                              : "border-rose-500/40 text-rose-400 bg-rose-500/10"
                          )}
                        >
                          {issue.type}
                        </Badge>
                        {issue.line && (
                          <button
                            type="button"
                            onClick={() => onEditCode(issue.line)}
                            className="flex items-center gap-1 font-mono text-[11px] text-primary hover:underline bg-primary/10 px-2 py-0.5 rounded border border-primary/20 transition-colors"
                            title="Click to jump to this line in Code Editor"
                          >
                            <FileCode className="h-3 w-3" />
                            Line {issue.line}
                            {issue.column ? `:${issue.column}` : ""} ↗
                          </button>
                        )}
                      </div>

                      <span
                        className={cn(
                          "text-[10px] font-mono font-bold uppercase",
                          issueIsWarning ? "text-amber-400" : "text-rose-400"
                        )}
                      >
                        {issueIsWarning ? "Advisory" : "Fatal Error"}
                      </span>
                    </div>

                    {/* Offending code line preview */}
                    {lineContent && (
                      <div className="rounded-lg bg-zinc-950/80 border border-zinc-800/80 px-3 py-1.5 font-mono text-[11px] text-zinc-200 overflow-x-auto flex items-center gap-2">
                        <span className="text-zinc-500 select-none">
                          {issue.line} |
                        </span>
                        <code className="text-amber-300 font-semibold">{lineContent}</code>
                      </div>
                    )}

                    {/* Human Explanation */}
                    <p className="text-zinc-300 leading-relaxed font-normal">
                      {issue.message}
                    </p>

                    {/* Actionable Suggestion */}
                    {issue.suggestion && (
                      <div className="flex items-start gap-2 rounded-lg bg-zinc-900/60 border border-zinc-800/60 p-2 text-[11px] text-zinc-400">
                        <Lightbulb className="h-3.5 w-3.5 text-amber-400 shrink-0 mt-0.5" />
                        <div className="leading-snug">
                          <span className="text-amber-300/90 font-medium">Suggestion:</span>{" "}
                          {issue.suggestion}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ) : diag.isTraceback ? (
          /* Branch B: Python Exception Traceback Breakdown */
          <div className="space-y-3">
            <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 space-y-2">
              <div className="flex items-center justify-between text-[11px] uppercase tracking-wider text-rose-400 font-mono font-bold">
                <span>Root Cause Exception:</span>
                {diag.crashedLineNumber && (
                  <button
                    type="button"
                    onClick={() => onEditCode(diag.crashedLineNumber)}
                    className="flex items-center gap-1 text-primary hover:underline bg-primary/10 px-2 py-0.5 rounded border border-primary/20 transition-colors lowercase font-sans font-normal"
                  >
                    <FileCode className="h-3 w-3" />
                    jump to line {diag.crashedLineNumber} ↗
                  </button>
                )}
              </div>

              <div className="font-mono text-xs font-semibold text-rose-200 break-words">
                {diag.exceptionType}: {diag.exceptionMessage}
              </div>

              {diag.crashedFunctionName && (
                <div className="text-[11px] text-zinc-400 font-mono">
                  Location: <span className="text-zinc-200">scene.py</span> • function{" "}
                  <span className="text-primary font-semibold">{diag.crashedFunctionName}()</span>
                  {diag.crashedLineNumber ? ` • line ${diag.crashedLineNumber}` : ""}
                </div>
              )}
            </div>

            {/* Context snippet of crashed code */}
            {diag.crashedSnippet && (
              <div className="space-y-1">
                <div className="text-[11px] font-mono text-zinc-400">Offending Scene Code:</div>
                <pre className="p-3 rounded-xl bg-zinc-950 border border-zinc-800 text-zinc-200 font-mono text-xs overflow-x-auto leading-relaxed">
                  {diag.crashedSnippet}
                </pre>
              </div>
            )}
          </div>
        ) : (
          /* Branch C: Generic Failure Text */
          <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3.5 text-xs font-mono text-zinc-200 whitespace-pre-wrap leading-relaxed">
            {diag.exceptionMessage || diag.rawDetails}
          </div>
        )}

        {/* Collapsible Full Engine Traceback */}
        <div className="pt-1">
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={() => setShowRawDetails(!showRawDetails)}
              className="flex items-center gap-1.5 text-[11px] font-mono text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              {showRawDetails ? (
                <>
                  <ChevronUp className="h-3.5 w-3.5" />
                  Hide Full Engine Logs & Traceback
                </>
              ) : (
                <>
                  <ChevronDown className="h-3.5 w-3.5" />
                  Show Full Engine Logs & Raw Diagnostic Bundle
                </>
              )}
            </button>

            <button
              type="button"
              onClick={handleCopy}
              className="flex items-center gap-1 text-[11px] font-mono text-zinc-400 hover:text-zinc-200 transition-colors"
              title="Copy raw error log to clipboard"
            >
              {copied ? (
                <>
                  <Check className="h-3 w-3 text-emerald-400" />
                  <span className="text-emerald-400">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3" />
                  <span>Copy Log</span>
                </>
              )}
            </button>
          </div>

          {showRawDetails && (
            <pre className="mt-2.5 p-3 rounded-xl bg-black/80 border border-zinc-800 font-mono text-[11px] text-zinc-300 overflow-x-auto max-h-48 whitespace-pre-wrap leading-relaxed shadow-inner">
              {diag.rawDetails}
            </pre>
          )}
        </div>
      </div>

      {/* ── HITL Action Footer: The 3 Choices ── */}
      <div className="p-4 sm:p-5 bg-muted/20 border-t border-border/40 flex flex-wrap items-center justify-between gap-3">
        <div className="text-xs text-muted-foreground flex items-center gap-1.5">
          {isWarningOnly ? (
            <span className="flex items-center gap-1 text-amber-400/90 font-medium">
              <ShieldCheck className="h-3.5 w-3.5" />
              Human Decision: Warnings are non-fatal. You may compile anyway or let the agent refine.
            </span>
          ) : (
            <span className="flex items-center gap-1 text-rose-400/90 font-medium">
              <AlertOctagon className="h-3.5 w-3.5" />
              Human Action: Repair automatically with Manim docs or inspect in the editor.
            </span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Action 1: Continue Anyway (Enabled when non-blocking warnings or user override) */}
          {isWarningOnly && onContinueAnyway && (
            <Button
              type="button"
              size="sm"
              onClick={onContinueAnyway}
              disabled={isFixing}
              className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-semibold gap-1.5 shadow-md shadow-emerald-950/20"
            >
              <Play className="h-3.5 w-3.5" />
              Continue Anyway
            </Button>
          )}

          {/* Action 2: Fix Automatically with Coder Agent */}
          <Button
            type="button"
            size="sm"
            onClick={() => onFixAutomatically(diag.rawDetails || error)}
            disabled={isFixing}
            className={cn(
              "h-8 text-xs font-semibold gap-1.5 text-white shadow-md",
              isWarningOnly
                ? "bg-amber-600 hover:bg-amber-700 shadow-amber-950/20"
                : "bg-primary hover:bg-primary/90 shadow-primary/20"
            )}
          >
            {isFixing ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Repairing with Manim Docs…
              </>
            ) : (
              <>
                <Wand2 className="h-3.5 w-3.5" />
                Fix Automatically
              </>
            )}
          </Button>

          {/* Action 3: Edit Code in Editor */}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onEditCode(diag.crashedLineNumber || diag.issues[0]?.line)}
            disabled={isFixing}
            className="h-8 text-xs gap-1.5 text-foreground hover:bg-muted font-medium"
          >
            <Edit3 className="h-3.5 w-3.5" />
            Edit Code
          </Button>
        </div>
      </div>
    </div>
  );
}
