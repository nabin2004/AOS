"""Recipe expanders — higher-level animation sugar."""

from __future__ import annotations

from collections.abc import Callable

from motiongram.core import Node, Scene
from motiongram.deeplearning.animators import AnimateAttribute
from motiongram.manifest.errors import ManifestValidationError
from motiongram.manifest.schema import RecipeSpec
from motiongram.manifest.time import parse_time

RecipeFn = Callable[[Scene, RecipeSpec, dict[str, Node]], None]


def _forward_pass_recipe(scene: Scene, recipe: RecipeSpec, node_map: dict[str, Node]) -> None:
    layers = recipe.layers
    if not layers:
        raise ManifestValidationError("ForwardPass recipe requires non-empty 'layers'")
    start = parse_time(recipe.start, field="recipe.start")
    duration = parse_time(recipe.duration, field="recipe.duration")
    step = duration / len(layers)
    for i, node_id in enumerate(layers):
        if node_id not in node_map:
            raise ManifestValidationError(f"ForwardPass: unknown layer id {node_id!r}")
        node = node_map[node_id]
        if not hasattr(node, "progress"):
            raise ManifestValidationError(
                f"ForwardPass: element {node_id!r} has no 'progress' attribute"
            )
        t0 = start + i * step
        t1 = start + (i + 1) * step
        scene.add_animation(t0, t1, node, AnimateAttribute("progress", 0.0, 1.0))


RECIPE_REGISTRY: dict[str, RecipeFn] = {
    "forwardpass": _forward_pass_recipe,
}


def expand_recipe(scene: Scene, recipe: RecipeSpec, node_map: dict[str, Node]) -> None:
    """Expand a scene-level recipe into timeline entries."""
    key = recipe.type.lower().replace("_", "")
    if key not in RECIPE_REGISTRY:
        known = ", ".join(sorted(RECIPE_REGISTRY))
        raise ManifestValidationError(f"unknown recipe type {recipe.type!r}; known: {known}")
    RECIPE_REGISTRY[key](scene, recipe, node_map)
