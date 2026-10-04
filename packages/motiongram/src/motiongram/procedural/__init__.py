"""Procedural manifests and preset builders (**optional**, unstable).

Authors should import explicitly, e.g. ``from motiongram.procedural import …``.
This subpackage is **not** re-exported from ``motiongram`` top-level.
"""

from motiongram.procedural.rainy_landscape import (
    LandscapeAnimationSpec,
    LandscapeTrackHandles,
    RainyLandscapeManifest,
    apply_rainy_landscape_animations,
    default_rainy_landscape_manifest,
    materialize_rainy_landscape,
    resting_anchor_y,
)

__all__ = (
    "LandscapeAnimationSpec",
    "LandscapeTrackHandles",
    "RainyLandscapeManifest",
    "apply_rainy_landscape_animations",
    "default_rainy_landscape_manifest",
    "materialize_rainy_landscape",
    "resting_anchor_y",
)
