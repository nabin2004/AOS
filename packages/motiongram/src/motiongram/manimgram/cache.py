"""Content-addressed caching engine for ManimGram renders."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

# Version constants tracking cache compatibility
CACHE_ENGINE_VERSION = "1.0.0"
COMPILER_VERSION = "0.1.0"


def canonicalize_spec(content: str) -> str:
    """Normalize YAML/JSON content to a deterministic, canonical JSON representation.

    Keys are recursively sorted and non-semantic whitespace is stripped.
    """
    try:
        data = yaml.safe_load(content)
        if isinstance(data, (dict, list)):
            return json.dumps(data, sort_keys=True, separators=(",", ":"))
    except Exception:
        pass
    # Fallback to normalized raw text if not structured YAML/JSON
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    return "\n".join(lines)


def get_manim_version() -> str:
    """Safely obtain installed Manim version."""
    try:
        import manim
        return getattr(manim, "__version__", "unknown")
    except Exception:
        return "unknown"


def compute_cache_key(
    spec_content: str,
    quality: str = "ql",
    mode: str = "video",
    custom_res: tuple[int, int] | None = None,
    fps: float | None = None,
    seed: int = 42,
) -> str:
    """Compute a deterministic SHA-256 cache key for a render request.

    Incorporates:
    - Canonical spec content
    - Target quality level (e.g. ql, qm, qh, qk)
    - Render mode ('video' or 'still')
    - Custom resolution/framerate if overridden
    - Global random seed
    - Compiler and Manim version signatures
    """
    canonical_spec = canonicalize_spec(spec_content)
    manim_version = get_manim_version()

    key_payload = {
        "spec": canonical_spec,
        "quality": quality,
        "mode": mode,
        "custom_res": custom_res,
        "fps": fps,
        "seed": seed,
        "cache_version": CACHE_ENGINE_VERSION,
        "compiler_version": COMPILER_VERSION,
        "manim_version": manim_version,
    }

    serialized = json.dumps(key_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass
class CacheEntry:
    """Represents a cached render artifact."""
    cache_key: str
    artifact_path: Path
    artifact_type: str  # "video" or "image"
    manifest_path: Path
    metadata: dict[str, Any]


def get_cached_entry(cache_dir: Path, cache_key: str) -> CacheEntry | None:
    """Look up an existing artifact in the content-addressed cache."""
    entry_dir = cache_dir / cache_key
    manifest_path = entry_dir / "manifest.json"

    if not manifest_path.is_file():
        return None

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rel_artifact = manifest.get("artifact_file")
        if not rel_artifact:
            return None

        artifact_path = entry_dir / rel_artifact
        if not artifact_path.is_file() or artifact_path.stat().st_size == 0:
            return None

        return CacheEntry(
            cache_key=cache_key,
            artifact_path=artifact_path,
            artifact_type=manifest.get("artifact_type", "video"),
            manifest_path=manifest_path,
            metadata=manifest,
        )
    except Exception:
        return None


def store_cached_entry(
    cache_dir: Path,
    cache_key: str,
    source_artifact: Path,
    artifact_type: str = "video",
    script_content: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> CacheEntry:
    """Store a rendered artifact into the content-addressed cache directory."""
    entry_dir = cache_dir / cache_key
    entry_dir.mkdir(parents=True, exist_ok=True)

    dest_artifact = entry_dir / source_artifact.name
    shutil.copy2(source_artifact, dest_artifact)

    if script_content is not None:
        (entry_dir / "scene.py").write_text(script_content, encoding="utf-8")

    manifest_data = {
        "cache_key": cache_key,
        "artifact_file": source_artifact.name,
        "artifact_type": artifact_type,
        "created_at": datetime.now(UTC).isoformat(),
        "file_size": dest_artifact.stat().st_size,
        "compiler_version": COMPILER_VERSION,
        "manim_version": get_manim_version(),
    }
    if extra_metadata:
        manifest_data.update(extra_metadata)

    manifest_path = entry_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    return CacheEntry(
        cache_key=cache_key,
        artifact_path=dest_artifact,
        artifact_type=artifact_type,
        manifest_path=manifest_path,
        metadata=manifest_data,
    )
