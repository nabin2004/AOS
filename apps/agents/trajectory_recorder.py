"""Application-layer trajectory capture for Code Agent SFT (no Logfire parsing)."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai.messages import ModelMessage

from export_traces.otel_messages import normalize_model_messages

AGENTS_ROOT = Path(__file__).resolve().parent
DEFAULT_GLOBAL_PATH = AGENTS_ROOT / "training_data" / "trajectories.jsonl"
MAX_OUTPUT_CHARS = 8192

_PATH_PREFIXES = (
    str(AGENTS_ROOT),
    "/home/",
    "/tmp/",
    "/var/",
)


class TrajectoryStep(BaseModel):
    type: str = "tool_call"
    tool_name: str
    input: str
    output: str
    is_error: bool = False


class TrajectoryRecord(BaseModel):
    user_prompt: str
    prompt_index: int | None = None
    success: bool
    final_code: str | None = None
    summary: str = ""
    trajectory: list[TrajectoryStep] = Field(default_factory=list)
    run_dir: str
    stopped_reason: str = "completed"
    usage: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = ""


def _tool_result_is_error(result: str) -> bool:
    text = result.strip()
    if not text:
        return False
    lowered = text.lower()
    if "traceback" in lowered or "error:" in lowered:
        return True
    if text.startswith("{"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return False
        if isinstance(payload, dict):
            if payload.get("ok") is False:
                return True
            if payload.get("error"):
                return True
    return False


def steps_from_messages(messages: list[ModelMessage] | None) -> list[TrajectoryStep]:
    """Pair tool_call parts with tool_call_response parts in message order."""
    if not messages:
        return []

    normalized = normalize_model_messages(messages)
    pending: dict[str, dict[str, str]] = {}
    steps: list[TrajectoryStep] = []

    for msg in normalized:
        for part in msg.get("parts") or []:
            part_type = part.get("type")
            if part_type == "tool_call":
                call_id = str(part.get("id", ""))
                arguments = part.get("arguments", "{}")
                if not isinstance(arguments, str):
                    arguments = json.dumps(arguments, ensure_ascii=False)
                pending[call_id] = {
                    "tool_name": str(part.get("name", "")),
                    "input": arguments,
                }
            elif part_type == "tool_call_response":
                call_id = str(part.get("id", ""))
                result = str(part.get("result", ""))
                meta = pending.pop(
                    call_id,
                    {
                        "tool_name": str(part.get("name", "")),
                        "input": "",
                    },
                )
                steps.append(
                    TrajectoryStep(
                        tool_name=meta["tool_name"],
                        input=sanitize(meta["input"]),
                        output=sanitize(result),
                        is_error=_tool_result_is_error(result),
                    )
                )

    return steps


def sanitize(text: str, *, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    """Strip absolute paths and truncate oversized tool payloads."""
    if not text:
        return text

    cleaned = text
    for prefix in _PATH_PREFIXES:
        cleaned = cleaned.replace(prefix, "")

    cleaned = re.sub(
        r"(workspace/coder_runs/)[^\s\"']+",
        r"\1<run>",
        cleaned,
    )
    cleaned = re.sub(
        r"(output_dir[\"']?\s*[:=]\s*[\"']?)[^\s\"',}]+",
        r"\1<run>",
        cleaned,
        flags=re.IGNORECASE,
    )

    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3] + "..."


def _relative_run_dir(run_dir: Path) -> str:
    resolved = run_dir.resolve()
    try:
        return str(resolved.relative_to(AGENTS_ROOT))
    except ValueError:
        return str(resolved)


class TrajectoryRecorder:
    def __init__(self, save_path: Path | str = DEFAULT_GLOBAL_PATH) -> None:
        self.save_path = Path(save_path)
        self.save_path.parent.mkdir(parents=True, exist_ok=True)

    def build_record(
        self,
        run_dir: Path | str,
        *,
        messages: list[ModelMessage] | None,
        user_prompt: str | None,
        prompt_index: int | None,
        code: str | None,
        compile_ok: bool,
        summary: str,
        stopped_reason: str,
        usage: dict[str, Any],
    ) -> TrajectoryRecord:
        run_path = Path(run_dir).resolve()
        prompt = (user_prompt or "").strip() or "unknown"
        return TrajectoryRecord(
            user_prompt=prompt,
            prompt_index=prompt_index,
            success=compile_ok,
            final_code=code,
            summary=summary or stopped_reason,
            trajectory=steps_from_messages(messages),
            run_dir=_relative_run_dir(run_path),
            stopped_reason=stopped_reason,
            usage=usage,
            timestamp=datetime.now(UTC).isoformat(),
        )

    def save_run(
        self,
        run_dir: Path | str,
        *,
        messages: list[ModelMessage] | None,
        user_prompt: str | None = None,
        prompt_index: int | None = None,
        code: str | None = None,
        compile_ok: bool = False,
        summary: str = "",
        stopped_reason: str = "completed",
        usage: dict[str, Any] | None = None,
    ) -> TrajectoryRecord:
        record = self.build_record(
            run_dir,
            messages=messages,
            user_prompt=user_prompt,
            prompt_index=prompt_index,
            code=code,
            compile_ok=compile_ok,
            summary=summary,
            stopped_reason=stopped_reason,
            usage=usage or {},
        )
        run_path = Path(run_dir).resolve()
        traces_dir = run_path / "traces"
        traces_dir.mkdir(parents=True, exist_ok=True)
        per_run_path = traces_dir / "trajectory.json"
        per_run_path.write_text(
            record.model_dump_json(indent=2),
            encoding="utf-8",
        )

        with self.save_path.open("a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")

        return record


default_recorder = TrajectoryRecorder()
