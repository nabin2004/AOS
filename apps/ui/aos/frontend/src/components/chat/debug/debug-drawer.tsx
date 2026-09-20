"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  Bug,
  Check,
  ChevronDown,
  ChevronRight,
  Copy,
  ExternalLink,
  Filter,
  RefreshCw,
  Search,
  Terminal,
  Trash2,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";

import { useDebugPanelStore } from "@/stores";
import { WS_URL } from "@/lib/constants";
import { cn } from "@/lib/utils";

export function DebugDrawer() {
  const {
    isOpen,
    setOpen,
    activeTab,
    setActiveTab,
    events,
    logs,
    setLogs,
    addLog,
    lastDiagnostic,
    targetEndpoint,
    targetModel,
    logfireUrl,
    clearEvents,
    clearLogs,
  } = useDebugPanelStore();

  const [logLevelFilter, setLogLevelFilter] = useState<string>("ALL");
  const [logSearchQuery, setLogSearchQuery] = useState<string>("");
  const [copiedDiag, setCopiedDiag] = useState<boolean>(false);
  const [expandedLogId, setExpandedLogId] = useState<number | null>(null);
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [isLiveStreaming, setIsLiveStreaming] = useState<boolean>(true);
  const wsStreamRef = useRef<WebSocket | null>(null);
  const logsContainerRef = useRef<HTMLDivElement | null>(null);

  // Poll / stream backend logs over WebSocket when open and on logs tab
  useEffect(() => {
    if (!isOpen) return;

    // Fetch initial logs batch
    const fetchInitialLogs = async () => {
      try {
        const res = await fetch("/api/v1/system/logs?limit=200");
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data.logs)) {
            setLogs(data.logs);
          }
        }
      } catch {
        // Best-effort
      }
    };
    fetchInitialLogs();

    // Connect to log stream
    const baseWs = WS_URL || (typeof window !== "undefined" ? `ws://${window.location.host}` : "ws://localhost:8000");
    const streamWsUrl = `${baseWs}/api/v1/system/logs/stream`;
    try {
      const ws = new WebSocket(streamWsUrl);
      wsStreamRef.current = ws;

      ws.onmessage = (evt) => {
        try {
          const entry = JSON.parse(evt.data);
          addLog(entry);
        } catch {
          // ignore malformed
        }
      };

      ws.onopen = () => setIsLiveStreaming(true);
      ws.onclose = () => setIsLiveStreaming(false);
      ws.onerror = () => setIsLiveStreaming(false);

      return () => {
        ws.close();
        wsStreamRef.current = null;
      };
    } catch {
      setIsLiveStreaming(false);
    }
  }, [isOpen, addLog, setLogs]);

  // Filtered logs
  const filteredLogs = useMemo(() => {
    return logs.filter((entry) => {
      if (logLevelFilter !== "ALL" && entry.level !== logLevelFilter) {
        return false;
      }
      if (logSearchQuery) {
        const q = logSearchQuery.toLowerCase();
        const msgMatch = entry.message?.toLowerCase().includes(q);
        const loggerMatch = entry.logger?.toLowerCase().includes(q);
        const traceMatch = entry.exc_info?.toLowerCase().includes(q);
        if (!msgMatch && !loggerMatch && !traceMatch) return false;
      }
      return true;
    });
  }, [logs, logLevelFilter, logSearchQuery]);

  const handleCopyDiagnostic = () => {
    if (!lastDiagnostic) return;
    const text = JSON.stringify(lastDiagnostic, null, 2);
    navigator.clipboard.writeText(text);
    setCopiedDiag(true);
    setTimeout(() => setCopiedDiag(false), 2000);
  };

  const handleClearServerLogs = async () => {
    clearLogs();
    try {
      await fetch("/api/v1/system/logs", { method: "DELETE" });
    } catch {
      // Best-effort
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-[2px] transition-all">
      <div className="bg-card text-card-foreground border-border flex h-full w-full max-w-2xl flex-col border-l shadow-2xl animate-in slide-in-from-right duration-200 sm:w-[640px]">
        {/* Header */}
        <div className="border-border bg-muted/40 flex items-center justify-between border-b px-5 py-3.5">
          <div className="flex items-center gap-2.5">
            <div className="bg-red-500/10 text-red-500 flex h-8 w-8 items-center justify-center rounded-lg border border-red-500/20">
              <Bug className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold tracking-tight">Live Telemetry & Dev HUD</h2>
                {isLiveStreaming ? (
                  <span className="bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 flex items-center gap-1 rounded-full px-2 py-0.5 font-mono text-[10px] font-medium">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    LIVE
                  </span>
                ) : (
                  <span className="bg-muted text-muted-foreground border flex items-center gap-1 rounded-full px-2 py-0.5 font-mono text-[10px]">
                    OFFLINE
                  </span>
                )}
              </div>
              <p className="text-muted-foreground font-mono text-[11px]">
                Endpoint: <span className="text-foreground">{targetEndpoint || "default"}</span> • Model:{" "}
                <span className="text-foreground">{targetModel || "system"}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <a
              href={logfireUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="bg-secondary text-secondary-foreground hover:bg-secondary/80 inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors"
              title="Open Logfire Distributed Tracing Cloud UI"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              <span>Logfire</span>
            </a>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="hover:bg-muted text-muted-foreground hover:text-foreground rounded-md p-1.5 transition-colors"
              title="Close Dev HUD"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="border-border bg-muted/20 flex items-center justify-between border-b px-5">
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setActiveTab("diagnostics")}
              className={cn(
                "relative border-b-2 px-3 py-2.5 text-xs font-medium transition-colors",
                activeTab === "diagnostics"
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              Diagnostics
              {lastDiagnostic && (
                <span className="bg-red-500 ml-1.5 inline-block h-1.5 w-1.5 rounded-full animate-ping" />
              )}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("events")}
              className={cn(
                "relative border-b-2 px-3 py-2.5 text-xs font-medium transition-colors",
                activeTab === "events"
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              WebSocket Events
              <span className="bg-muted text-muted-foreground ml-1.5 rounded-full px-1.5 py-0.2 font-mono text-[10px]">
                {events.length}
              </span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("logs")}
              className={cn(
                "relative border-b-2 px-3 py-2.5 text-xs font-medium transition-colors",
                activeTab === "logs"
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              Backend Logs
              <span className="bg-muted text-muted-foreground ml-1.5 rounded-full px-1.5 py-0.2 font-mono text-[10px]">
                {logs.length}
              </span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            {activeTab === "events" && events.length > 0 && (
              <button
                type="button"
                onClick={clearEvents}
                className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 text-[11px]"
              >
                <Trash2 className="h-3 w-3" />
                <span>Clear</span>
              </button>
            )}
            {activeTab === "logs" && logs.length > 0 && (
              <button
                type="button"
                onClick={handleClearServerLogs}
                className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 text-[11px]"
              >
                <Trash2 className="h-3 w-3" />
                <span>Clear</span>
              </button>
            )}
          </div>
        </div>

        {/* Tab Body */}
        <div className="flex-1 overflow-y-auto p-5">
          {/* 1. Diagnostics Tab */}
          {activeTab === "diagnostics" && (
            <div className="space-y-4">
              {lastDiagnostic ? (
                <div className="border-red-500/30 bg-red-500/5 space-y-3 rounded-xl border p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="text-red-500 h-5 w-5 shrink-0" />
                      <h3 className="text-sm font-semibold text-red-400">
                        {lastDiagnostic.error_type || "Connection Error"}
                      </h3>
                    </div>
                    <button
                      type="button"
                      onClick={handleCopyDiagnostic}
                      className="border-red-500/20 text-red-400 hover:bg-red-500/10 flex items-center gap-1 rounded border px-2 py-1 font-mono text-[10px] transition-colors"
                    >
                      {copiedDiag ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                      <span>{copiedDiag ? "Copied" : "Copy Report"}</span>
                    </button>
                  </div>

                  <div className="text-foreground/90 text-xs leading-relaxed">
                    {lastDiagnostic.message}
                  </div>

                  {lastDiagnostic.hint && (
                    <div className="bg-card/80 border-border/60 text-muted-foreground rounded-lg border p-3 text-xs">
                      <strong className="text-foreground block mb-1">💡 Troubleshooting Hint:</strong>
                      {lastDiagnostic.hint}
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-2 font-mono text-[11px]">
                    <div className="bg-card/60 border rounded p-2">
                      <span className="text-muted-foreground block text-[10px] uppercase">Target Endpoint</span>
                      <span className="text-foreground break-all">{lastDiagnostic.endpoint || "default"}</span>
                    </div>
                    <div className="bg-card/60 border rounded p-2">
                      <span className="text-muted-foreground block text-[10px] uppercase">Requested Model</span>
                      <span className="text-foreground break-all">{lastDiagnostic.model || "default"}</span>
                    </div>
                  </div>

                  {lastDiagnostic.raw_error && (
                    <details className="text-[11px]">
                      <summary className="text-muted-foreground hover:text-foreground cursor-pointer font-mono text-[10px] uppercase">
                        View Raw Trace / Error
                      </summary>
                      <pre className="bg-black/40 text-red-300 mt-2 max-h-48 overflow-x-auto rounded p-2.5 font-mono text-[10px] leading-tight">
                        {lastDiagnostic.raw_error}
                      </pre>
                    </details>
                  )}
                </div>
              ) : (
                <div className="border-border bg-card flex flex-col items-center justify-center rounded-xl border p-8 text-center">
                  <div className="bg-emerald-500/10 text-emerald-500 mb-3 flex h-10 w-10 items-center justify-center rounded-full">
                    <Wifi className="h-5 w-5" />
                  </div>
                  <h3 className="text-sm font-semibold">No Connection Errors Reported</h3>
                  <p className="text-muted-foreground mt-1 max-w-sm text-xs">
                    All WebSocket turns and LLM calls have completed normally. If an error occurs, detailed diagnostic data will appear here.
                  </p>
                </div>
              )}

              {/* Logfire Information Card */}
              <div className="border-border bg-card space-y-2 rounded-xl border p-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold">Cloud Distributed Tracing (Logfire)</h4>
                  <a
                    href={logfireUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline inline-flex items-center gap-1 text-xs"
                  >
                    <span>View in Logfire</span>
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
                <p className="text-muted-foreground text-xs leading-relaxed">
                  Pydantic Logfire captures full HTTP request payloads, headers, token counts, and execution spans across all agents.
                </p>
                <div className="bg-muted/60 text-muted-foreground rounded p-2 font-mono text-[10px]">
                  Project URL: {logfireUrl}
                </div>
              </div>
            </div>
          )}

          {/* 2. WebSocket Events Tab */}
          {activeTab === "events" && (
            <div className="space-y-2 font-mono text-xs">
              {events.length === 0 ? (
                <div className="text-muted-foreground py-12 text-center text-xs">
                  No WebSocket events captured yet. Send a message to inspect the event stream.
                </div>
              ) : (
                events.map((evt) => {
                  const isExpanded = expandedEventId === evt.id;
                  const isError = evt.type === "error";
                  const isOut = evt.direction === "out";

                  return (
                    <div
                      key={evt.id}
                      className={cn(
                        "border-border rounded-lg border transition-all",
                        isError ? "border-red-500/40 bg-red-500/5" : "bg-card hover:border-foreground/20",
                      )}
                    >
                      <button
                        type="button"
                        onClick={() => setExpandedEventId(isExpanded ? null : evt.id)}
                        className="flex w-full items-center justify-between p-2.5 text-left"
                      >
                        <div className="flex items-center gap-2">
                          {isOut ? (
                            <span className="bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded p-1" title="Outgoing frame">
                              <ArrowUp className="h-3 w-3" />
                            </span>
                          ) : (
                            <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded p-1" title="Incoming frame">
                              <ArrowDown className="h-3 w-3" />
                            </span>
                          )}
                          <span className={cn("font-semibold text-xs", isError ? "text-red-400" : "text-foreground")}>
                            {evt.type}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                          <span>{evt.timestamp}</span>
                          {isExpanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                        </div>
                      </button>

                      {isExpanded && (
                        <div className="border-border/60 bg-muted/20 border-t p-3 text-[11px]">
                          <pre className="max-h-60 overflow-x-auto rounded bg-black/40 p-2 text-foreground/90">
                            {JSON.stringify(evt.data, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          )}

          {/* 3. Backend Logs Tab */}
          {activeTab === "logs" && (
            <div className="space-y-3">
              {/* Filter controls */}
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative flex-1">
                  <Search className="text-muted-foreground absolute left-2.5 top-2.5 h-3.5 w-3.5" />
                  <input
                    type="text"
                    value={logSearchQuery}
                    onChange={(e) => setLogSearchQuery(e.target.value)}
                    placeholder="Search logs, errors, or loggers..."
                    className="border-input bg-background text-foreground placeholder:text-muted-foreground h-8 w-full rounded-md border pl-8 pr-3 text-xs"
                  />
                </div>

                <div className="flex items-center gap-1">
                  {["ALL", "ERROR", "WARNING", "INFO"].map((lvl) => (
                    <button
                      key={lvl}
                      type="button"
                      onClick={() => setLogLevelFilter(lvl)}
                      className={cn(
                        "rounded px-2 py-1 font-mono text-[10px] font-semibold uppercase transition-colors",
                        logLevelFilter === lvl
                          ? "bg-foreground text-background"
                          : "bg-muted text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {lvl}
                    </button>
                  ))}
                </div>
              </div>

              {/* Log List */}
              <div ref={logsContainerRef} className="space-y-1.5 font-mono text-[11px]">
                {filteredLogs.length === 0 ? (
                  <div className="text-muted-foreground py-12 text-center text-xs">
                    No backend logs matching current filter.
                  </div>
                ) : (
                  filteredLogs.map((log) => {
                    const isExpanded = expandedLogId === log.id;
                    const isErr = log.level === "ERROR" || log.level === "CRITICAL";
                    const isWarn = log.level === "WARNING";

                    return (
                      <div
                        key={log.id}
                        className={cn(
                          "border-border rounded border p-2 transition-colors",
                          isErr ? "border-red-500/40 bg-red-500/5 text-red-300" : isWarn ? "border-yellow-500/30 bg-yellow-500/5 text-yellow-300" : "bg-card text-foreground/90",
                        )}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <span
                              className={cn(
                                "rounded px-1.5 py-0.5 text-[9px] font-bold uppercase",
                                isErr
                                  ? "bg-red-500/20 text-red-400"
                                  : isWarn
                                  ? "bg-yellow-500/20 text-yellow-400"
                                  : "bg-muted text-muted-foreground",
                              )}
                            >
                              {log.level}
                            </span>
                            <span className="text-muted-foreground text-[10px] shrink-0">
                              {new Date(log.timestamp).toLocaleTimeString()}
                            </span>
                            <span className="text-foreground/70 truncate text-[10px]">
                              [{log.logger}]
                            </span>
                          </div>

                          {log.exc_info && (
                            <button
                              type="button"
                              onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                              className="text-primary hover:underline text-[10px] shrink-0"
                            >
                              {isExpanded ? "Hide Trace" : "View Trace"}
                            </button>
                          )}
                        </div>

                        <div className="mt-1 break-words leading-tight">{log.message}</div>

                        {isExpanded && log.exc_info && (
                          <pre className="bg-black/60 text-red-200 mt-2 max-h-64 overflow-x-auto rounded p-2 text-[10px] leading-tight">
                            {log.exc_info}
                          </pre>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
