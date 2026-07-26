#!/usr/bin/env python3
"""Diff raw Ollama completions vs SFT Jinja / parse_gemma_tool_calls / CodeMode contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DIAG = Path(__file__).resolve().parent
SFT_ROOT = DIAG.parents[1]
sys.path.insert(0, str(SFT_ROOT))

from infer_tools import (  # noqa: E402
    _codemode_preflight,
    extract_run_code_source,
    parse_gemma_tool_calls,
    strip_tool_call_markup,
)


def classify_code(code: str) -> str:
    has_mw = "manim_write" in code
    has_star = "from manim import" in code
    has_assign = bool(re.search(r"\bcode\s*=", code))
    if has_mw and has_assign:
        return "wrap_then_manim_write"
    if has_mw:
        return "manim_write_other"
    if has_star:
        return "raw_manim_top_level"
    return "other_orchestration"


def analyze_text(label: str, text: str) -> dict:
    calls = []
    parse_err = None
    try:
        calls = parse_gemma_tool_calls(text)
    except Exception as exc:  # noqa: BLE001
        parse_err = f"{type(exc).__name__}: {exc}"
    leftover = strip_tool_call_markup(text) if text else ""
    markers = {
        "has_tool_call_start": "<|tool_call>call:" in text,
        "has_tool_call_end": "<tool_call|>" in text,
        "has_gemma_string_delim": '<|"|>' in text,
        "has_channel_thought": "<|channel>thought" in text or "<|channel>" in text,
        "has_think_token": "<|think|>" in text,
        "has_turn_marker": "<|turn>" in text,
        "has_eos": "<eos>" in text or "<|eot|>" in text or "<end_of_turn>" in text,
        "mentions_run_code": "run_code" in text,
        "mentions_manim_write": "manim_write" in text,
        "mentions_from_manim": "from manim import" in text,
    }
    bodies = []
    for c in calls:
        args = c.get("function", {}).get("arguments", {})
        try:
            src = extract_run_code_source(args)
        except Exception as exc:  # noqa: BLE001
            src = f"<extract_error {exc}>"
        pre = _codemode_preflight(src) if isinstance(src, str) else None
        bodies.append(
            {
                "name": c.get("function", {}).get("name"),
                "arg_keys": sorted(args.keys())
                if isinstance(args, dict)
                else type(args).__name__,
                "code_class": classify_code(src) if isinstance(src, str) else None,
                "preflight": pre,
                "code_preview": (src[:400] if isinstance(src, str) else src),
            }
        )
    return {
        "label": label,
        "text_len": len(text),
        "markers": markers,
        "parse_error": parse_err,
        "n_gemma_parsed_calls": len(calls),
        "leftover_text_preview": leftover[:300],
        "bodies": bodies,
    }


def analyze_openai_tool_calls(label: str, tool_calls) -> dict:
    bodies = []
    for tc in tool_calls or []:
        # Ollama native vs OpenAI shape
        if "function" in tc:
            fn = tc["function"]
            name = fn.get("name")
            args = fn.get("arguments")
        else:
            name = (
                tc.get("function", {}).get("name")
                if isinstance(tc.get("function"), dict)
                else tc.get("name")
            )
            args = (
                tc.get("function", {}).get("arguments")
                if isinstance(tc.get("function"), dict)
                else tc.get("arguments")
            )
            if name is None and "function" not in tc:
                # ollama api/chat shape: {"function":{"name","arguments":{...}}}
                fn = tc.get("function") or {}
                name = fn.get("name")
                args = fn.get("arguments")
        if isinstance(args, str):
            try:
                args_obj = json.loads(args)
            except json.JSONDecodeError:
                args_obj = {"_raw": args}
        else:
            args_obj = args or {}
        try:
            src = extract_run_code_source(args_obj)
        except Exception as exc:  # noqa: BLE001
            src = f"<extract_error {exc}>"
        pre = _codemode_preflight(src) if isinstance(src, str) else None
        bodies.append(
            {
                "name": name,
                "arg_keys": sorted(args_obj.keys())
                if isinstance(args_obj, dict)
                else type(args_obj).__name__,
                "code_class": classify_code(src) if isinstance(src, str) else None,
                "preflight": pre,
                "code_preview": (src[:400] if isinstance(src, str) else src),
            }
        )
    return {
        "label": label,
        "n_structured_tool_calls": len(tool_calls or []),
        "bodies": bodies,
    }


def render_jinja_golden() -> dict:
    """Render one training-format tool call via gemma4_training.jinja if tokenizer available."""
    from chat_template import load_gemma4_training_template

    try:
        from transformers import AutoTokenizer
    except ImportError:
        return {"error": "transformers not importable"}

    model_id = "google/gemma-4-E2B-it"
    try:
        tok = AutoTokenizer.from_pretrained(model_id)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"tokenizer load failed: {exc}"}

    tok.chat_template = load_gemma4_training_template()
    messages = [
        {
            "role": "system",
            "content": "You are a Manim coding agent. Call tools ONLY via run_code.",
        },
        {
            "role": "user",
            "content": DIAG.joinpath("euler_short_prompt.txt").read_text(),
        },
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_0",
                    "type": "function",
                    "function": {
                        "name": "run_code",
                        "arguments": {
                            "code": (
                                "code = '''from manim import *\\nclass Demo(Scene):\\n"
                                "    def construct(self):\\n        self.play(Create(Circle()))'''\n"
                                "await manim_write(code=code, scene_name='Demo')"
                            )
                        },
                    },
                }
            ],
        },
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "run_code",
                "description": "Execute CodeMode sandbox code",
                "parameters": {
                    "type": "object",
                    "properties": {"code": {"type": "string"}},
                    "required": ["code"],
                },
            },
        }
    ]
    rendered = tok.apply_chat_template(
        messages, tools=tools, tokenize=False, add_generation_prompt=False
    )
    DIAG.joinpath("jinja_golden_rendered.txt").write_text(rendered)
    # Isolate assistant tool markup
    idx = rendered.rfind("<|tool_call>")
    tool_surface = rendered[idx:] if idx >= 0 else rendered[-800:]
    DIAG.joinpath("jinja_golden_tool_surface.txt").write_text(tool_surface)
    return {
        "rendered_len": len(rendered),
        "tool_surface_preview": tool_surface[:600],
        "has_tool_call_markup": "<|tool_call>call:run_code" in rendered,
        "has_pipe_string": '<|"|>' in rendered,
    }


def compare_templates() -> dict:
    sft = (SFT_ROOT / "templates" / "gemma4_training.jinja").read_text()
    ollama_tmpl_path = DIAG / "ollama_template.txt"
    ollama = ollama_tmpl_path.read_text() if ollama_tmpl_path.exists() else ""
    modelfile = (
        DIAG.joinpath("ollama_modelfile.txt").read_text()
        if DIAG.joinpath("ollama_modelfile.txt").exists()
        else ""
    )
    checks = {
        "sft_len": len(sft),
        "ollama_template_len": len(ollama),
        "modelfile_has_TEMPLATE": "TEMPLATE" in modelfile.upper()
        or bool(re.search(r"(?m)^TEMPLATE", modelfile)),
        "modelfile_preview": modelfile[:500],
        "markers": {},
    }
    for name, blob in ("sft", sft), ("ollama", ollama):
        checks["markers"][name] = {
            "tool_call_call": "<|tool_call>call:" in blob,
            "tool_call_end": "<tool_call|>" in blob,
            "pipe_string": '<|"|>' in blob,
            "turn": "<|turn>" in blob,
            "channel_thought": "<|channel>thought" in blob,
            "think": "<|think|>" in blob,
            "generation_marker": "{% generation %}" in blob
            or "{%- generation -%}" in blob,
            "enable_thinking": "enable_thinking" in blob,
        }
    # Rough similarity: shared distinctive substrings
    distinctive = [
        "<|tool_call>call:",
        "<tool_call|>",
        '<|"|>',
        "<|turn>",
        "<|channel>thought",
        "format_argument",
        "strip_thinking",
    ]
    checks["distinctive_in_both"] = {s: (s in sft and s in ollama) for s in distinctive}
    checks["distinctive_only_sft"] = [
        s for s in distinctive if s in sft and s not in ollama
    ]
    checks["distinctive_only_ollama"] = [
        s for s in distinctive if s in ollama and s not in sft
    ]
    checks["templates_identical"] = sft.strip() == ollama.strip() if ollama else False
    return checks


def analyze_euler_trace() -> dict:
    path = Path(
        "/home/nabin/myallprojects/AOS/apps/agents/workspace/coder_runs/"
        "20260726-114637-euler-s-formula-visualization/traces/messages.json"
    )
    msgs = json.loads(path.read_text())
    out: dict = {"turns": []}
    for i, m in enumerate(msgs):
        for part in m.get("parts") or []:
            pk = part.get("part_kind")
            if pk == "tool-call":
                args = part.get("args")
                if isinstance(args, str):
                    try:
                        args_obj = json.loads(args)
                    except json.JSONDecodeError:
                        args_obj = {"_raw": args}
                else:
                    args_obj = args or {}
                src = extract_run_code_source(args_obj)
                out["turns"].append(
                    {
                        "msg": i,
                        "kind": "tool-call",
                        "name": part.get("tool_name"),
                        "code_class": classify_code(src),
                        "preflight": _codemode_preflight(src),
                        "finish_reason": m.get("finish_reason"),
                        "output_tokens": (m.get("usage") or {}).get("output_tokens"),
                    }
                )
            elif pk == "thinking":
                out["turns"].append(
                    {
                        "msg": i,
                        "kind": "thinking",
                        "len": len(part.get("content") or ""),
                        "finish_reason": m.get("finish_reason"),
                        "output_tokens": (m.get("usage") or {}).get("output_tokens"),
                        "tail": (part.get("content") or "")[-200:],
                    }
                )
            elif pk == "text" and m.get("kind") == "response":
                out["turns"].append(
                    {
                        "msg": i,
                        "kind": "text",
                        "content": part.get("content"),
                        "finish_reason": m.get("finish_reason"),
                    }
                )
            elif pk == "retry-prompt":
                out["turns"].append(
                    {
                        "msg": i,
                        "kind": "retry-prompt",
                        "preview": (part.get("content") or "")[:200],
                    }
                )
    return out


def main() -> None:
    report: dict = {
        "euler_trace": analyze_euler_trace(),
        "template_compare": compare_templates(),
        "jinja_golden": render_jinja_golden(),
        "probes": [],
    }

    # Raw content files from probes
    for stem in ("raw_ollama_no_tools", "raw_ollama_with_tools"):
        content_path = DIAG / f"{stem}_content.txt"
        if content_path.exists():
            report["probes"].append(
                analyze_text(stem + "_content", content_path.read_text())
            )
        tc_path = DIAG / f"{stem}_tool_calls.json"
        if tc_path.exists():
            report["probes"].append(
                analyze_openai_tool_calls(
                    stem + "_tool_calls", json.loads(tc_path.read_text())
                )
            )
        thinking_path = DIAG / f"{stem}_thinking.txt"
        if thinking_path.exists():
            t = thinking_path.read_text()
            report["probes"].append(
                {
                    "label": stem + "_thinking",
                    "thinking_len": len(t),
                    "mentions_missing_plan": "lecture plan" in t.lower()
                    and (
                        "no" in t.lower()
                        or "missing" in t.lower()
                        or "not provided" in t.lower()
                    ),
                    "tail": t[-300:],
                }
            )

    for stem in (
        "raw_openai_with_tools_message",
        "raw_openai_full_euler_message",
    ):
        openai_msg = DIAG / f"{stem}.json"
        if not openai_msg.exists():
            continue
        msg = json.loads(openai_msg.read_text())
        report["probes"].append(
            analyze_text(f"{stem}_content", msg.get("content") or "")
        )
        report["probes"].append(
            analyze_openai_tool_calls(f"{stem}_tool_calls", msg.get("tool_calls"))
        )
        if msg.get("reasoning") or msg.get("thinking"):
            r = msg.get("reasoning") or msg.get("thinking") or ""
            report["probes"].append(
                {
                    "label": f"{stem}_reasoning",
                    "reasoning_len": len(r),
                    "tail": r[-250:],
                }
            )

    # Training contamination snapshot
    train = Path(
        "/home/nabin/myallprojects/AOS/apps/agents/export_traces/coder_sft/tool_trace.train.jsonl"
    )
    if train.exists():
        from collections import Counter

        first = Counter()
        n = 0
        with train.open() as f:
            for line in f:
                row = json.loads(line)
                n += 1
                for m in row.get("messages") or []:
                    if m.get("role") != "assistant":
                        continue
                    for tc in m.get("tool_calls") or []:
                        fn = tc.get("function") or {}
                        if fn.get("name") != "run_code":
                            continue
                        args = fn.get("arguments")
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except json.JSONDecodeError:
                                break
                        src = extract_run_code_source(args or {})
                        first[classify_code(src)] += 1
                        break
                    else:
                        continue
                    break
        report["train_first_run_code"] = {"rows": n, "classes": dict(first)}

    DIAG.joinpath("analysis_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False)
    )
    # Human summary
    lines = ["# Serving-format diagnosis summary", ""]
    tc = report["template_compare"]
    lines.append("## Template audit")
    lines.append(f"- templates_identical: {tc.get('templates_identical')}")
    lines.append(f"- modelfile_has_TEMPLATE: {tc.get('modelfile_has_TEMPLATE')}")
    lines.append(f"- distinctive_only_sft: {tc.get('distinctive_only_sft')}")
    lines.append(f"- ollama markers: {tc.get('markers', {}).get('ollama')}")
    lines.append(f"- sft markers: {tc.get('markers', {}).get('sft')}")
    lines.append("")
    lines.append("## Jinja golden")
    lines.append(json.dumps(report["jinja_golden"], indent=2)[:800])
    lines.append("")
    lines.append("## Euler hybrid trace")
    for t in report["euler_trace"]["turns"]:
        lines.append(f"- {t}")
    lines.append("")
    lines.append("## Probe results")
    for p in report["probes"]:
        lines.append(f"- {json.dumps(p, ensure_ascii=False)[:500]}")
    lines.append("")
    lines.append("## Train first-run_code classes")
    lines.append(str(report.get("train_first_run_code")))
    DIAG.joinpath("SUMMARY.md").write_text("\n".join(lines))
    print(DIAG.joinpath("SUMMARY.md").read_text())


if __name__ == "__main__":
    main()
