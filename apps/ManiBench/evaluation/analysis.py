#!/usr/bin/env python3
"""
ManiBench Evaluation — Results Analysis & Paper Table Generation
=================================================================
Post-processing of evaluation results for paper presentation.

Generates:
    1. LaTeX tables (model × metric summary, model × problem grid)
    2. CSV exports for plotting
    3. Markdown summary tables
    4. Per-difficulty breakdown
    5. Prompt-strategy comparison (if multi-strategy data available)

Usage:
    python -m evaluation.analysis --results results/results_<run_id>.json
    python -m evaluation.analysis --results-dir results/
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from evaluation.config import RESULTS_DIR


# ══════════════════════════════════════════════════════════════════════════
# Loading
# ══════════════════════════════════════════════════════════════════════════

def load_results(path: Path) -> list[dict]:
    """Load a single results JSON file."""
    with open(path, "r") as f:
        return json.load(f)


def load_results_dir(results_dir: Path) -> list[dict]:
    """Load and merge all results JSON files in a directory."""
    all_results = []
    for p in sorted(results_dir.glob("results_*.json")):
        print(f"Loading {p.name}")
        all_results.extend(load_results(p))
    print(f"Total records: {len(all_results)}")
    return all_results


def load_summary(path: Path) -> dict:
    """Load a summary JSON file."""
    with open(path, "r") as f:
        return json.load(f)


# ══════════════════════════════════════════════════════════════════════════
# Aggregation
# ══════════════════════════════════════════════════════════════════════════

def aggregate_results(results: list[dict]) -> dict:
    """Aggregate raw results into structured summaries."""
    models = sorted(set(r["model"] for r in results))
    problems = sorted(set(r["problem_id"] for r in results))

    # Per-model
    per_model = {}
    for m in models:
        m_results = [r for r in results if r["model"] == m]
        per_model[m] = _agg_scores(m_results)

    # Per-problem
    per_problem = {}
    for p in problems:
        p_results = [r for r in results if r["problem_id"] == p]
        per_problem[p] = _agg_scores(p_results)
        # Add difficulty if available
        for r in p_results:
            if "metrics_detail" in r:
                break

    # Per-difficulty
    difficulty_map: dict[str, list[dict]] = {}
    for r in results:
        # We need to look up difficulty from the records
        d = str(r.get("difficulty", "?"))
        difficulty_map.setdefault(d, []).append(r)
    per_difficulty = {d: _agg_scores(rs) for d, rs in difficulty_map.items()}

    # Grid: model × problem
    grid = {}
    for m in models:
        grid[m] = {}
        for p in problems:
            cell = [r for r in results if r["model"] == m and r["problem_id"] == p]
            grid[m][p] = _agg_scores(cell)

    # Per-strategy (if multiple strategies in results)
    strategies = sorted(set(r.get("strategy", "zero_shot") for r in results))
    per_strategy = {}
    for s in strategies:
        s_results = [r for r in results if r.get("strategy", "zero_shot") == s]
        per_strategy[s] = _agg_scores(s_results)

    return {
        "models": models,
        "problems": problems,
        "strategies": strategies,
        "per_model": per_model,
        "per_problem": per_problem,
        "per_difficulty": per_difficulty,
        "per_strategy": per_strategy,
        "grid": grid,
        "global": _agg_scores(results),
    }


def _agg_scores(records: list[dict]) -> dict:
    """Compute mean ± std for all four metrics."""
    scores = [r["metrics"] for r in records if "metrics" in r]
    n = len(scores)
    if n == 0:
        return {"n": 0, "exec": 0, "vc": 0, "align": 0, "cov": 0}

    exec_vals = [s["executability"] for s in scores]
    vc_vals = [s["version_conflict_rate"] for s in scores]
    align_vals = [s["alignment_score"] for s in scores]
    cov_vals = [s["coverage_score"] for s in scores]

    def mean(vs):
        return sum(vs) / len(vs)

    def std(vs):
        m = mean(vs)
        return (sum((v - m) ** 2 for v in vs) / len(vs)) ** 0.5

    return {
        "n": n,
        "exec_mean": round(mean(exec_vals), 4),
        "exec_std": round(std(exec_vals), 4),
        "vc_mean": round(mean(vc_vals), 4),
        "vc_std": round(std(vc_vals), 4),
        "align_mean": round(mean(align_vals), 4),
        "align_std": round(std(align_vals), 4),
        "cov_mean": round(mean(cov_vals), 4),
        "cov_std": round(std(cov_vals), 4),
    }


# ══════════════════════════════════════════════════════════════════════════
# LaTeX Table Generation
# ══════════════════════════════════════════════════════════════════════════

def generate_latex_model_table(agg: dict) -> str:
    """
    Generate a LaTeX table: rows = models, columns = metrics.
    Paper Table 1: Overall Model Performance on ManiBench.
    """
    lines = [
        r"\begin{table}[ht]",
        r"\centering",
        r"\caption{Overall model performance on ManiBench (mean $\pm$ std, $n=" + str(agg["global"]["n"]) + r"$ total samples).}",
        r"\label{tab:model_performance}",
        r"\begin{tabular}{lcccc}",
        r"\toprule",
        r"\textbf{Model} & \textbf{Exec.} $\uparrow$ & \textbf{VC-Rate} $\downarrow$ & \textbf{Align.} $\uparrow$ & \textbf{Cover.} $\uparrow$ \\",
        r"\midrule",
    ]

    for model in agg["models"]:
        s = agg["per_model"][model]
        lines.append(
            f"  {_latex_escape(model)} & "
            f"${s['exec_mean']:.3f} \\pm {s['exec_std']:.3f}$ & "
            f"${s['vc_mean']:.4f} \\pm {s['vc_std']:.4f}$ & "
            f"${s['align_mean']:.3f} \\pm {s['align_std']:.3f}$ & "
            f"${s['cov_mean']:.3f} \\pm {s['cov_std']:.3f}$ \\\\"
        )

    g = agg["global"]
    lines.extend([
        r"\midrule",
        f"  \\textbf{{Overall}} & "
        f"${g['exec_mean']:.3f} \\pm {g['exec_std']:.3f}$ & "
        f"${g['vc_mean']:.4f} \\pm {g['vc_std']:.4f}$ & "
        f"${g['align_mean']:.3f} \\pm {g['align_std']:.3f}$ & "
        f"${g['cov_mean']:.3f} \\pm {g['cov_std']:.3f}$ \\\\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])

    return "\n".join(lines)


def generate_latex_grid_table(agg: dict, metric: str = "exec") -> str:
    """
    Generate a LaTeX table: rows = models, columns = problems.
    Shows a single metric across the full grid.
    """
    metric_names = {
        "exec": ("Executability", "exec_mean"),
        "vc": ("Version-Conflict Rate", "vc_mean"),
        "align": ("Alignment Score", "align_mean"),
        "cov": ("Coverage Score", "cov_mean"),
    }
    title, key = metric_names.get(metric, ("Executability", "exec_mean"))

    problems = agg["problems"]
    n_cols = len(problems)

    # Short problem IDs for columns
    short_pids = [p.replace("MB-0", "").replace("MB-", "") for p in problems]

    col_spec = "l" + "c" * n_cols
    header_cols = " & ".join([f"\\textbf{{{sp}}}" for sp in short_pids])

    lines = [
        r"\begin{table}[ht]",
        r"\centering",
        r"\small",
        f"\\caption{{{title} grid (model $\\times$ problem).}}",
        f"\\label{{tab:grid_{metric}}}",
        f"\\begin{{tabular}}{{{col_spec}}}",
        r"\toprule",
        f"\\textbf{{Model}} & {header_cols} \\\\",
        r"\midrule",
    ]

    for model in agg["models"]:
        vals = []
        for p in problems:
            cell = agg["grid"][model].get(p, {})
            v = cell.get(key, 0)
            # Color coding: green for good, red for bad
            if metric == "vc":
                color = "green" if v < 0.05 else ("orange" if v < 0.15 else "red")
            else:
                color = "green" if v > 0.7 else ("orange" if v > 0.3 else "red")
            vals.append(f"\\textcolor{{{color}}}{{{v:.2f}}}")
        lines.append(f"  {_latex_escape(model)} & {' & '.join(vals)} \\\\")

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])

    return "\n".join(lines)


def generate_latex_strategy_table(agg: dict) -> str:
    """Generate a LaTeX table comparing prompt strategies."""
    if len(agg["strategies"]) <= 1:
        return "% Only one strategy used — no comparison table."

    lines = [
        r"\begin{table}[ht]",
        r"\centering",
        r"\caption{Prompt strategy comparison on ManiBench.}",
        r"\label{tab:strategy_comparison}",
        r"\begin{tabular}{lcccc}",
        r"\toprule",
        r"\textbf{Strategy} & \textbf{Exec.} $\uparrow$ & \textbf{VC-Rate} $\downarrow$ & \textbf{Align.} $\uparrow$ & \textbf{Cover.} $\uparrow$ \\",
        r"\midrule",
    ]

    for strat in agg["strategies"]:
        s = agg["per_strategy"][strat]
        lines.append(
            f"  {_latex_escape(strat)} & "
            f"${s['exec_mean']:.3f}$ & "
            f"${s['vc_mean']:.4f}$ & "
            f"${s['align_mean']:.3f}$ & "
            f"${s['cov_mean']:.3f}$ \\\\"
        )

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])
    return "\n".join(lines)


def _latex_escape(text: str) -> str:
    """Escape special LaTeX characters."""
    replacements = {
        "_": r"\_",
        "&": r"\&",
        "%": r"\%",
        "#": r"\#",
        "$": r"\$",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


# ══════════════════════════════════════════════════════════════════════════
# CSV Export
# ══════════════════════════════════════════════════════════════════════════

def export_csv(results: list[dict], output_path: Path):
    """Export flat CSV of all results for plotting."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "model", "model_id", "problem_id", "trial", "strategy",
        "executability", "version_conflict_rate", "alignment_score",
        "coverage_score", "latency_s", "code_lines", "error",
    ]

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in results:
            metrics = r.get("metrics", {})
            gen = r.get("generation", {})
            writer.writerow({
                "model": r.get("model", ""),
                "model_id": r.get("model_id", ""),
                "problem_id": r.get("problem_id", ""),
                "trial": r.get("trial", ""),
                "strategy": r.get("strategy", ""),
                "executability": metrics.get("executability", ""),
                "version_conflict_rate": metrics.get("version_conflict_rate", ""),
                "alignment_score": metrics.get("alignment_score", ""),
                "coverage_score": metrics.get("coverage_score", ""),
                "latency_s": gen.get("latency_s", ""),
                "code_lines": gen.get("code_lines", ""),
                "error": r.get("error", ""),
            })

    print(f"CSV exported: {output_path}")


# ══════════════════════════════════════════════════════════════════════════
# Markdown Tables
# ══════════════════════════════════════════════════════════════════════════

def generate_markdown_summary(agg: dict) -> str:
    """Generate full Markdown report of evaluation results."""
    lines = [
        "# ManiBench Evaluation Results",
        "",
        f"**Total samples:** {agg['global']['n']}  ",
        f"**Models:** {', '.join(agg['models'])}  ",
        f"**Problems:** {len(agg['problems'])}  ",
        f"**Strategies:** {', '.join(agg['strategies'])}",
        "",
        "## Overall Model Performance",
        "",
        "| Model | Exec. ↑ | VC-Rate ↓ | Align. ↑ | Cover. ↑ |",
        "|-------|---------|-----------|----------|----------|",
    ]

    for model in agg["models"]:
        s = agg["per_model"][model]
        lines.append(
            f"| {model} | {s['exec_mean']:.3f} ± {s['exec_std']:.3f} | "
            f"{s['vc_mean']:.4f} ± {s['vc_std']:.4f} | "
            f"{s['align_mean']:.3f} ± {s['align_std']:.3f} | "
            f"{s['cov_mean']:.3f} ± {s['cov_std']:.3f} |"
        )

    g = agg["global"]
    lines.append(
        f"| **Overall** | **{g['exec_mean']:.3f}** ± {g['exec_std']:.3f} | "
        f"**{g['vc_mean']:.4f}** ± {g['vc_std']:.4f} | "
        f"**{g['align_mean']:.3f}** ± {g['align_std']:.3f} | "
        f"**{g['cov_mean']:.3f}** ± {g['cov_std']:.3f} |"
    )

    # Per-problem table
    lines.extend([
        "",
        "## Per-Problem Results",
        "",
        "| Problem | Exec. | VC-Rate | Align. | Cover. |",
        "|---------|-------|---------|--------|--------|",
    ])

    for pid in agg["problems"]:
        s = agg["per_problem"][pid]
        lines.append(
            f"| {pid} | {s['exec_mean']:.3f} | {s['vc_mean']:.4f} | "
            f"{s['align_mean']:.3f} | {s['cov_mean']:.3f} |"
        )

    # Strategy comparison
    if len(agg["strategies"]) > 1:
        lines.extend([
            "",
            "## Prompt Strategy Comparison",
            "",
            "| Strategy | Exec. | VC-Rate | Align. | Cover. |",
            "|----------|-------|---------|--------|--------|",
        ])
        for strat in agg["strategies"]:
            s = agg["per_strategy"][strat]
            lines.append(
                f"| {strat} | {s['exec_mean']:.3f} | {s['vc_mean']:.4f} | "
                f"{s['align_mean']:.3f} | {s['cov_mean']:.3f} |"
            )

    lines.append("")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="ManiBench Results Analysis — Paper Table Generator",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--results", type=str,
        help="Path to a single results JSON file",
    )
    group.add_argument(
        "--results-dir", type=str,
        help="Path to a directory with results_*.json files",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Output directory for generated tables (default: results/analysis/)",
    )
    args = parser.parse_args()

    # Load results
    if args.results:
        results = load_results(Path(args.results))
    else:
        results = load_results_dir(Path(args.results_dir))

    if not results:
        print("ERROR: No results found.")
        sys.exit(1)

    # Output directory
    out_dir = Path(args.output_dir) if args.output_dir else RESULTS_DIR / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Aggregate
    agg = aggregate_results(results)

    # ── Generate all outputs ──

    # 1. LaTeX tables
    latex_model = generate_latex_model_table(agg)
    (out_dir / "table_model_performance.tex").write_text(latex_model)
    print(f"✓ LaTeX model table → {out_dir / 'table_model_performance.tex'}")

    for metric in ["exec", "vc", "align", "cov"]:
        latex_grid = generate_latex_grid_table(agg, metric)
        fname = f"table_grid_{metric}.tex"
        (out_dir / fname).write_text(latex_grid)
        print(f"✓ LaTeX grid ({metric}) → {out_dir / fname}")

    latex_strategy = generate_latex_strategy_table(agg)
    (out_dir / "table_strategy_comparison.tex").write_text(latex_strategy)
    print(f"✓ LaTeX strategy table → {out_dir / 'table_strategy_comparison.tex'}")

    # 2. CSV export
    csv_path = out_dir / "results_flat.csv"
    export_csv(results, csv_path)

    # 3. Markdown summary
    md_report = generate_markdown_summary(agg)
    md_path = out_dir / "evaluation_report.md"
    md_path.write_text(md_report)
    print(f"✓ Markdown report → {md_path}")

    # 4. Aggregated JSON
    agg_path = out_dir / "aggregated_results.json"
    with open(agg_path, "w") as f:
        json.dump(agg, f, indent=2, default=str)
    print(f"✓ Aggregated JSON → {agg_path}")

    print(f"\n✓ Analysis complete. All outputs in: {out_dir}")

    # Print tables to console
    print("\n" + "=" * 60)
    print("LATEX TABLE — Model Performance:")
    print("=" * 60)
    print(latex_model)

    print("\n" + "=" * 60)
    print("MARKDOWN REPORT:")
    print("=" * 60)
    print(md_report)


if __name__ == "__main__":
    main()
