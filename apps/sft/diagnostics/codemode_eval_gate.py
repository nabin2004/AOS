#!/usr/bin/env python3
"""Greedy Ollama eval gate: live coder prompt must yield nested CodeMode.

Pass = first ``run_code`` nests Manim inside ``manim_write`` / ``compile_manim_code``
(no top-level ``from manim import *``).

By default uses ``CODE_PROMPT_LOCAL`` (same as hybrid/local Ollama coder). Use
``--prompt-variant full`` to probe the cloud-length prompt.

Usage (from apps/sft, with Ollama serving the GGUF):

    uv run python diagnostics/codemode_eval_gate.py
    uv run python diagnostics/codemode_eval_gate.py --prompt-variant full
    uv run python diagnostics/codemode_eval_gate.py --probe production
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SFT_ROOT = Path(__file__).resolve().parents[1]
AGENTS_ROOT = SFT_ROOT.parent / "agents"
DIAG = Path(__file__).resolve().parent
TRAINING_ROOT = SFT_ROOT.parent / "training"
sys.path.insert(0, str(SFT_ROOT))
sys.path.insert(0, str(TRAINING_ROOT))

from codemode_contract import extract_run_code_body, run_code_has_star_import  # noqa: E402
from model_identity import OLLAMA_HF_GGUF_REF  # noqa: E402

DEFAULT_MODEL = OLLAMA_HF_GGUF_REF
DEFAULT_BASE = "http://127.0.0.1:11434/v1"

# Keep close to the diagnosis short prompt that greedily passes CodeMode on E2B GGUF.
EVAL_USER_PROMPT = """Topic: Euler's Formula Visualization
Subject: math
Create a short Manim VoiceoverScene that visualizes e^(ix)=cos(x)+i*sin(x) on the unit circle.
Use scene_name=EulersFormulaVisualization.
Call tools ONLY via run_code (CodeMode): wrap Manim source in a string and await manim_write / compile_manim_code.
"""

PRODUCTION_PLAN_FIXTURE = DIAG / "fixtures" / "euler_lecture_plan.json"
PRODUCTION_OUTPUT_DIR = "/home/nabin/myallprojects/AOS/apps/agents/workspace/coder_runs/eval-gate-euler-probe"

RUN_CODE_TOOL = {
    "type": "function",
    "function": {
        "name": "run_code",
        "description": (
            "Execute Python in a Monty sandbox. Orchestrate tools with await; "
            "do not put from manim import * at top level."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "restart": {"type": "boolean"},
            },
            "required": ["code"],
        },
    },
}


def _load_prompt_constant(name: str) -> str:
    """Read a string constant from coder_agent.py without importing Agent side effects."""
    path = AGENTS_ROOT / "coder_agent.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise RuntimeError(f"{name} not found in {path}")


def resolve_prompt_variant(model: str, explicit: str | None) -> str:
    """Match live coder_system_prompt(): ollama models → local, else full."""
    if explicit in ("local", "full"):
        return explicit
    if (
        model.startswith("ollama:")
        or "gguf" in model.lower()
        or "aos-gemma4" in model.lower()
    ):
        return "local"
    return "full"


def load_code_prompt(variant: str) -> str:
    if variant == "local":
        return _load_prompt_constant("CODE_PROMPT_LOCAL")
    return _load_prompt_constant("CODE_PROMPT")


def build_production_user_prompt(
    topic: str,
    subject: str,
    plan: dict,
    output_dir: str,
) -> str:
    """Mirror agent_graph.run_coder_step user message shape."""
    plan_text = json.dumps(plan, indent=2)
    return (
        f"Topic: {topic}\n"
        f"Subject: {subject}\n"
        f"output_dir: {output_dir}\n"
        f"Use output_dir={output_dir!s} for every manim_write / compile_manim_code / "
        f"manim_read / synthesize_narration call.\n\n"
        f"Plan:\n{plan_text}"
    )


def load_production_user_prompt() -> str:
    sys.path.insert(0, str(AGENTS_ROOT))
    from coder_prompt import (  # noqa: E402
        LOCAL_CODER_CODEMODE_HINT,
        compact_plan_for_local_coder,
    )

    plan = json.loads(PRODUCTION_PLAN_FIXTURE.read_text(encoding="utf-8"))
    plan = compact_plan_for_local_coder(plan)
    plan_text = json.dumps(plan, indent=2)
    topic = plan.get("topic", "Euler's Formula")
    subject = plan.get("subject", "math")
    return (
        f"Topic: {topic}\n"
        f"Subject: {subject}\n"
        f"output_dir: {PRODUCTION_OUTPUT_DIR}\n"
        f"Use output_dir={PRODUCTION_OUTPUT_DIR!s} for every manim_write / compile_manim_code / "
        f"manim_read / synthesize_narration call.\n"
        f"{LOCAL_CODER_CODEMODE_HINT}\n"
        f"Plan:\n{plan_text}"
    )


def classify_code(code: str) -> str:
    has_mw = "manim_write" in code or "compile_manim_code" in code
    has_star = run_code_has_star_import(code)
    if has_star:
        return "raw_manim_top_level"
    if has_mw:
        return "wrap_then_manim_write"
    return "other_orchestration"


DEFAULT_NUM_CTX = 16384


def call_openai(
    base_url: str,
    model: str,
    system: str,
    user: str,
    max_tokens: int,
    *,
    num_ctx: int = DEFAULT_NUM_CTX,
) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
        "tools": [RUN_CODE_TOOL],
        "tool_choice": "auto",
        "think": False,
        "chat_template_kwargs": {"enable_thinking": False},
        "options": {"num_ctx": num_ctx},
    }
    url = base_url.rstrip("/") + "/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=1200) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise RuntimeError(f"ollama_http_{exc.code}: {body[:500]}") from exc


def _evaluate_response(data: dict, report: dict) -> tuple[bool, int]:
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    tool_calls = msg.get("tool_calls") or []
    report["finish_reason"] = choice.get("finish_reason")
    report["usage"] = data.get("usage")
    report["n_tool_calls"] = len(tool_calls)
    report["user_prompt_chars"] = report.get("user_prompt_chars")

    if not tool_calls:
        report["pass"] = False
        report["error"] = "no_tool_calls"
        report["content_preview"] = (msg.get("content") or "")[:400]
        return False, 1

    fn = tool_calls[0].get("function") or {}
    name = fn.get("name")
    body = extract_run_code_body(fn.get("arguments"))
    report["tool_name"] = name
    report["code_class"] = classify_code(body or "")
    report["code_preview"] = (body or "")[:500]
    report["has_star_import"] = bool(body and run_code_has_star_import(body))
    report["has_manim_write"] = bool(
        body and ("manim_write" in body or "compile_manim_code" in body)
    )

    ok = (
        name == "run_code"
        and body is not None
        and not run_code_has_star_import(body)
        and ("manim_write" in body or "compile_manim_code" in body)
    )
    report["pass"] = ok
    return ok, 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Greedy CodeMode eval gate via Ollama")
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--num-ctx", type=int, default=DEFAULT_NUM_CTX)
    parser.add_argument(
        "--prompt-variant",
        choices=("auto", "local", "full"),
        default="auto",
        help="auto = local for GGUF/Ollama (matches live hybrid coder), else full",
    )
    parser.add_argument(
        "--probe",
        choices=("short", "production"),
        default="short",
        help="short = compact eval prompt; production = full lecture plan like run_coder_step",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write JSON report (default: diagnostics/codemode_eval_gate_<ts>.json)",
    )
    args = parser.parse_args()

    explicit = None if args.prompt_variant == "auto" else args.prompt_variant
    variant = resolve_prompt_variant(args.model, explicit)
    system = load_code_prompt(variant)
    user_prompt = (
        load_production_user_prompt()
        if args.probe == "production"
        else EVAL_USER_PROMPT
    )
    report: dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "base_url": args.base_url,
        "max_tokens": args.max_tokens,
        "num_ctx": args.num_ctx,
        "prompt_variant": variant,
        "probe": args.probe,
        "prompt_chars": len(system),
        "user_prompt_chars": len(user_prompt),
    }

    try:
        data = call_openai(
            args.base_url,
            args.model,
            system,
            user_prompt,
            args.max_tokens,
            num_ctx=args.num_ctx,
        )
    except urllib.error.URLError as exc:
        report["pass"] = False
        report["error"] = f"ollama_unreachable: {exc}"
        _write(report, args.out)
        print(report["error"], file=sys.stderr)
        return 2
    except RuntimeError as exc:
        report["pass"] = False
        report["error"] = str(exc)
        _write(report, args.out)
        print(report["error"], file=sys.stderr)
        return 2

    ok, code = _evaluate_response(data, report)
    _write(report, args.out)

    if ok:
        print(
            f"PASS: CodeMode contract ok ({report['code_class']}, "
            f"probe={args.probe}, prompt={variant})"
        )
        return 0
    print(
        f"FAIL: code_class={report.get('code_class')} "
        f"star_import={report.get('has_star_import')} "
        f"has_manim_write={report.get('has_manim_write')} "
        f"probe={args.probe} prompt={variant} error={report.get('error')}",
        file=sys.stderr,
    )
    return code


def _write(report: dict, out: Path | None) -> None:
    if out is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = DIAG / f"codemode_eval_gate_{ts}.json"
    else:
        out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {out}")


if __name__ == "__main__":
    raise SystemExit(main())
