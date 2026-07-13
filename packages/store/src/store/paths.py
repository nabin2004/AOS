"""Locate the repo's data directory regardless of where a script is invoked from."""
from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "uv.lock").exists():
            return candidate
    return Path.cwd()


def data_dir() -> Path:
    d = repo_root() / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def lectures_dir() -> Path:
    d = data_dir() / "lectures"
    d.mkdir(parents=True, exist_ok=True)
    return d


def courses_dir() -> Path:
    d = data_dir() / "courses"
    d.mkdir(parents=True, exist_ok=True)
    return d


def players_dir() -> Path:
    d = data_dir() / "players"
    d.mkdir(parents=True, exist_ok=True)
    return d
