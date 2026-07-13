from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "workspace" / "coder"


def resolve_output_dir(output_dir: str | None = None) -> Path:
    path = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    path.mkdir(parents=True, exist_ok=True)
    (path / "logs").mkdir(exist_ok=True)
    (path / "audio").mkdir(exist_ok=True)
    return path.resolve()


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
