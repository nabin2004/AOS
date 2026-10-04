"""Load and validate YAML manifest files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from motiongram.core import Scene
from motiongram.manifest.compose import ComposedProgram, compose_program
from motiongram.manifest.errors import ManifestValidationError
from motiongram.manifest.schema import ManifestDocument


def load_manifest(path: Path | str) -> ManifestDocument:
    """Parse and validate a YAML manifest file."""
    manifest_path = Path(path).expanduser().resolve()
    if not manifest_path.is_file():
        raise ManifestValidationError(f"manifest not found: {manifest_path}")

    try:
        raw_text = manifest_path.read_text(encoding="utf-8")
        data: Any = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ManifestValidationError(f"invalid YAML in {manifest_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ManifestValidationError("manifest root must be a mapping")

    try:
        return ManifestDocument.model_validate(data)
    except ValidationError as exc:
        raise ManifestValidationError(str(exc)) from exc


def load_and_compose(path: Path | str) -> ComposedProgram:
    """Load manifest and compose into render-ready program."""
    manifest_path = Path(path).expanduser().resolve()
    doc = load_manifest(manifest_path)
    return compose_program(doc, base_dir=manifest_path.parent)


def render_manifest(path: Path | str) -> tuple[ComposedProgram, Scene]:
    """Load, compose, and merge to a single Scene."""
    from motiongram.manifest.compose import merge_to_single_scene

    program = load_and_compose(path)
    scene = merge_to_single_scene(program)
    return program, scene
