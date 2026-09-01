#!/usr/bin/env python3
"""
ManiBench Evaluation Runner
==============================
Main entry point for running the full evaluation pipeline.

Usage:
    # Full evaluation (all models × all problems × 3 trials)
    python -m evaluation.run

    # Single model, specific problems
    python -m evaluation.run --models gpt-4o --problems MB-001 MB-002

    # Specific strategy, skip rendering
    python -m evaluation.run --strategy cot --skip-render

    # Quick test run (1 trial)
    python -m evaluation.run --trials 1 --models claude-sonnet-4 --problems MB-001

    # OpenAI-compatible / vLLM endpoint
    python -m evaluation.run --provider openai \\
        --base-url http://localhost:8000/v1 \\
        --models Qwen/Qwen2.5-Coder-7B-Instruct --trials 1

Environment:
    OPENROUTER_API_KEY — required for --provider openrouter (or pass --api-key)
    OPENROUTER_BASE_URL — optional OpenRouter base URL override
    INFERENCE_API_KEY  — required for --provider inference (or pass --api-key)
    OPENAI_BASE_URL    — base URL for --provider openai (or use --base-url)
    OPENAI_API_KEY     — optional for --provider openai (or pass --api-key)
"""

import argparse
import json
import os
import re
import sys
import time
import traceback
from pathlib import Path

from evaluation.config import (
    DATASET_PATH,
    DEFAULT_MODELS,
    INFERENCE_API_KEY,
    INFERENCE_MODELS,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    SUPPORTED_PROVIDERS,
    EvalConfig,
    GENERATED_CODE_DIR,
    ModelSpec,
    RESULTS_DIR,
    get_model_by_short_name,
    get_models_for_provider,
)
from evaluation.logger import StructuredLogger
from evaluation.openrouter_client import OpenRouterClient, OpenRouterError
from evaluation.inference_client import InferenceNetClient, InferenceNetError
from evaluation.openai_client import OpenAICompatibleClient, OpenAICompatibleError
from evaluation.prompts import build_messages
from evaluation.metrics import (
    compute_executability,
    detect_version_conflicts,
    detect_specific_conflicts,
    compute_alignment,
    compute_coverage,
)


def load_dataset(path: str | Path) -> list[dict]:
    """Load and validate the ManiBench dataset JSON."""
    path = Path(path)
    if not path.exists():
        print(f"ERROR: Dataset not found at {path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    problems = data.get("problems", [])
    print(f"Loaded {len(problems)} problems from {path.name}")
    return problems


def filter_problems(problems: list[dict], ids: list[str] | None) -> list[dict]:
    """Filter problems by ID list (None = all)."""
    if ids is None:
        return problems
    id_set = set(ids)
    filtered = [p for p in problems if p["id"] in id_set]
    missing = id_set - {p["id"] for p in filtered}
    if missing:
        print(f"WARNING: problems not found: {missing}")
    return filtered


def _filesystem_safe_name(name: str) -> str:
    """Turn a served model id into a safe short_name for dirs/filenames."""
    safe = re.sub(r"[^\w.\-]+", "-", name.strip())
    safe = re.sub(r"-+", "-", safe).strip("-")
    return safe or "model"


def resolve_models(names: list[str] | None, provider: str = "openrouter"):
    """Resolve model short names to ModelSpec objects."""
    # OpenAI-compatible: CLI names are the served model IDs (no fixed roster)
    if provider == "openai":
        if not names:
            print("ERROR: --models is required for --provider openai "
                  "(pass the served model id(s), e.g. Qwen/Qwen2.5-7B-Instruct).")
            sys.exit(1)
        return [
            ModelSpec(
                id=name,
                short_name=_filesystem_safe_name(name),
                provider="OpenAI-compatible",
            )
            for name in names
        ]

    roster = get_models_for_provider(provider)
    if names is None:
        return roster
    models = []
    for name in names:
        m = get_model_by_short_name(name, provider=provider)
        if m is None:
            print(f"WARNING: unknown model '{name}' for provider '{provider}', skipping. "
                  f"Available: {[m.short_name for m in roster]}")
        else:
            models.append(m)
    if not models:
        print(f"ERROR: no valid models specified for provider '{provider}'.")
        sys.exit(1)
    return models


def create_client(config: EvalConfig):
    """Factory: return the right API client for the chosen provider."""
    if config.provider == "inference":
        return InferenceNetClient(api_key=config.api_key or None)
    if config.provider == "openai":
        return OpenAICompatibleClient(
            base_url=config.base_url or OPENAI_BASE_URL,
            api_key=config.api_key if config.api_key is not None else (OPENAI_API_KEY or None),
        )
    return OpenRouterClient(
        api_key=config.api_key or None,
        base_url=config.base_url or OPENROUTER_BASE_URL,
    )


def save_generated_code(code: str, model_name: str, problem_id: str,
                        trial: int, strategy: str) -> Path:
    """Persist generated code to disk for inspection."""
    out_dir = GENERATED_CODE_DIR / model_name / strategy
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{problem_id}_trial{trial}.py"
    out_path = out_dir / filename
    out_path.write_text(code, encoding="utf-8")
    return out_path


def compute_all_metrics(
    code: str,
    problem: dict,
    skip_render: bool = False,
    manim_timeout: int = 60,
) -> dict:
    """Run all four metrics on a generated code sample."""

    # 1. Executability
    exec_result = compute_executability(
        code,
        timeout=manim_timeout,
        skip_render=skip_render,
    )

    # 2. Version-Conflict Error Rate
    vc_result = detect_version_conflicts(code)

    # Check problem-specific conflicts
    known_incompat = []
    vcn = problem.get("version_conflict_notes", {})
    if isinstance(vcn, dict):
        known_incompat = vcn.get("known_incompatibilities", [])
    vc_specific = detect_specific_conflicts(code, known_incompat)

    # 3. Alignment Score
    required_events = problem.get("required_visual_events", [])
    align_result = compute_alignment(code, required_events)

    # 4. Coverage Score
    coverage_reqs = problem.get("coverage_requirements", [])
    cov_result = compute_coverage(code, coverage_reqs)

    return {
        "executability": exec_result,
        "version_conflict": {
            **vc_result,
            "problem_specific": vc_specific,
        },
        "alignment": align_result,
        "coverage": cov_result,
        # Summary scalars (for quick aggregation)
        "_scores": {
            "executability": exec_result.get("executability", 0),
            "version_conflict_rate": vc_result.get("version_conflict_rate", 1.0),
            "alignment_score": align_result.get("alignment_score", 0.0),
            "coverage_score": cov_result.get("coverage_score", 0.0),
        },
    }


def run_evaluation(config: EvalConfig):
    """Execute the full evaluation loop."""

    # ── Load dataset ──
    problems = load_dataset(DATASET_PATH)
    problems = filter_problems(problems, config.problems)
    models = resolve_models(config.models, provider=config.provider)

    total_calls = len(models) * len(problems) * config.trials
    print(f"\n{'='*60}")
    print(f"ManiBench Evaluation")
    print(f"{'='*60}")
    print(f"Provider:  {config.provider}")
    if config.provider == "openai" and config.base_url:
        print(f"Base URL:  {config.base_url}")
    print(f"Models:    {[m.short_name for m in models]}")
    print(f"Problems:  {[p['id'] for p in problems]}")
    print(f"Trials:    {config.trials}")
    print(f"Strategy:  {config.prompt_strategy}")
    print(f"Total API calls: {total_calls}")
    print(f"Skip render: {config.skip_render}")
    print(f"Manim timeout: {config.manim_timeout}s")
    print(f"{'='*60}\n")

    if not config.skip_render:
        try:
            import manim  # noqa: F401
            print(f"Manim preflight: OK ({manim.__version__})")
        except ImportError as e:
            print("ERROR: Manim is not importable in this interpreter.")
            print("  Executability requires a real render when --skip-render is not set.")
            print("  Install with: uv pip install -r requirements.txt")
            print(f"  Details: {e}")
            sys.exit(1)

    # ── Initialize components ──
    client = create_client(config)
    logger = StructuredLogger()

    # Log configuration
    logger.log_run_config({
        "provider": config.provider,
        "base_url": config.base_url,
        "models": [m.short_name for m in models],
        "model_ids": [m.id for m in models],
        "problems": [p["id"] for p in problems],
        "trials": config.trials,
        "prompt_strategy": config.prompt_strategy,
        "skip_render": config.skip_render,
        "manim_timeout": config.manim_timeout,
        "seed": config.seed,
    })

    # ── Results accumulator ──
    all_results: list[dict] = []
    call_counter = 0

    for model in models:
        print(f"\n{'─'*50}")
        print(f"Model: {model.short_name} ({model.id})")
        print(f"{'─'*50}")

        for problem in problems:
            pid = problem["id"]
            difficulty = problem.get("difficulty", "?")
            print(f"\n  Problem {pid} (difficulty {difficulty})")

            for trial in range(1, config.trials + 1):
                call_counter += 1
                print(f"    Trial {trial}/{config.trials} "
                      f"[{call_counter}/{total_calls}] ... ", end="", flush=True)

                record = {
                    "model": model.short_name,
                    "model_id": model.id,
                    "problem_id": pid,
                    "trial": trial,
                    "strategy": config.prompt_strategy,
                }

                try:
                    # ── Generate code ──
                    messages = build_messages(problem, config.prompt_strategy)
                    gen_start = time.time()
                    result = client.generate(
                        model=model,
                        messages=messages,
                        max_tokens=model.max_tokens,
                        temperature=model.temperature,
                    )
                    gen_time = time.time() - gen_start

                    code = result.get("code", "")
                    record["generation"] = {
                        "latency_s": round(gen_time, 2),
                        "prompt_tokens": result.get("prompt_tokens", 0),
                        "completion_tokens": result.get("completion_tokens", 0),
                        "code_length": len(code),
                        "code_lines": len(code.split("\n")) if code else 0,
                    }

                    # Save generated code
                    if code:
                        code_path = save_generated_code(
                            code, model.short_name, pid, trial,
                            config.prompt_strategy,
                        )
                        record["code_path"] = str(code_path)

                        # Log generation
                        logger.log_generation(
                            model=model.short_name,
                            problem_id=pid,
                            trial=trial,
                            prompt_strategy=config.prompt_strategy,
                            prompt_tokens=result.get("prompt_tokens", 0),
                            completion_tokens=result.get("completion_tokens", 0),
                            latency_ms=result.get("latency_ms", gen_time * 1000),
                            code=code,
                        )

                        # ── Compute metrics ──
                        metrics = compute_all_metrics(
                            code, problem,
                            skip_render=config.skip_render,
                            manim_timeout=config.manim_timeout,
                        )
                        record["metrics"] = metrics["_scores"]
                        record["metrics_detail"] = {
                            k: v for k, v in metrics.items() if k != "_scores"
                        }

                        # Log metrics + Manim subprocess output
                        logger.log_metrics(
                            model=model.short_name,
                            problem_id=pid,
                            trial=trial,
                            metrics=metrics["_scores"],
                        )
                        exec_detail = metrics.get("executability", {})
                        logger.log_render(
                            model=model.short_name,
                            problem_id=pid,
                            trial=trial,
                            exec_detail=exec_detail,
                        )

                        scores = metrics["_scores"]
                        exec_sym = "✓" if scores["executability"] == 1 else "✗"
                        dur = exec_detail.get("render_duration_s", 0.0)
                        rc = exec_detail.get("returncode")
                        err = exec_detail.get("error_type") or "-"
                        print(f"{exec_sym}  exec={scores['executability']} "
                              f"vc={scores['version_conflict_rate']:.3f} "
                              f"align={scores['alignment_score']:.3f} "
                              f"cov={scores['coverage_score']:.3f} "
                              f"render={dur}s rc={rc} error={err} "
                              f"({gen_time:.1f}s gen)")
                    else:
                        record["error"] = "empty_code"
                        record["metrics"] = {
                            "executability": 0,
                            "version_conflict_rate": 1.0,
                            "alignment_score": 0.0,
                            "coverage_score": 0.0,
                        }
                        print("✗  (empty code)")

                except (OpenRouterError, InferenceNetError, OpenAICompatibleError) as e:
                    record["error"] = str(e)
                    record["metrics"] = {
                        "executability": 0,
                        "version_conflict_rate": 1.0,
                        "alignment_score": 0.0,
                        "coverage_score": 0.0,
                    }
                    print(f"✗  API error: {e}")

                except Exception as e:
                    record["error"] = traceback.format_exc()
                    record["metrics"] = {
                        "executability": 0,
                        "version_conflict_rate": 1.0,
                        "alignment_score": 0.0,
                        "coverage_score": 0.0,
                    }
                    print(f"✗  Error: {e}")

                all_results.append(record)

    # ── Save & summarize ──
    print(f"\n{'='*60}")
    print(f"Evaluation complete: {len(all_results)} records")
    print(f"{'='*60}")

    # Save raw results
    results_path = RESULTS_DIR / f"results_{logger.run_id}.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"Raw results saved: {results_path}")

    # Generate summary
    summary = _build_summary(all_results, models, problems, config)
    logger.save_summary(summary)

    _print_summary_table(summary)

    return all_results, summary


def _build_summary(
    results: list[dict],
    models,
    problems: list[dict],
    config: EvalConfig,
) -> dict:
    """Aggregate results into paper-ready summary tables."""

    # Per-model aggregation
    model_agg: dict[str, dict] = {}
    for m in models:
        model_results = [r for r in results if r["model"] == m.short_name]
        if not model_results:
            continue
        scores = [r["metrics"] for r in model_results if "metrics" in r]
        n = len(scores)
        model_agg[m.short_name] = {
            "n_samples": n,
            "executability_mean": sum(s["executability"] for s in scores) / max(n, 1),
            "version_conflict_mean": sum(s["version_conflict_rate"] for s in scores) / max(n, 1),
            "alignment_mean": sum(s["alignment_score"] for s in scores) / max(n, 1),
            "coverage_mean": sum(s["coverage_score"] for s in scores) / max(n, 1),
        }

    # Per-problem aggregation
    problem_agg: dict[str, dict] = {}
    for p in problems:
        pid = p["id"]
        prob_results = [r for r in results if r["problem_id"] == pid]
        scores = [r["metrics"] for r in prob_results if "metrics" in r]
        n = len(scores)
        problem_agg[pid] = {
            "n_samples": n,
            "difficulty": p.get("difficulty", "?"),
            "executability_mean": sum(s["executability"] for s in scores) / max(n, 1),
            "version_conflict_mean": sum(s["version_conflict_rate"] for s in scores) / max(n, 1),
            "alignment_mean": sum(s["alignment_score"] for s in scores) / max(n, 1),
            "coverage_mean": sum(s["coverage_score"] for s in scores) / max(n, 1),
        }

    # Per-(model, problem) grid
    grid: dict[str, dict[str, dict]] = {}
    for m in models:
        grid[m.short_name] = {}
        for p in problems:
            pid = p["id"]
            cell_results = [
                r for r in results
                if r["model"] == m.short_name and r["problem_id"] == pid
            ]
            scores = [r["metrics"] for r in cell_results if "metrics" in r]
            n = len(scores)
            grid[m.short_name][pid] = {
                "n": n,
                "exec": sum(s["executability"] for s in scores) / max(n, 1),
                "vc": sum(s["version_conflict_rate"] for s in scores) / max(n, 1),
                "align": sum(s["alignment_score"] for s in scores) / max(n, 1),
                "cov": sum(s["coverage_score"] for s in scores) / max(n, 1),
            }

    # Global aggregate
    all_scores = [r["metrics"] for r in results if "metrics" in r]
    n_all = len(all_scores)
    global_agg = {
        "n_samples": n_all,
        "executability_mean": sum(s["executability"] for s in all_scores) / max(n_all, 1),
        "version_conflict_mean": sum(s["version_conflict_rate"] for s in all_scores) / max(n_all, 1),
        "alignment_mean": sum(s["alignment_score"] for s in all_scores) / max(n_all, 1),
        "coverage_mean": sum(s["coverage_score"] for s in all_scores) / max(n_all, 1),
    }

    return {
        "config": {
            "strategy": config.prompt_strategy,
            "trials": config.trials,
            "n_models": len(models),
            "n_problems": len(problems),
        },
        "global": global_agg,
        "per_model": model_agg,
        "per_problem": problem_agg,
        "grid": grid,
    }


def _print_summary_table(summary: dict):
    """Print a nice ASCII summary table."""
    print(f"\n{'='*80}")
    print("SUMMARY — Per-Model Averages")
    print(f"{'='*80}")
    print(f"{'Model':<20} {'N':>4}  {'Exec':>6}  {'VC-Rate':>8}  {'Align':>7}  {'Cover':>7}")
    print(f"{'─'*20} {'─'*4}  {'─'*6}  {'─'*8}  {'─'*7}  {'─'*7}")

    for model_name, agg in summary["per_model"].items():
        print(f"{model_name:<20} {agg['n_samples']:>4}  "
              f"{agg['executability_mean']:>6.3f}  "
              f"{agg['version_conflict_mean']:>8.4f}  "
              f"{agg['alignment_mean']:>7.3f}  "
              f"{agg['coverage_mean']:>7.3f}")

    g = summary["global"]
    print(f"{'─'*20} {'─'*4}  {'─'*6}  {'─'*8}  {'─'*7}  {'─'*7}")
    print(f"{'OVERALL':<20} {g['n_samples']:>4}  "
          f"{g['executability_mean']:>6.3f}  "
          f"{g['version_conflict_mean']:>8.4f}  "
          f"{g['alignment_mean']:>7.3f}  "
          f"{g['coverage_mean']:>7.3f}")

    print(f"\n{'='*80}")
    print("SUMMARY — Per-Problem Averages")
    print(f"{'='*80}")
    print(f"{'Problem':<10} {'Diff':>4} {'N':>4}  {'Exec':>6}  {'VC-Rate':>8}  {'Align':>7}  {'Cover':>7}")
    print(f"{'─'*10} {'─'*4} {'─'*4}  {'─'*6}  {'─'*8}  {'─'*7}  {'─'*7}")

    for pid, agg in summary["per_problem"].items():
        print(f"{pid:<10} {str(agg['difficulty']):>4} {agg['n_samples']:>4}  "
              f"{agg['executability_mean']:>6.3f}  "
              f"{agg['version_conflict_mean']:>8.4f}  "
              f"{agg['alignment_mean']:>7.3f}  "
              f"{agg['coverage_mean']:>7.3f}")

    print()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="ManiBench Evaluation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m evaluation.run
  python -m evaluation.run --api-key sk-or-v1-... --models claude-sonnet-4 --trials 1
  python -m evaluation.run --models gpt-4o claude-sonnet-4 --trials 1
  python -m evaluation.run --strategy cot --problems MB-001 MB-002 MB-003
  python -m evaluation.run --skip-render --models deepseek-r1
  python -m evaluation.run --provider openai --base-url http://localhost:8000/v1 \\
      --models Qwen/Qwen2.5-Coder-7B-Instruct --problems MB-001 --trials 1
        """,
    )
    parser.add_argument(
        "--models", nargs="+", default=None,
        help="Model short names (default: all for openrouter/inference). "
             "For --provider openai, pass served model id(s) "
             "(e.g. Qwen/Qwen2.5-Coder-7B-Instruct).",
    )
    parser.add_argument(
        "--problems", nargs="+", default=None,
        help="Problem IDs to evaluate (default: all). E.g., MB-001 MB-005",
    )
    parser.add_argument(
        "--trials", type=int, default=3,
        help="Number of trials per (model, problem) pair (default: 3)",
    )
    parser.add_argument(
        "--strategy", type=str, default="zero_shot",
        choices=["zero_shot", "few_shot", "cot", "constraint", "version_aware"],
        help="Prompt strategy (default: zero_shot)",
    )
    parser.add_argument(
        "--skip-render", action="store_true",
        help="Skip Manim rendering (syntax + static analysis only)",
    )
    parser.add_argument(
        "--timeout", type=int, default=60,
        help="Manim render timeout in seconds (default: 60)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--provider", type=str, default="openrouter",
        choices=SUPPORTED_PROVIDERS,
        help="API provider: openrouter (default), inference, or openai "
             "(OpenAI-compatible / vLLM)",
    )
    parser.add_argument(
        "--base-url", type=str, default=None,
        help="API base URL. For openai: required (or OPENAI_BASE_URL). "
             "For openrouter: optional override of OPENROUTER_BASE_URL. "
             "E.g. http://localhost:8000/v1",
    )
    parser.add_argument(
        "--api-key", type=str, default=None,
        help="API token/key for the chosen provider. Overrides env "
             "(OPENROUTER_API_KEY / INFERENCE_API_KEY / OPENAI_API_KEY).",
    )
    return parser.parse_args()


def main():
    """Entry point."""
    args = parse_args()

    api_key = args.api_key
    if args.provider == "openai":
        base_url = args.base_url or OPENAI_BASE_URL or None
    elif args.provider == "openrouter":
        base_url = args.base_url or OPENROUTER_BASE_URL
    else:
        base_url = args.base_url or None

    # Validate credentials / endpoint for the chosen provider
    if args.provider == "inference":
        resolved_key = api_key or INFERENCE_API_KEY or os.environ.get("INFERENCE_API_KEY", "")
        if not resolved_key:
            print("ERROR: Inference.net API token not set.")
            print("  Pass --api-key or export INFERENCE_API_KEY='your-inference-net-key'")
            sys.exit(1)
        api_key = resolved_key
    elif args.provider == "openai":
        if not base_url:
            print("ERROR: --base-url or OPENAI_BASE_URL is required "
                  "for --provider openai.")
            print("  Example: --base-url http://localhost:8000/v1")
            sys.exit(1)
        if not args.models:
            print("ERROR: --models is required for --provider openai.")
            print("  Pass the served model id(s), e.g. "
                  "--models Qwen/Qwen2.5-Coder-7B-Instruct")
            sys.exit(1)
        resolved_key = api_key if api_key is not None else OPENAI_API_KEY
        if not resolved_key:
            print("WARNING: no API key; "
                  "requests will be unauthenticated (OK for local vLLM).")
        api_key = resolved_key or None
    else:
        resolved_key = api_key or OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY", "")
        if not resolved_key:
            print("ERROR: OpenRouter API token not set.")
            print("  Pass --api-key 'sk-or-v1-...' or export OPENROUTER_API_KEY")
            sys.exit(1)
        api_key = resolved_key

    config = EvalConfig(
        trials=args.trials,
        problems=args.problems,
        models=args.models,
        prompt_strategy=args.strategy,
        manim_timeout=args.timeout,
        skip_render=args.skip_render,
        seed=args.seed,
        provider=args.provider,
        base_url=base_url,
        api_key=api_key,
    )

    run_evaluation(config)


if __name__ == "__main__":
    main()
