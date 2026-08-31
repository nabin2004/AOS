"use client";

import React, { useEffect, useState } from "react";
import { Brain, RefreshCw, Sparkles, X, Database, Network } from "lucide-react";
import { Button } from "@/components/ui";

interface MemoryNode {
  id: string;
  name?: string;
  type?: string;
  concept?: string;
  summary?: string;
}

interface MemoryEdge {
  source: string;
  target: string;
  relation?: string;
}

interface MemoryData {
  nodes?: MemoryNode[];
  edges?: MemoryEdge[];
  concepts?: Record<string, any>;
  facts?: string[];
}

export function MemoryDrawer({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [data, setData] = useState<MemoryData | null>(null);
  const [loading, setLoading] = useState(false);
  const [curating, setCurating] = useState(false);

  const fetchMemory = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/educlaw/memory");
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch (e) {
      console.error("Failed to fetch memory graph", e);
    } finally {
      setLoading(false);
    }
  };

  const handleCurate = async () => {
    setCurating(true);
    try {
      const res = await fetch("/api/v1/educlaw/memory/curate", { method: "POST" });
      if (res.ok) {
        await fetchMemory();
      }
    } catch (e) {
      console.error("Failed to curate memory", e);
    } finally {
      setCurating(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchMemory();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const nodes = data?.nodes || [];
  const edges = data?.edges || [];

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-96 border-l border-border bg-background/95 p-4 shadow-2xl backdrop-blur-md flex flex-col">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div className="flex items-center gap-2">
          <Brain className="h-5 w-5 text-indigo-400" />
          <h2 className="font-semibold text-foreground">Dagestan Graph Memory</h2>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={fetchMemory} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex items-center justify-between py-2 border-b border-border/40 text-xs text-muted-foreground">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <Database className="h-3.5 w-3.5 text-indigo-400" />
            {nodes.length} Nodes
          </span>
          <span className="flex items-center gap-1">
            <Network className="h-3.5 w-3.5 text-sky-400" />
            {edges.length} Edges
          </span>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs gap-1 border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/10"
          onClick={handleCurate}
          disabled={curating}
        >
          <Sparkles className="h-3 w-3" />
          {curating ? "Curating..." : "Curate Memory"}
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto pt-3 space-y-3">
        {nodes.length === 0 ? (
          <div className="py-12 text-center text-xs text-muted-foreground">
            No memories extracted yet in this workspace. Run a few turns with EduClaw to seed the graph.
          </div>
        ) : (
          nodes.map((node, idx) => (
            <div
              key={node.id || idx}
              className="rounded-lg border border-border/60 bg-muted/20 p-2.5 text-xs transition hover:border-indigo-500/40"
            >
              <div className="flex items-center justify-between font-mono font-medium text-foreground">
                <span className="text-indigo-300">{node.name || node.concept || node.id}</span>
                {node.type && (
                  <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                    {node.type}
                  </span>
                )}
              </div>
              {node.summary && (
                <p className="mt-1 text-[11px] text-muted-foreground line-clamp-3">
                  {node.summary}
                </p>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
