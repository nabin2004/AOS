"""Harness settings from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

PermissionMode = Literal["default", "edit", "auto"]


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped or default


@dataclass(slots=True)
class Settings:
    model: str
    api_key: str | None
    harness_home: Path | None
    context_window_tokens: int | None
    compaction_threshold: float
    compaction_tail: int
    memory_digest_every: int
    memory_stub: bool
    test_model: bool
    permission_mode: PermissionMode
    manim_image: str
    docker_user: str | None
    manim_quality: str
    kitaru: bool
    logfire: bool
    ollama_base_url: str | None = None

    @classmethod
    def from_env(cls) -> Settings:
        window_raw = _env("EDUCLAW_CONTEXT_WINDOW")
        threshold_raw = _env("EDUCLAW_COMPACTION_THRESHOLD", "0.7")
        tail_raw = _env("EDUCLAW_COMPACTION_TAIL", "6")
        digest_raw = _env("EDUCLAW_MEMORY_DIGEST_EVERY", "3")
        harness_raw = _env("EDUCLAW_HARNESS_HOME")
        model = _env("EDUCLAW_MODEL", "ollama:hf.co/nabin2004/AOS-qwen3-8b-narrated-sft-gguf") or "ollama:hf.co/nabin2004/AOS-qwen3-8b-narrated-sft-gguf"
        mode = (_env("EDUCLAW_PERMISSION_MODE", "default") or "default").lower()
        if mode not in {"default", "edit", "auto"}:
            mode = "default"
        
        ollama_url = _env("OLLAMA_BASE_URL")
        if not ollama_url:
            if Path("/.dockerenv").is_file() or Path("/app").is_dir():
                ollama_url = "http://host.docker.internal:11434/v1"
            else:
                ollama_url = "http://localhost:11434/v1"
            os.environ["OLLAMA_BASE_URL"] = ollama_url
        elif "localhost" in ollama_url and (Path("/.dockerenv").is_file() or Path("/app").is_dir()):
            ollama_url = ollama_url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
            os.environ["OLLAMA_BASE_URL"] = ollama_url
        elif "OLLAMA_BASE_URL" not in os.environ:
            os.environ["OLLAMA_BASE_URL"] = ollama_url

        return cls(
            model=model,
            api_key=_env("EDUCLAW_API_KEY") or _env("OPENAI_API_KEY") or _env("ANTHROPIC_API_KEY"),
            harness_home=Path(harness_raw).expanduser() if harness_raw else None,
            context_window_tokens=int(window_raw) if window_raw else None,
            compaction_threshold=float(threshold_raw or "0.7"),
            compaction_tail=int(tail_raw or "6"),
            memory_digest_every=int(digest_raw or "3"),
            memory_stub=_truthy(_env("EDUCLAW_MEMORY_STUB", "0")),
            test_model=_truthy(_env("EDUCLAW_TEST_MODEL", "0")) or model == "test",
            permission_mode=mode,  # type: ignore[arg-type]
            manim_image=_env("EDUCLAW_MANIM_IMAGE", "manimcommunity/manim:stable")
            or "manimcommunity/manim:stable",
            docker_user=_env("EDUCLAW_DOCKER_USER"),
            manim_quality=_env("EDUCLAW_MANIM_QUALITY", "m") or "m",
            kitaru=_truthy(_env("EDUCLAW_KITARU", "0")),
            logfire=_truthy(_env("EDUCLAW_LOGFIRE", "0")) or bool(_env("LOGFIRE_TOKEN")),
            ollama_base_url=ollama_url,
        )


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def resolve_harness_home(cwd: Path, settings: Settings) -> Path:
    if settings.harness_home is not None:
        return settings.harness_home
    return cwd / ".aos"
