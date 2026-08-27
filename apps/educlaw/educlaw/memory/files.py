"""Static AGENTS.md / MEMORY.md companions to the Dagestan graph."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

MEMORY_TEMPLATE = """# MEMORY.md

Human-readable notes for this workspace. The source of truth for extracted
facts is the Dagestan temporal graph at `.aos/memory/graph.json`.

Digests from the harness are appended below.
"""


def load_agents_md(cwd: Path) -> str:
    path = cwd / "AGENTS.md"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def load_memory_md(cwd: Path) -> str:
    path = cwd / "MEMORY.md"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def ensure_memory_md(cwd: Path) -> Path:
    path = cwd / "MEMORY.md"
    if not path.exists():
        path.write_text(MEMORY_TEMPLATE, encoding="utf-8")
    return path


def append_memory_digest(cwd: Path, digest: str) -> None:
    path = ensure_memory_md(cwd)
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    block = f"\n- ({stamp}) {digest.strip()}\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(block)
