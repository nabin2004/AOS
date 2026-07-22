from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

AGENTS_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = AGENTS_ROOT / "workspace"
DEFAULT_OUTPUT_DIR = WORKSPACE_ROOT / "coder"
# Legacy/accidental run dir used by some web sessions; kept allowlisted.
LEGACY_OUTPUT_DIR = AGENTS_ROOT / "output"

_ALLOWED_ROOTS = (WORKSPACE_ROOT, LEGACY_OUTPUT_DIR)


class OutputDirError(ValueError):
    """Raised when output_dir is outside the allowlisted coder workspace roots."""


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _candidate_path(output_dir: str | None) -> Path:
    if output_dir is None or not str(output_dir).strip():
        return DEFAULT_OUTPUT_DIR

    raw = str(output_dir).strip()
    path = Path(raw)

    # Bare relative names like "output" or "coder" map under workspace/.
    if not path.is_absolute():
        # Explicit workspace-relative paths: workspace/coder_runs/...
        if raw.startswith("workspace/") or raw == "workspace":
            return AGENTS_ROOT / path
        return WORKSPACE_ROOT / path

    return path


def resolve_output_dir(output_dir: str | None = None) -> Path:
    """
    Resolve and create a coder workspace directory.

    Allowed locations (after resolve):
      - apps/agents/workspace/**  (default: workspace/coder)
      - apps/agents/output/**     (legacy allowlist)

    Relative paths like ``output`` become ``workspace/output``.
    Absolute paths outside the allowlist (e.g. ``/workspace``) raise OutputDirError.
    """
    path = _candidate_path(output_dir).resolve()

    if not any(_is_under(path, root) for root in _ALLOWED_ROOTS):
        allowed = ", ".join(str(r) for r in _ALLOWED_ROOTS)
        raise OutputDirError(
            f"output_dir must be under {allowed} "
            f"(got {path!s}). Omit output_dir to use the default "
            f"{DEFAULT_OUTPUT_DIR}, or pass a path under workspace/."
        )

    path.mkdir(parents=True, exist_ok=True)
    (path / "logs").mkdir(exist_ok=True)
    (path / "audio").mkdir(exist_ok=True)
    return path


def scene_file_path(output_dir: Path, scene_name: str = "scene") -> Path:
    name = (scene_name or "scene").strip()
    if not name.endswith(".py"):
        name = f"{name}.py"
    return output_dir / name


def load_manifest(output_dir: Path) -> dict:
    manifest_path = output_dir / "manifest.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "output_dir": str(output_dir),
        "scene_file": None,
        "compile_log": None,
        "last_write": None,
        "last_compile": None,
        "last_narration": None,
        "history": [],
    }


def save_manifest(output_dir: Path, manifest: dict) -> Path:
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def record_step(output_dir: Path, step: str, payload: dict) -> dict:
    manifest = load_manifest(output_dir)
    manifest["history"].append(
        {
            "step": step,
            "timestamp": datetime.now(UTC).isoformat(),
            **payload,
        }
    )
    save_manifest(output_dir, manifest)
    return manifest


def result_json(**fields) -> str:
    return json.dumps(fields, indent=2)
