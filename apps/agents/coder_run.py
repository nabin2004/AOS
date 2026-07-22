"""Per-run workspace layout and structured artifacts for the Code Agent."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from pydantic_ai.usage import RunUsage

from tools.coder_workspace import load_manifest, resolve_output_dir

CODER_RUNS_ROOT = Path(__file__).resolve().parent / "workspace" / "coder_runs"

DEFAULT_REQUEST_LIMIT = 20
DEFAULT_TOOL_CALLS_LIMIT = 40


class CoderRunResult(BaseModel):
    """Structured summary of one Code Agent run (code + audio + traces)."""

    run_dir: str
    scene_name: str | None = None
    scene_file: str | None = None
    code: str | None = None
    compile_ok: bool = False
    compile_log_path: str | None = None
    audio_paths: list[str] = Field(default_factory=list)
    media_hint: str | None = None
    manifest_path: str | None = None
    traces_path: str | None = None
    summary: str = ""
    usage: dict[str, Any] = Field(default_factory=dict)
    stopped_reason: str = "completed"


def _slug(text: str, *, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug or "run")[:max_len]


def new_coder_run_dir(topic: str) -> Path:
    """Create a fresh per-run workspace under workspace/coder_runs/."""
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    run_dir = CODER_RUNS_ROOT / f"{stamp}-{_slug(topic)}"
    resolve_output_dir(str(run_dir))
    (run_dir / "traces").mkdir(exist_ok=True)
    return run_dir.resolve()


def _usage_dict(usage: RunUsage | None) -> dict[str, Any]:
    if usage is None:
        return {}
    return asdict(usage)


def _collect_audio_paths(run_dir: Path) -> list[str]:
    audio_dir = run_dir / "audio"
    if not audio_dir.is_dir():
        return []
    return sorted(str(p.resolve()) for p in audio_dir.glob("*.wav"))


def _scene_name_from_manifest(manifest: dict) -> str | None:
    scene_file = manifest.get("scene_file")
    if not scene_file:
        last_write = manifest.get("last_write") or {}
        scene_file = last_write.get("scene_file")
    if not scene_file:
        return None
    return Path(scene_file).stem


def _compile_ok(manifest: dict) -> bool:
    last = manifest.get("last_compile") or {}
    if "ok" in last:
        return bool(last["ok"])
    for entry in reversed(manifest.get("history") or []):
        if entry.get("step") == "compile" and "ok" in entry:
            return bool(entry["ok"])
    return False


def dump_messages(run_dir: Path, messages: list[ModelMessage] | None) -> Path | None:
    """Write pydantic-ai message history for offline SFT."""
    traces_dir = run_dir / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)
    if not messages:
        return None
    path = traces_dir / "messages.json"
    path.write_bytes(ModelMessagesTypeAdapter.dump_json(messages, indent=2))
    return path


def arrange_coder_artifacts(
    run_dir: Path | str,
    *,
    messages: list[ModelMessage] | None = None,
    usage: RunUsage | None = None,
    summary: str = "",
    stopped_reason: str = "completed",
    request_limit: int | None = None,
    tool_calls_limit: int | None = None,
    user_prompt: str | None = None,
    prompt_index: int | None = None,
) -> CoderRunResult:
    """Read workspace tools output, dump traces, write run_result.json."""
    run_path = Path(run_dir).resolve()
    resolve_output_dir(str(run_path))
    traces_dir = run_path / "traces"
    traces_dir.mkdir(exist_ok=True)

    manifest = load_manifest(run_path)
    scene_name = _scene_name_from_manifest(manifest)
    scene_file = manifest.get("scene_file")
    code: str | None = None
    if scene_file:
        scene_path = (
            Path(scene_file)
            if Path(scene_file).is_absolute()
            else run_path / scene_file
        )
        if scene_path.is_file():
            code = scene_path.read_text(encoding="utf-8")
            scene_file = str(scene_path)

    compile_log = manifest.get("compile_log")
    if compile_log:
        log_path = (
            Path(compile_log)
            if Path(compile_log).is_absolute()
            else run_path / compile_log
        )
        compile_log = str(log_path) if log_path.is_file() else None
    else:
        candidate = run_path / "logs" / "compile.log"
        compile_log = str(candidate) if candidate.is_file() else None

    media_dir = run_path / "media"
    media_hint = (
        str(media_dir) if media_dir.is_dir() and any(media_dir.iterdir()) else None
    )

    traces_path = dump_messages(run_path, messages)
    usage_data = _usage_dict(usage)
    compile_ok = _compile_ok(manifest)

    from trajectory_recorder import default_recorder

    default_recorder.save_run(
        run_path,
        messages=messages,
        user_prompt=user_prompt,
        prompt_index=prompt_index,
        code=code,
        compile_ok=compile_ok,
        summary=summary,
        stopped_reason=stopped_reason,
        usage=usage_data,
    )

    meta = {
        "agent_name": "Code Agent",
        "stopped_reason": stopped_reason,
        "usage": usage_data,
        "limits": {
            "request_limit": request_limit,
            "tool_calls_limit": tool_calls_limit,
        },
        "export": {
            "local": "uv run python export_local_sft.py",
            "logfire": "uv run python export_coder_sft.py --days 30",
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }
    (traces_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    result = CoderRunResult(
        run_dir=str(run_path),
        scene_name=scene_name,
        scene_file=scene_file,
        code=code,
        compile_ok=compile_ok,
        compile_log_path=compile_log,
        audio_paths=_collect_audio_paths(run_path),
        media_hint=media_hint,
        manifest_path=str(run_path / "manifest.json"),
        traces_path=str(traces_path)
        if traces_path
        else str(traces_dir / "messages.json"),
        summary=summary or stopped_reason,
        usage=usage_data,
        stopped_reason=stopped_reason,
    )
    (run_path / "run_result.json").write_text(
        result.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return result
