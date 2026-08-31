"""On-demand skill directories (pydantic-ai-skills)."""

from __future__ import annotations

from pathlib import Path

PACKAGE_SKILLS = Path(__file__).resolve().parent.parent / ".decode" / "skills"
PACKAGE_AGENT_SKILLS = Path(__file__).resolve().parent.parent / ".agents" / "skills"


def skill_directories(cwd: Path | None = None) -> list[str]:
    found: list[str] = []
    candidates = [PACKAGE_SKILLS, PACKAGE_AGENT_SKILLS]
    if cwd is not None:
        candidates.append(cwd / ".decode" / "skills")
        candidates.append(cwd / ".agents" / "skills")
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen or not resolved.is_dir():
            continue
        seen.add(resolved)
        found.append(str(resolved))
    return found

