import { Bot, CheckCircle2, Code2, Cpu, FileText, Search, Sparkles, User, Video } from "lucide-react";

import { cn } from "@/lib/utils";

type MockupKind = "agents" | "rag" | "billing";

interface FeatureMockupProps {
  kind: MockupKind;
  className?: string;
}

/** Stylized mini-UIs that showcase AOS capabilities: Agent graph, EduClaw RAG, and Docker Render Engine. */
export function FeatureMockup({ kind, className }: FeatureMockupProps) {
  if (kind === "agents") return <AgentMockup className={className} />;
  if (kind === "rag") return <RagMockup className={className} />;
  return <RenderMetricsMockup className={className} />;
}

function MockFrame({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "border-foreground/15 bg-card relative w-full max-w-lg overflow-hidden rounded-2xl border shadow-2xl",
        className,
      )}
    >
      <div className="border-foreground/10 flex items-center gap-1.5 border-b px-4 py-2.5">
        <span className="bg-foreground/20 h-2 w-2 rounded-full" />
        <span className="bg-foreground/20 h-2 w-2 rounded-full" />
        <span className="bg-foreground/20 h-2 w-2 rounded-full" />
      </div>
      {children}
    </div>
  );
}

function AgentMockup({ className }: { className?: string }) {
  return (
    <MockFrame className={className}>
      <div className="space-y-3 p-4">
        <div className="flex justify-end">
          <div className="bg-foreground text-background flex max-w-[85%] items-center gap-2 rounded-2xl rounded-tr-sm px-3.5 py-2 text-xs">
            <span>Synthesize Fourier Epicycles animation with LaTeX MathTex.</span>
            <User className="h-3.5 w-3.5 opacity-60" />
          </div>
        </div>

        <div className="flex">
          <div className="border-brand/40 bg-brand/15 flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[10px]">
            <Cpu className="h-3 w-3 text-brand" />
            <span className="text-foreground/80">aos.pipeline · Storyboard → Beats (4 scenes)</span>
          </div>
        </div>

        <div className="flex">
          <div className="bg-card border-foreground/10 max-w-[92%] rounded-2xl rounded-tl-sm border p-3.5">
            <div className="text-foreground/55 mb-2 flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Code2 className="h-3.5 w-3.5 text-brand" />
                <span className="font-mono text-[10px] tracking-wider uppercase">lecture.py (Compiled)</span>
              </div>
              <span className="text-[10px] font-mono text-emerald-500 flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" /> Validated
              </span>
            </div>
            <pre className="font-mono text-[11px] leading-relaxed text-foreground/85 bg-foreground/5 p-2 rounded-lg overflow-x-auto">
              {`c = Circle(radius=1.8, color=BLUE)\narrow = Arrow(ORIGIN, c.point_at_angle(PI/4))\nself.play(Create(c), GrowArrow(arrow))\nself.play(Transform(formula, next_tex))`}
            </pre>
          </div>
        </div>

        <div className="border-foreground/10 mt-2 flex items-center gap-2 rounded-lg border px-3 py-2">
          <Sparkles className="text-foreground/40 h-3.5 w-3.5" />
          <span className="text-foreground/40 flex-1 text-xs">Add animation beat or narration...</span>
          <kbd className="border-foreground/15 text-foreground/50 inline-flex items-center gap-0.5 rounded border px-1.5 py-0.5 font-mono text-[10px]">
            ⌘ ↵
          </kbd>
        </div>
      </div>
    </MockFrame>
  );
}

function RagMockup({ className }: { className?: string }) {
  const RESULTS = [
    {
      title: "fourier_analysis_stein.pdf",
      snippet: "...complex exponentials form an orthonormal basis on L2(T)...",
      score: 0.98,
    },
    {
      title: "linear_algebra_strang.md",
      snippet: "...orthogonal projection translates directly into visual epicycle rotations...",
      score: 0.94,
    },
    {
      title: "quantum_pedagogy_notes.docx",
      snippet: "...visualize phase angles in the complex plane before continuous transforms...",
      score: 0.89,
    },
  ];
  return (
    <MockFrame className={className}>
      <div className="p-4">
        <div className="border-foreground/10 mb-3 flex items-center gap-2 rounded-lg border px-3 py-2">
          <Search className="text-foreground/40 h-3.5 w-3.5" />
          <span className="text-foreground text-xs font-mono">EduClaw: orthogonality of basis functions</span>
        </div>
        <ul className="space-y-2.5">
          {RESULTS.map((r) => (
            <li key={r.title} className="border-foreground/10 rounded-lg border p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <FileText className="text-foreground/50 h-3 w-3" />
                  <span className="text-foreground font-mono text-[11px]">{r.title}</span>
                </div>
                <span className="bg-brand text-brand-foreground rounded-full px-1.5 py-0.5 font-mono text-[10px] tabular-nums">
                  {r.score.toFixed(2)}
                </span>
              </div>
              <p className="text-foreground/65 mt-1.5 text-[11px] leading-snug">{r.snippet}</p>
            </li>
          ))}
        </ul>
      </div>
    </MockFrame>
  );
}

function RenderMetricsMockup({ className }: { className?: string }) {
  const bars = [35, 42, 50, 48, 62, 70, 78, 85, 80, 92, 95, 100];
  const max = Math.max(...bars);
  return (
    <MockFrame className={className}>
      <div className="space-y-4 p-4">
        <div>
          <p className="text-foreground/55 font-mono text-[10px] tracking-wider uppercase">
            Manim Docker Engine
          </p>
          <p className="text-foreground font-display mt-1 text-3xl font-bold tracking-tight">
            60 FPS
          </p>
          <p className="text-brand mt-0.5 flex items-center gap-1 text-xs font-medium">
            <Video className="h-3 w-3" />
            1080p & 4K · 14.2s render time
          </p>
        </div>

        <div className="flex h-20 items-end gap-1">
          {bars.map((b, i) => (
            <div
              key={i}
              className="bg-foreground/15 flex-1 rounded-sm"
              style={{ height: `${(b / max) * 100}%` }}
            >
              <div
                className="bg-brand h-1 w-full"
                style={{ display: i === bars.length - 1 ? "block" : "none" }}
              />
            </div>
          ))}
        </div>

        <div className="border-foreground/10 grid grid-cols-3 gap-2 border-t pt-3">
          <div>
            <p className="text-foreground/45 font-mono text-[10px] uppercase">Renders</p>
            <p className="text-foreground font-mono text-sm font-medium">1,420</p>
          </div>
          <div>
            <p className="text-foreground/45 font-mono text-[10px] uppercase">Cache Hit</p>
            <p className="text-foreground font-mono text-sm font-medium">94.2%</p>
          </div>
          <div>
            <p className="text-foreground/45 font-mono text-[10px] uppercase">Sync Acc</p>
            <p className="text-foreground font-mono text-sm font-medium">99.8%</p>
          </div>
        </div>
      </div>
    </MockFrame>
  );
}
