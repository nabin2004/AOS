#!/usr/bin/env python3
"""Bypass PydanticAI: probe Ollama GGUF with greedy decoding (raw + tools)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

DIAG = Path(__file__).resolve().parent
MODEL = "huggingface.co/nabin2004/AOS-gemma4-manim-gguf:Q4_K_M"
BASE = "http://127.0.0.1:11434"

INFER_SYS = """You are a Manim coding agent. Call tools ONLY via run_code (CodeMode).
Inside run_code, orchestrate workspace tools with await:
  await manim_write(code=..., scene_name=...)
  await compile_manim_code(code=..., scene_name=...)
Never write `from manim import *` directly in run_code — put Manim source inside a string passed to manim_write.
Workflow: manim_write → compile_manim_code → fix (at most 3 compile attempts) → stop.
"""

RUN_CODE_TOOL = {
    "type": "function",
    "function": {
        "name": "run_code",
        "description": (
            "Execute Python in a Monty sandbox. Orchestrate tools with await; "
            "do not put Manim imports at top level."
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


def _post(path: str, payload: dict, timeout: int = 900) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _get(path: str, timeout: int = 60) -> dict | str:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=timeout) as resp:
        body = resp.read().decode()
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return body


def dump_model_meta() -> None:
    tags = _get("/api/tags")
    DIAG.joinpath("ollama_tags.json").write_text(json.dumps(tags, indent=2))
    show = _post("/api/show", {"model": MODEL, "verbose": True})
    DIAG.joinpath("ollama_show_verbose.json").write_text(
        json.dumps(show, indent=2, ensure_ascii=False)[:2_000_000]
    )
    # Extract useful fields even if huge
    slim = {
        k: show.get(k)
        for k in (
            "modelfile",
            "parameters",
            "template",
            "details",
            "model_info",
            "capabilities",
        )
        if k in show
    }
    # Truncate template for readability in summary file
    tmpl = slim.get("template")
    if isinstance(tmpl, str):
        DIAG.joinpath("ollama_template.txt").write_text(tmpl)
    mf = slim.get("modelfile")
    if isinstance(mf, str):
        DIAG.joinpath("ollama_modelfile.txt").write_text(mf)
    # Keep model_info keys related to tokenizer/chat
    info = slim.get("model_info") or {}
    if isinstance(info, dict):
        interesting = {
            k: v
            for k, v in info.items()
            if any(
                s in k.lower()
                for s in ("token", "chat", "template", "eos", "bos", "stop", "vocab")
            )
        }
        DIAG.joinpath("ollama_model_info_tokens.json").write_text(
            json.dumps(interesting, indent=2, ensure_ascii=False)[:500_000]
        )
    DIAG.joinpath("ollama_show_slim.json").write_text(
        json.dumps(
            {
                "parameters": slim.get("parameters"),
                "details": slim.get("details"),
                "capabilities": slim.get("capabilities"),
                "template_len": len(tmpl) if isinstance(tmpl, str) else None,
                "modelfile_len": len(mf) if isinstance(mf, str) else None,
                "template_preview": (tmpl[:2000] if isinstance(tmpl, str) else tmpl),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print(
        "dumped model meta; template_len=", len(tmpl) if isinstance(tmpl, str) else None
    )


def probe_chat(*, with_tools: bool, out_stem: str) -> None:
    prompt = DIAG.joinpath("euler_short_prompt.txt").read_text()
    payload: dict = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": INFER_SYS},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": 0, "num_predict": 1024},
    }
    if with_tools:
        payload["tools"] = [RUN_CODE_TOOL]
    print(f"probing {out_stem} tools={with_tools} ...")
    data = _post("/api/chat", payload)
    DIAG.joinpath(f"{out_stem}.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False)
    )
    msg = data.get("message") or {}
    content = msg.get("content") or ""
    thinking = msg.get("thinking") or ""
    tool_calls = msg.get("tool_calls")
    DIAG.joinpath(f"{out_stem}_content.txt").write_text(content)
    if isinstance(thinking, str):
        DIAG.joinpath(f"{out_stem}_thinking.txt").write_text(thinking)
    if tool_calls is not None:
        DIAG.joinpath(f"{out_stem}_tool_calls.json").write_text(
            json.dumps(tool_calls, indent=2, ensure_ascii=False)
        )
    print(
        f"  done_reason={data.get('done_reason')} eval_count={data.get('eval_count')} "
        f"content_len={len(content)} thinking_len={len(thinking) if isinstance(thinking, str) else 0} "
        f"tool_calls={len(tool_calls) if tool_calls else 0}"
    )
    print("  content preview:", repr(content[:300]))
    if tool_calls:
        print("  tool_calls preview:", json.dumps(tool_calls, ensure_ascii=False)[:500])


def probe_openai_tools() -> None:
    """OpenAI-compatible path (what pydantic-ai uses)."""
    prompt = DIAG.joinpath("euler_short_prompt.txt").read_text()
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": INFER_SYS},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 1024,
        "tools": [RUN_CODE_TOOL],
        "tool_choice": "auto",
    }
    print("probing openai /v1/chat/completions ...")
    data = _post("/v1/chat/completions", payload)
    DIAG.joinpath("raw_openai_with_tools.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False)
    )
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    DIAG.joinpath("raw_openai_with_tools_message.json").write_text(
        json.dumps(msg, indent=2, ensure_ascii=False)
    )
    print(
        "  finish_reason=",
        choice.get("finish_reason"),
        " content_len=",
        len(msg.get("content") or ""),
        " tool_calls=",
        len(msg.get("tool_calls") or []),
    )


def main() -> None:
    try:
        _get("/api/tags")
    except urllib.error.URLError as exc:
        raise SystemExit(f"Ollama not reachable at {BASE}: {exc}") from exc
    dump_model_meta()
    probe_chat(with_tools=False, out_stem="raw_ollama_no_tools")
    probe_chat(with_tools=True, out_stem="raw_ollama_with_tools")
    probe_openai_tools()
    print("all probes written to", DIAG)


if __name__ == "__main__":
    main()
