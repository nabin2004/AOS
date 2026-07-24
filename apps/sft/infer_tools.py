"""Tool schemas, Gemma tool-call parsing, and Manim/CodeMode execution for infer.py.

Training trajectories almost exclusively use CodeMode ``run_code`` (see
``apps/agents/training_data/trajectories.jsonl``). ``format_trajectory_messages``
wraps each step as ``arguments={"input": <payload>}``, so the primary tool
schema mirrors that shape. Direct ``manim_write`` / ``compile_manim_code`` /
``manim_read`` tools are also exposed for robustness.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import json
import os
import re
import sys
import textwrap
from pathlib import Path
from typing import Any, Callable

AGENTS_ROOT = Path(__file__).resolve().parents[1] / "agents"
WORKSPACE_INFER_ROOT = AGENTS_ROOT / "workspace" / "infer_runs"

TOOL_CALL_START = "<|tool_call>call:"
TOOL_CALL_END = "<tool_call|>"
STRING_DELIM = '<|"|>'

# OpenAI-style tool defs passed to apply_chat_template(..., tools=...).
INFER_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "run_code",
            "description": (
                "Execute CodeMode sandbox Python that can call manim_write, "
                "compile_manim_code, manim_read, search_manim_docs, "
                "search_manim_signatures, and synthesize_narration."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "description": (
                            'JSON string {"code": "..."} or raw CodeMode Python.'
                        ),
                    },
                    "code": {
                        "type": "string",
                        "description": "CodeMode Python (alternative to input).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manim_write",
            "description": "Write Manim scene source into the coder workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Full Manim Python source",
                    },
                    "scene_name": {
                        "type": "string",
                        "description": "Scene module / class stem",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Workspace output directory",
                    },
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compile_manim_code",
            "description": "Write and compile Manim code in the coder workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Full Manim Python source",
                    },
                    "scene_name": {
                        "type": "string",
                        "description": "Scene module / class stem",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Workspace output directory",
                    },
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manim_read",
            "description": "Read back the current scene source from the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "output_dir": {
                        "type": "string",
                        "description": "Workspace output directory",
                    },
                },
            },
        },
    },
]


def default_infer_output_dir() -> Path:
    """Scratch dir under the agents workspace allowlist."""
    from datetime import UTC, datetime

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    path = WORKSPACE_INFER_ROOT / stamp
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ensure_agents_importable() -> None:
    os.environ.setdefault("AOS_DBOS", "0")
    os.environ.setdefault("AOS_LOGFIRE", "0")
    root = str(AGENTS_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def _load_agent_tools() -> dict[str, Callable[..., str]]:
    _ensure_agents_importable()
    from tools.compile import compile_manim_code
    from tools.manim_read import manim_read
    from tools.manim_write import manim_write

    tools: dict[str, Callable[..., str]] = {
        "manim_write": manim_write,
        "compile_manim_code": compile_manim_code,
        "manim_read": manim_read,
    }
    try:
        from tools.manim_docs import search_manim_docs, search_manim_signatures

        tools["search_manim_docs"] = search_manim_docs
        tools["search_manim_signatures"] = search_manim_signatures
    except Exception:  # noqa: BLE001 — optional at infer time
        tools["search_manim_docs"] = lambda query, top_k=5: json.dumps(
            {"ok": False, "error": "search_manim_docs unavailable", "query": query}
        )
        tools["search_manim_signatures"] = lambda query, top_k=5: json.dumps(
            {
                "ok": False,
                "error": "search_manim_signatures unavailable",
                "query": query,
            }
        )
    try:
        from tools.voiceover import synthesize_narration

        tools["synthesize_narration"] = synthesize_narration
    except Exception:  # noqa: BLE001
        tools["synthesize_narration"] = lambda text, voice="alba", output_dir=None: (
            json.dumps(
                {
                    "ok": False,
                    "error": "synthesize_narration unavailable",
                    "message": "Voiceover deps not loaded in this environment.",
                }
            )
        )
    return tools


def _skip_ws(text: str, i: int) -> int:
    while i < len(text) and text[i].isspace():
        i += 1
    return i


def _parse_string(text: str, i: int) -> tuple[str, int]:
    if not text.startswith(STRING_DELIM, i):
        raise ValueError(f"expected {STRING_DELIM!r} string at {i}")
    i += len(STRING_DELIM)
    end = text.find(STRING_DELIM, i)
    if end < 0:
        raise ValueError("unterminated Gemma tool-call string")
    return text[i:end], end + len(STRING_DELIM)


def _parse_value(text: str, i: int) -> tuple[Any, int]:
    i = _skip_ws(text, i)
    if text.startswith(STRING_DELIM, i):
        return _parse_string(text, i)
    if text.startswith("null", i) and (i + 4 >= len(text) or not text[i + 4].isalnum()):
        return None, i + 4
    if text.startswith("true", i) and (i + 4 >= len(text) or not text[i + 4].isalnum()):
        return True, i + 4
    if text.startswith("false", i) and (
        i + 5 >= len(text) or not text[i + 5].isalnum()
    ):
        return False, i + 5
    if text[i : i + 1] == "{":
        return _parse_object(text, i)
    if text[i : i + 1] == "[":
        return _parse_array(text, i)
    # number or bare identifier token
    m = re.match(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", text[i:])
    if m:
        raw = m.group(0)
        i2 = i + len(raw)
        if "." in raw or "e" in raw.lower():
            return float(raw), i2
        return int(raw), i2
    raise ValueError(f"cannot parse tool-call value at index {i}: {text[i : i + 40]!r}")


def _parse_object(text: str, i: int) -> tuple[dict[str, Any], int]:
    if text[i] != "{":
        raise ValueError("expected '{'")
    i += 1
    out: dict[str, Any] = {}
    i = _skip_ws(text, i)
    if i < len(text) and text[i] == "}":
        return out, i + 1
    while i < len(text):
        i = _skip_ws(text, i)
        if text.startswith(STRING_DELIM, i):
            key, i = _parse_string(text, i)
        else:
            m = re.match(r"[A-Za-z_][A-Za-z0-9_]*", text[i:])
            if not m:
                raise ValueError(f"expected object key at {i}")
            key = m.group(0)
            i += len(key)
        i = _skip_ws(text, i)
        if i >= len(text) or text[i] != ":":
            raise ValueError(f"expected ':' after key {key!r}")
        i += 1
        value, i = _parse_value(text, i)
        out[key] = value
        i = _skip_ws(text, i)
        if i < len(text) and text[i] == ",":
            i += 1
            continue
        if i < len(text) and text[i] == "}":
            return out, i + 1
        raise ValueError(f"expected ',' or '}}' in object at {i}")
    raise ValueError("unterminated object")


def _parse_array(text: str, i: int) -> tuple[list[Any], int]:
    if text[i] != "[":
        raise ValueError("expected '['")
    i += 1
    out: list[Any] = []
    i = _skip_ws(text, i)
    if i < len(text) and text[i] == "]":
        return out, i + 1
    while i < len(text):
        value, i = _parse_value(text, i)
        out.append(value)
        i = _skip_ws(text, i)
        if i < len(text) and text[i] == ",":
            i += 1
            continue
        if i < len(text) and text[i] == "]":
            return out, i + 1
        raise ValueError(f"expected ',' or ']' in array at {i}")
    raise ValueError("unterminated array")


def parse_gemma_tool_calls(text: str) -> list[dict[str, Any]]:
    """Parse ``<|tool_call>call:name{...}<tool_call|>`` blocks from a model turn."""
    calls: list[dict[str, Any]] = []
    i = 0
    while True:
        start = text.find(TOOL_CALL_START, i)
        if start < 0:
            break
        pos = start + len(TOOL_CALL_START)
        brace = text.find("{", pos)
        if brace < 0:
            break
        name = text[pos:brace].strip()
        try:
            args, end = _parse_object(text, brace)
        except ValueError:
            # Fallback: brace-match and try JSON (models sometimes emit JSON args).
            end = _find_matching_brace(text, brace)
            raw = text[brace : end + 1]
            try:
                parsed = json.loads(raw)
                args = parsed if isinstance(parsed, dict) else {"input": raw}
            except json.JSONDecodeError:
                args = {"input": raw}
            end += 1
        end = _skip_ws(text, end)
        if text.startswith(TOOL_CALL_END, end):
            end += len(TOOL_CALL_END)
        call_id = f"call_{len(calls)}"
        calls.append(
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": args},
            }
        )
        i = end
    return calls


def _find_matching_brace(text: str, open_idx: int) -> int:
    depth = 0
    in_string = False
    j = open_idx
    while j < len(text):
        if text.startswith(STRING_DELIM, j):
            in_string = not in_string
            j += len(STRING_DELIM)
            continue
        ch = text[j]
        if not in_string:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return j
        j += 1
    return len(text) - 1


def strip_tool_call_markup(text: str) -> str:
    """Remove tool-call blocks; leftover is plain assistant text."""
    if TOOL_CALL_START not in text:
        return text.strip()
    parts: list[str] = []
    i = 0
    while i < len(text):
        start = text.find(TOOL_CALL_START, i)
        if start < 0:
            parts.append(text[i:])
            break
        parts.append(text[i:start])
        brace = text.find("{", start + len(TOOL_CALL_START))
        if brace < 0:
            parts.append(text[start:])
            break
        try:
            _, end = _parse_object(text, brace)
        except ValueError:
            end = _find_matching_brace(text, brace) + 1
        end = _skip_ws(text, end)
        if text.startswith(TOOL_CALL_END, end):
            end += len(TOOL_CALL_END)
        i = end
    return "".join(parts).strip()


def extract_run_code_source(arguments: dict[str, Any] | str) -> str:
    """Unwrap training-shaped ``input`` / native ``code`` payloads to Python source."""
    if isinstance(arguments, str):
        payload: Any = arguments
    else:
        if "code" in arguments and arguments["code"] is not None:
            payload = arguments["code"]
        elif "input" in arguments:
            payload = arguments["input"]
        else:
            payload = arguments

    if isinstance(payload, dict):
        if "code" in payload:
            return str(payload["code"])
        return json.dumps(payload)

    text = str(payload).strip()
    if text.startswith("{"):
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return text
        if isinstance(obj, dict) and "code" in obj:
            return str(obj["code"])
    return text


async def _exec_codemode(code: str, output_dir: str) -> str:
    tools = _load_agent_tools()

    def _force_output_dir(kwargs: dict[str, Any]) -> dict[str, Any]:
        out = dict(kwargs)
        out["output_dir"] = output_dir
        return out

    async def manim_write(**kwargs: Any) -> str:
        return tools["manim_write"](**_force_output_dir(kwargs))

    async def compile_manim_code(**kwargs: Any) -> str:
        return tools["compile_manim_code"](**_force_output_dir(kwargs))

    async def manim_read(**kwargs: Any) -> str:
        return tools["manim_read"](**_force_output_dir(kwargs))

    async def synthesize_narration(**kwargs: Any) -> str:
        return tools["synthesize_narration"](**_force_output_dir(kwargs))

    async def search_manim_docs(query: str, top_k: int = 5) -> str:
        return tools["search_manim_docs"](query, top_k=top_k)

    async def search_manim_signatures(query: str, top_k: int = 5) -> str:
        return tools["search_manim_signatures"](query, top_k=top_k)

    ns: dict[str, Any] = {
        "__builtins__": __builtins__,
        "manim_write": manim_write,
        "compile_manim_code": compile_manim_code,
        "manim_read": manim_read,
        "synthesize_narration": synthesize_narration,
        "search_manim_docs": search_manim_docs,
        "search_manim_signatures": search_manim_signatures,
        "asyncio": asyncio,
        "json": json,
    }
    wrapped = "async def __codemode_main():\n" + textwrap.indent(code, "    ")
    try:
        exec(wrapped, ns)  # noqa: S102 — intentional CodeMode sandbox for SFT infer
    except SyntaxError as exc:
        return json.dumps({"ok": False, "error": "syntax_error", "message": str(exc)})

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            result = await ns["__codemode_main"]()
    except Exception as exc:  # noqa: BLE001 — surface tool failures to the model
        err = {"ok": False, "error": type(exc).__name__, "message": str(exc)}
        printed = buf.getvalue().strip()
        if printed:
            err["stdout"] = printed
        return json.dumps(err)

    printed = buf.getvalue().strip()
    chunks: list[str] = []
    if printed:
        chunks.append(printed)
    if result is not None:
        chunks.append(str(result))
    return (
        "\n".join(chunks)
        if chunks
        else json.dumps({"ok": True, "message": "run_code finished with no output"})
    )


def execute_tool_call(
    name: str,
    arguments: dict[str, Any] | str,
    *,
    output_dir: str | Path,
) -> str:
    """Execute one parsed tool call; always returns a string tool result."""
    output_dir_s = str(Path(output_dir))
    args = arguments if isinstance(arguments, dict) else {"input": arguments}
    tools = _load_agent_tools()

    try:
        if name == "run_code":
            code = extract_run_code_source(args)
            return asyncio.run(_exec_codemode(code, output_dir_s))

        if name == "manim_write":
            return tools["manim_write"](
                code=str(args.get("code", "")),
                scene_name=str(args.get("scene_name", "scene")),
                output_dir=output_dir_s,
            )

        if name == "compile_manim_code":
            return tools["compile_manim_code"](
                code=str(args.get("code", "")),
                scene_name=str(args.get("scene_name", "scene")),
                output_dir=output_dir_s,
            )

        if name == "manim_read":
            return tools["manim_read"](output_dir=output_dir_s)

        if name in ("search_manim_docs", "search_manim_signatures"):
            query = str(args.get("query", args.get("input", "")))
            top_k = int(args.get("top_k", 5))
            return tools[name](query, top_k=top_k)

        if name == "synthesize_narration":
            return tools["synthesize_narration"](
                text=str(args.get("text", "")),
                voice=str(args.get("voice", "alba")),
                output_dir=output_dir_s,
            )

        return json.dumps(
            {
                "ok": False,
                "error": "unknown_tool",
                "message": f"Unknown tool {name!r}",
            }
        )
    except Exception as exc:  # noqa: BLE001
        return json.dumps(
            {"ok": False, "error": type(exc).__name__, "message": str(exc)}
        )


def assistant_message_from_generation(raw: str) -> dict[str, Any]:
    """Build an OpenAI-style assistant message from a decoded model turn."""
    tool_calls = parse_gemma_tool_calls(raw)
    text = strip_tool_call_markup(raw)
    # Drop trailing special tokens often left when skip_special_tokens=False.
    text = re.sub(r"<\|[^|>]+(?:\|>)?$", "", text).strip()
    text = re.sub(r"<eos>\s*$", "", text).strip()
    msg: dict[str, Any] = {"role": "assistant"}
    if tool_calls:
        msg["content"] = text or None
        msg["tool_calls"] = tool_calls
    else:
        msg["content"] = text or raw.strip()
    return msg
