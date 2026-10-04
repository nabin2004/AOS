"""YAML manifest loader — declarative scenes without Python."""

from __future__ import annotations

from motiongram.manifest.compose import ComposedProgram, compose_program, merge_to_single_scene
from motiongram.manifest.errors import ManifestError, ManifestValidationError
from motiongram.manifest.loader import load_and_compose, load_manifest, render_manifest

__all__ = [
    "ComposedProgram",
    "ManifestError",
    "ManifestValidationError",
    "compose_program",
    "load_and_compose",
    "load_manifest",
    "merge_to_single_scene",
    "render_manifest",
]
