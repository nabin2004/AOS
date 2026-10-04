"""Disk caching utilities for scientific simulation data."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from motiongram.sci.solvers.base import DataResult


def get_sci_cache_dir() -> Path:
    """Return the base directory for cached scientific numerical data."""
    cache_dir = Path.cwd() / "cache" / "sci_data"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def save_cached_result(cache_key: str, result: DataResult, cache_dir: Path | None = None) -> Path:
    """Save DataResult to compressed .npz archive."""
    target_dir = cache_dir or get_sci_cache_dir()
    filepath = target_dir / f"{cache_key}.npz"
    metadata_json = json.dumps(result.metadata)
    np.savez_compressed(
        filepath,
        points=result.points,
        time=result.time if result.time is not None else np.array([]),
        metadata=np.array([metadata_json]),
        status=np.array([result.status]),
    )
    return filepath


def load_cached_result(cache_key: str, cache_dir: Path | None = None) -> DataResult | None:
    """Load DataResult from cache if it exists."""
    target_dir = cache_dir or get_sci_cache_dir()
    filepath = target_dir / f"{cache_key}.npz"
    if not filepath.exists():
        return None
    try:
        with np.load(filepath, allow_pickle=False) as data:
            points = data["points"]
            time_arr = data["time"]
            time = time_arr if time_arr.size > 0 else None
            metadata = {}
            if "metadata" in data and len(data["metadata"]) > 0:
                raw_meta = str(data["metadata"][0])
                if raw_meta:
                    metadata = json.loads(raw_meta)
            status = "success"
            if "status" in data and len(data["status"]) > 0:
                status = str(data["status"][0])
            return DataResult(points=points, time=time, metadata=metadata, status=status)
    except Exception:
        return None
