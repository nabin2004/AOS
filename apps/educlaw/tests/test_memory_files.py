from pathlib import Path

from educlaw.memory.files import (
    MEMORY_TEMPLATE,
    append_memory_digest,
    ensure_memory_md,
    load_agents_md,
    load_memory_md,
)


def test_load_agents_md_missing(tmp_path: Path) -> None:
    assert load_agents_md(tmp_path) == ""


def test_load_agents_md(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("Prefer scenes under 30 seconds.", encoding="utf-8")
    assert "30 seconds" in load_agents_md(tmp_path)


def test_ensure_and_append_memory_md(tmp_path: Path) -> None:
    path = ensure_memory_md(tmp_path)
    assert path.is_file()
    assert MEMORY_TEMPLATE.splitlines()[0] in path.read_text(encoding="utf-8")
    append_memory_digest(tmp_path, "User wants a Fourier series scene")
    text = load_memory_md(tmp_path)
    assert "Fourier series" in text
