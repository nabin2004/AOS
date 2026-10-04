"""Component, animation, easing, and recipe registries for YAML manifests."""

from __future__ import annotations

import dataclasses
import inspect
from collections.abc import Callable
from typing import Any

from motiongram.animate import (
    Blur,
    CameraPan,
    CameraZoom,
    CircleOutline,
    Delay,
    FadeIn,
    FadeOut,
    MoveAlongPath,
    MoveArc,
    MoveX,
    MoveY,
    Parallel,
    Rotate,
    ScaleX,
    ScaleY,
    Sequence,
    SquashStretch,
    TimeScale,
    smoothstep,
)
from motiongram.core import Circle, Node, Scene
from motiongram.deeplearning.animators import AnimateAttribute, AnimateIntAttribute
from motiongram.easing import (
    ease_in_cubic,
    ease_in_out_cubic,
    ease_in_out_quad,
    ease_in_quad,
    ease_out_cubic,
    ease_out_quad,
    linear,
)
from motiongram.form import Cube, Cylinder, Sphere
from motiongram.manifest.errors import ManifestValidationError
from motiongram.shapes import (
    Arc,
    BezierCurve,
    Ellipse,
    Line,
    Path,
    Polygon,
    Rectangle,
    RegularPolygon,
    Sector,
    SemiCircle,
)
from motiongram.text import CodeBlock, MathExpr, Text

AnimationBuilder = Callable[[Scene, Node, dict[str, Any], dict[str, Node]], Any]

EASING_REGISTRY: dict[str, Callable[[float], float]] = {
    "linear": linear,
    "smoothstep": smoothstep,
    "ease_in_quad": ease_in_quad,
    "ease_out_quad": ease_out_quad,
    "ease_in_out_quad": ease_in_out_quad,
    "ease_in_cubic": ease_in_cubic,
    "ease_out_cubic": ease_out_cubic,
    "ease_in_out_cubic": ease_in_out_cubic,
}


def _discover_components() -> dict[str, type[Node]]:
    """Build type-name → Node subclass registry from core and deeplearning exports."""
    import motiongram.deeplearning as dl

    registry: dict[str, type[Node]] = {
        "Node": Node,
        "Circle": Circle,
        "Line": Line,
        "Polygon": Polygon,
        "BezierCurve": BezierCurve,
        "Arc": Arc,
        "Sector": Sector,
        "SemiCircle": SemiCircle,
        "Path": Path,
        "Rectangle": Rectangle,
        "Ellipse": Ellipse,
        "RegularPolygon": RegularPolygon,
        "Sphere": Sphere,
        "Cube": Cube,
        "Cylinder": Cylinder,
        "Text": Text,
        "MathExpr": MathExpr,
        "CodeBlock": CodeBlock,
    }
    for name in dl.__all__:
        if name in ("AnimateAttribute", "AnimateIntAttribute"):
            continue
        obj = getattr(dl, name, None)
        if inspect.isclass(obj) and issubclass(obj, Node):
            registry[name] = obj
    return registry


COMPONENT_REGISTRY: dict[str, type[Node]] = _discover_components()


def _resolve_target(
    scene: Scene,
    anim: dict[str, Any],
    node_map: dict[str, Node],
    *,
    default: Node | None = None,
) -> Node:
    target_ref = anim.get("target")
    if target_ref in (None, "scene"):
        return scene.root
    if not isinstance(target_ref, str):
        raise ManifestValidationError(f"animation target must be element id or 'scene', got {target_ref!r}")
    if target_ref not in node_map:
        raise ManifestValidationError(f"unknown animation target id: {target_ref!r}")
    return node_map[target_ref]


def _build_inner_animator(
    scene: Scene,
    target: Node,
    anim: dict[str, Any],
    node_map: dict[str, Node],
) -> Any:
    anim_type = anim.get("type")
    if not isinstance(anim_type, str):
        raise ManifestValidationError("animation requires string 'type'")
    key = anim_type.lower()
    if key not in ANIMATION_BUILDERS:
        known = ", ".join(sorted(ANIMATION_BUILDERS))
        raise ManifestValidationError(f"unknown animation type {anim_type!r}; known: {known}")
    return ANIMATION_BUILDERS[key](scene, target, anim, node_map)


def _wrap_easing(animator: Any, anim: dict[str, Any]) -> Any:
    easing_name = anim.get("easing")
    if easing_name is None:
        return animator
    if not isinstance(easing_name, str):
        raise ManifestValidationError(f"easing must be a string, got {easing_name!r}")
    ease_key = easing_name.lower()
    if ease_key not in EASING_REGISTRY:
        known = ", ".join(sorted(EASING_REGISTRY))
        raise ManifestValidationError(f"unknown easing {easing_name!r}; known: {known}")
    return TimeScale(animator, ease=EASING_REGISTRY[ease_key])


def build_animator(
    scene: Scene,
    target: Node,
    anim: dict[str, Any],
    node_map: dict[str, Node],
) -> Any:
    """Build an animator, optionally wrapped with per-animation easing."""
    inner = _build_inner_animator(scene, target, anim, node_map)
    return _wrap_easing(inner, anim)


def _build_move_x(_s: Scene, _t: Node, anim: dict[str, Any], _m: dict[str, Node]) -> MoveX:
    return MoveX(float(anim["from"]), float(anim["to"]))


def _build_move_y(_s: Scene, _t: Node, anim: dict[str, Any], _m: dict[str, Node]) -> MoveY:
    return MoveY(float(anim["from"]), float(anim["to"]))


def _build_fade_in(_s: Scene, _t: Node, anim: dict[str, Any], _m: dict[str, Node]) -> FadeIn:
    return FadeIn(float(anim.get("from", 0.0)), float(anim.get("to", 1.0)))


def _build_fade_out(_s: Scene, _t: Node, anim: dict[str, Any], _m: dict[str, Node]) -> FadeOut:
    return FadeOut(float(anim.get("from", 1.0)), float(anim.get("to", 0.0)))


def _build_scale_x(_s: Scene, _t: Node, anim: dict[str, Any], _m: dict[str, Node]) -> ScaleX:
    return ScaleX(float(anim["from"]), float(anim["to"]))


def _build_scale_y(_s: Scene, _t: Node, anim: dict[str, Any], _m: dict[str, Node]) -> ScaleY:
    return ScaleY(float(anim["from"]), float(anim["to"]))


def _build_rotate(_s: Scene, _t: Node, anim: dict[str, Any], _m: dict[str, Node]) -> Rotate:
    return Rotate(float(anim["from"]), float(anim["to"]))


def _build_blur(_s: Scene, _t: Node, anim: dict[str, Any], _m: dict[str, Node]) -> Blur:
    return Blur(float(anim.get("from", 0.0)), float(anim.get("to", 8.0)))


def _build_circle_outline(_s: Scene, _t: Node, _anim: dict[str, Any], _m: dict[str, Node]) -> CircleOutline:
    return CircleOutline()


def _build_animate_attribute(_s: Scene, _t: Node, anim: dict[str, Any], _m: dict[str, Node]) -> AnimateAttribute:
    return AnimateAttribute(str(anim["attribute"]), float(anim["from"]), float(anim["to"]))


def _build_animate_int_attribute(_s: Scene, _t: Node, anim: dict[str, Any], _m: dict[str, Node]) -> AnimateIntAttribute:
    return AnimateIntAttribute(str(anim["attribute"]), int(anim["from"]), int(anim["to"]))


def _build_camera_pan(scene: Scene, _t: Node, anim: dict[str, Any], _m: dict[str, Node]) -> CameraPan:
    fr = anim.get("from", [0.0, 0.0])
    to = anim.get("to", [0.0, 0.0])
    if not isinstance(fr, list | tuple) or len(fr) != 2:
        raise ManifestValidationError("camera_pan 'from' must be [x, y]")
    if not isinstance(to, list | tuple) or len(to) != 2:
        raise ManifestValidationError("camera_pan 'to' must be [x, y]")
    return CameraPan(scene, float(fr[0]), float(fr[1]), float(to[0]), float(to[1]))


def _build_camera_zoom(scene: Scene, _t: Node, anim: dict[str, Any], _m: dict[str, Node]) -> CameraZoom:
    return CameraZoom(scene, float(anim.get("from", 1.0)), float(anim.get("to", 1.4)))


def _build_move_arc(_s: Scene, _t: Node, anim: dict[str, Any], _m: dict[str, Node]) -> MoveArc:
    return MoveArc(
        float(anim["x0"]),
        float(anim["y0"]),
        float(anim["x1"]),
        float(anim["y1"]),
        float(anim.get("arc_height", 0.0)),
    )


def _build_move_along_path(_s: Scene, _t: Node, anim: dict[str, Any], _m: dict[str, Node]) -> MoveAlongPath:
    points = anim.get("points", [])
    if not isinstance(points, list):
        raise ManifestValidationError("move_along_path points must be a list of [x, y]")
    parsed = [(float(p[0]), float(p[1])) for p in points]
    return MoveAlongPath(parsed)


def _build_squash_stretch(_s: Scene, _t: Node, anim: dict[str, Any], _m: dict[str, Node]) -> SquashStretch:
    return SquashStretch(float(anim.get("amount", 0.35)), str(anim.get("axis", "y")))


def _build_parallel(scene: Scene, target: Node, anim: dict[str, Any], node_map: dict[str, Node]) -> Parallel:
    children = anim.get("animations", [])
    if not isinstance(children, list):
        raise ManifestValidationError("parallel requires 'animations' list")
    built = [_build_inner_animator(scene, target, c, node_map) for c in children]
    return Parallel(*built)


def _build_sequence(scene: Scene, target: Node, anim: dict[str, Any], node_map: dict[str, Node]) -> Sequence:
    children = anim.get("animations", [])
    if not isinstance(children, list):
        raise ManifestValidationError("sequence requires 'animations' list")
    built = [_build_inner_animator(scene, target, c, node_map) for c in children]
    return Sequence(*built)


def _build_delay(scene: Scene, target: Node, anim: dict[str, Any], node_map: dict[str, Node]) -> Delay:
    inner_spec = anim.get("animation")
    if not isinstance(inner_spec, dict):
        raise ManifestValidationError("delay requires nested 'animation' object")
    inner = _build_inner_animator(scene, target, inner_spec, node_map)
    return Delay(inner, float(anim.get("window_start", 0.0)), float(anim.get("window_end", 1.0)))


ANIMATION_BUILDERS: dict[str, AnimationBuilder] = {
    "move_x": _build_move_x,
    "move_y": _build_move_y,
    "fade_in": _build_fade_in,
    "fade_out": _build_fade_out,
    "scale_x": _build_scale_x,
    "scale_y": _build_scale_y,
    "rotate": _build_rotate,
    "blur": _build_blur,
    "circle_outline": _build_circle_outline,
    "animate_attribute": _build_animate_attribute,
    "animate_int_attribute": _build_animate_int_attribute,
    "camera_pan": _build_camera_pan,
    "camera_zoom": _build_camera_zoom,
    "move_arc": _build_move_arc,
    "move_along_path": _build_move_along_path,
    "squash_stretch": _build_squash_stretch,
    "parallel": _build_parallel,
    "sequence": _build_sequence,
    "delay": _build_delay,
}


def instantiate_node(type_name: str, properties: dict[str, Any]) -> Node:
    """Construct a Node subclass from registry type name and properties."""
    if type_name not in COMPONENT_REGISTRY:
        known = ", ".join(sorted(COMPONENT_REGISTRY))
        raise ManifestValidationError(f"unknown component type {type_name!r}; known: {known}")
    cls = COMPONENT_REGISTRY[type_name]
    fields = {f.name for f in dataclasses.fields(cls)}
    kwargs = {k: v for k, v in properties.items() if k in fields}
    return cls(**kwargs)
