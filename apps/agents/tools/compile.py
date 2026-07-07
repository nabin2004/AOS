from __future__ import annotations

import json
import textwrap
from typing import Any

from ir.manim_ir import (
    CAMERA_TARGET,
    Beat,
    Computation,
    Direction,
    EntityType,
    LectureIR,
    Operation,
    OperationType,
    RateFunction,
    Scene,
    SceneObject,
    SymbolSource,
)

from tools.compute import execute_computation
from tools.registry import aos_toolset

SUPPORTED_ENTITIES = {
    EntityType.CIRCLE,
    EntityType.LINE,
    EntityType.DOT,
    EntityType.ARROW,
    EntityType.MATH_TEX,
    EntityType.TEXT,
    EntityType.AXES,
    EntityType.NUMBER_PLANE,
    EntityType.COMPLEX_PLANE,
    EntityType.PARAMETRIC_CURVE,
    EntityType.GRAPH,
    EntityType.THREE_D_AXES,
    EntityType.SQUARE,
    EntityType.SPHERE,
}

SUPPORTED_OPS = {
    OperationType.CREATE,
    OperationType.WRITE,
    OperationType.FADE_IN,
    OperationType.MOVE,
    OperationType.SHIFT,
    OperationType.SCALE,
    OperationType.ROTATE,
    OperationType.HIGHLIGHT,
    OperationType.CIRCUMSCRIBE,
    OperationType.TRANSFORM_FROM_COPY,
    OperationType.FADE_OUT,
    OperationType.SET_CAMERA_ORIENTATION,
    OperationType.GROW,
}

RATE_FUNC_MAP = {
    RateFunction.LINEAR: "linear",
    RateFunction.SMOOTH: "smooth",
    RateFunction.EASE_IN_OUT: "there_and_back_with_pause",
    RateFunction.EASE_IN: "ease_in_sine",
    RateFunction.EASE_OUT: "ease_out_sine",
    RateFunction.RUSH_INTO: "rush_into",
    RateFunction.RUSH_FROM: "rush_from",
}

DIRECTION_MAP = {
    Direction.UP: "UP",
    Direction.DOWN: "DOWN",
    Direction.LEFT: "LEFT",
    Direction.RIGHT: "RIGHT",
    Direction.UL: "UL",
    Direction.UR: "UR",
    Direction.DL: "DL",
    Direction.DR: "DR",
}


def _py_str(value: str) -> str:
    return json.dumps(value)


def _rate_kw(op: Operation) -> str:
    if op.rate_func is None:
        return ""
    name = RATE_FUNC_MAP.get(op.rate_func, "smooth")
    return f", rate_func={name}"


def _color(style_color: str | None, default: str = "WHITE") -> str:
    if style_color:
        if style_color.startswith("#"):
            return f'"{style_color}"'
        return style_color
    return default


def _position_expr(obj: SceneObject, var_names: dict[str, str]) -> str:
    pos = obj.position
    if pos.next_to:
        ref = var_names.get(pos.next_to, pos.next_to)
        direction = DIRECTION_MAP.get(pos.direction or Direction.DOWN, "DOWN")
        return f".next_to({ref}, {direction}, buff={pos.buff})"
    return f".move_to([{pos.x}, {pos.y}, {pos.z}])"


def _emit_object(
    obj: SceneObject,
    var_names: dict[str, str],
    computation_data: dict[str, Any],
) -> tuple[str, str]:
    """Return (var_name, construction line) for a scene object."""
    var = var_names[obj.id]
    style = obj.style
    color = _color(style.color)
    pos_suffix = _position_expr(obj, var_names)

    if obj.entity_type == EntityType.CIRCLE:
        radius = obj.params.get("radius", 1.0)
        line = f"{var} = Circle(radius={radius}, color={color}){pos_suffix}"
    elif obj.entity_type == EntityType.LINE:
        line = f"{var} = Line(ORIGIN, RIGHT, color={color}){pos_suffix}"
    elif obj.entity_type == EntityType.DOT:
        line = f"{var} = Dot(color={color}){pos_suffix}"
        if style.glow:
            line += f"\n        {var}.set_glow_factor(2)"
    elif obj.entity_type == EntityType.ARROW:
        line = f"{var} = Arrow(ORIGIN, RIGHT, color={color}){pos_suffix}"
    elif obj.entity_type == EntityType.MATH_TEX:
        tex = obj.params.get("tex", "")
        line = f"{var} = MathTex({_py_str(tex)}, color={color}){pos_suffix}"
    elif obj.entity_type == EntityType.TEXT:
        text = obj.params.get("text", obj.params.get("tex", ""))
        line = f"{var} = Text({_py_str(text)}, color={color}){pos_suffix}"
    elif obj.entity_type == EntityType.AXES:
        x_range = obj.params.get("x_range", [-3, 3, 1])
        y_range = obj.params.get("y_range", [-3, 3, 1])
        line = (
            f"{var} = Axes(x_range={x_range}, y_range={y_range}, "
            f"x_length=6, y_length=4, axis_config={{'color': {color}}}){pos_suffix}"
        )
    elif obj.entity_type == EntityType.NUMBER_PLANE:
        line = f"{var} = NumberPlane(){pos_suffix}"
    elif obj.entity_type == EntityType.COMPLEX_PLANE:
        line = f"{var} = ComplexPlane(){pos_suffix}"
    elif obj.entity_type == EntityType.THREE_D_AXES:
        line = f"{var} = ThreeDAxes(){pos_suffix}"
    elif obj.entity_type == EntityType.SQUARE:
        side = obj.params.get("side_length", 2.0)
        line = f"{var} = Square(side_length={side}, color={color}){pos_suffix}"
    elif obj.entity_type == EntityType.SPHERE:
        radius = obj.params.get("radius", 1.0)
        line = f"{var} = Sphere(radius={radius}, color={color}){pos_suffix}"
    elif obj.entity_type == EntityType.GRAPH:
        fn = obj.params.get("function", "lambda x: x**2")
        axes_ref = var_names.get(obj.params.get("axes", ""), obj.params.get("axes", "axes"))
        line = f"{var} = {axes_ref}.plot({fn}, color={color})"
    elif obj.entity_type == EntityType.PARAMETRIC_CURVE:
        comp_id = obj.computation
        if comp_id and comp_id in computation_data:
            points = computation_data[comp_id]
            const_name = f"_{comp_id.upper()}_POINTS"
            line = (
                f"{var} = VMobject(color={color}, stroke_width={style.stroke_width})\n"
                f"        {var}.set_points_smoothly(np.array({const_name}))"
            )
        else:
            line = f"{var} = ParametricFunction(lambda t: np.array([t, t, 0]), t_range=[0, 1], color={color})"
    else:
        supported = ", ".join(sorted(e.value for e in SUPPORTED_ENTITIES))
        raise ValueError(
            f"unsupported entity_type {obj.entity_type.value!r} for object {obj.id!r}; "
            f"supported: {supported}"
        )

    if obj.fix_in_frame:
        line += f"\n        self.add_fixed_in_frame_mobjects({var})"

    return var, line


def _emit_animation(op: Operation, var_names: dict[str, str]) -> str:
    target = var_names.get(op.target, op.target)
    rt = f", run_time={op.run_time}" if op.run_time else ""
    rate = _rate_kw(op)

    if op.op == OperationType.CREATE:
        return f"Create({target}{rate}{rt})"
    if op.op == OperationType.WRITE:
        return f"Write({target}{rate}{rt})"
    if op.op == OperationType.FADE_IN:
        return f"FadeIn({target}{rate}{rt})"
    if op.op == OperationType.GROW:
        return f"GrowFromCenter({target}{rate}{rt})"
    if op.op == OperationType.FADE_OUT:
        return f"FadeOut({target}{rate}{rt})"
    if op.op == OperationType.HIGHLIGHT:
        return f"Indicate({target}{rate}{rt})"
    if op.op == OperationType.CIRCUMSCRIBE:
        return f"Circumscribe({target}{rate}{rt})"
    if op.op == OperationType.MOVE:
        dest = op.params.get("to", op.params.get("position", [0, 0, 0]))
        return f"{target}.animate.move_to({dest}{rate}{rt})"
    if op.op == OperationType.SHIFT:
        direction = op.params.get("direction", "UP")
        amount = op.params.get("amount", 1.0)
        return f"{target}.animate.shift({amount} * {direction}{rate}{rt})"
    if op.op == OperationType.SCALE:
        factor = op.params.get("factor", 1.2)
        return f"{target}.animate.scale({factor}{rate}{rt})"
    if op.op == OperationType.ROTATE:
        angle = op.params.get("angle", 3.14159 / 4)
        return f"Rotate({target}, angle={angle}{rate}{rt})"
    if op.op == OperationType.TRANSFORM_FROM_COPY:
        src = op.params.get("source") or op.params.get("from")
        src_var = var_names.get(src, src)
        return f"TransformFromCopy({src_var}, {target}{rate}{rt})"
    if op.op == OperationType.SET_CAMERA_ORIENTATION and op.target == CAMERA_TARGET:
        phi = op.params.get("phi", 0)
        theta = op.params.get("theta", 0)
        return f"self.set_camera_orientation(phi={phi}, theta={theta}{rt})"

    supported = ", ".join(sorted(o.value for o in SUPPORTED_OPS))
    raise ValueError(f"unsupported op {op.op.value!r}; supported: {supported}")


# Ops whose compiled form is already a full scene-method statement
# (e.g. `self.set_camera_orientation(...)`), not an Animation instance —
# these must never be passed to self.play()/AnimationGroup().
STATEMENT_OPS = {OperationType.SET_CAMERA_ORIENTATION}


def _compile_beat(beat: Beat, var_names: dict[str, str]) -> list[str]:
    lines: list[str] = []
    if not beat.animation_segment:
        if beat.hold_seconds > 0:
            lines.append(f"        self.wait({beat.hold_seconds})")
        return lines

    # Each group is ("play", [anim, ...]) for self.play()/AnimationGroup(),
    # or ("statement", expr) for a bare scene-method call like
    # self.set_camera_orientation(...), which is not an Animation and must
    # never be passed to self.play().
    groups: list[tuple[str, list[str]]] = []
    current: list[str] = []

    def flush() -> None:
        nonlocal current
        if current:
            groups.append(("play", current))
            current = []

    for op in beat.animation_segment:
        if op.op not in SUPPORTED_OPS and op.op not in STATEMENT_OPS:
            supported = ", ".join(sorted(o.value for o in SUPPORTED_OPS))
            raise ValueError(f"unsupported op {op.op.value!r}; supported: {supported}")

        emitted = _emit_animation(op, var_names)
        if op.op in STATEMENT_OPS:
            flush()
            groups.append(("statement", [emitted]))
            continue

        if op.with_previous and current:
            current.append(emitted)
        else:
            flush()
            current = [emitted]
    flush()

    for kind, group in groups:
        if kind == "statement":
            lines.append(f"        {group[0]}")
        elif len(group) == 1:
            lines.append(f"        self.play({group[0]})")
        else:
            joined = ", ".join(group)
            lines.append(f"        self.play(AnimationGroup({joined}, lag_ratio=0))")

    if beat.hold_seconds > 0:
        lines.append(f"        self.wait({beat.hold_seconds})")

    return lines


def _resolve_computations(scene: Scene) -> dict[str, list[list[float]]]:
    data: dict[str, list[list[float]]] = {}
    comp_by_id = {c.id: c for c in scene.computations}
    for obj in scene.scene_graph:
        if obj.computation and obj.computation in comp_by_id:
            comp = comp_by_id[obj.computation]
            if comp.id not in data:
                data[comp.id] = execute_computation(comp)
    return data


def compile_scene(scene: Scene) -> str:
    """Compile a Scene IR object to Manim Python source."""
    unsupported = [
        obj.entity_type.value
        for obj in scene.scene_graph
        if obj.entity_type not in SUPPORTED_ENTITIES
    ]
    if unsupported:
        supported = ", ".join(sorted(e.value for e in SUPPORTED_ENTITIES))
        raise ValueError(f"unsupported entity types: {unsupported}; supported: {supported}")

    var_names = {obj.id: obj.id for obj in scene.scene_graph}
    computation_data = _resolve_computations(scene)

    base_class = "ThreeDScene" if scene.is_3d else "Scene"
    lines = [
        f"class {scene.class_name}({base_class}):",
        '    """Auto-generated from AOS IR."""',
        "",
        "    def construct(self):",
    ]

    const_lines: list[str] = []
    for comp_id, points in computation_data.items():
        const_lines.append(f"_{comp_id.upper()}_POINTS = {points!r}")

    if const_lines:
        for cl in const_lines:
            lines.append(f"        {cl}")

    for obj in scene.scene_graph:
        _, construction = _emit_object(obj, var_names, computation_data)
        for subline in construction.split("\n"):
            lines.append(f"        {subline.strip()}")

    for beat in scene.beats:
        lines.extend(_compile_beat(beat, var_names))

    return "\n".join(lines) + "\n"


def compile_lecture(lecture: LectureIR) -> str:
    """Compile a full LectureIR to a single Manim Python module."""
    header = textwrap.dedent(
        '''\
        """Auto-generated AOS lecture — do not edit by hand."""
        from manim import *
        import numpy as np

        '''
    )

    scene_sources: list[str] = []
    for scene in lecture.scenes:
        scene_sources.append(compile_scene(scene))

    body = "\n\n".join(scene_sources)
    footer = textwrap.dedent(
        '''

        if __name__ == "__main__":
            pass
        '''
    )
    return header + body + footer


@aos_toolset.tool_plain
def compile_scene_to_manim(scene_json: str) -> str:
    """Compile a single Scene IR JSON object to Manim Python source code."""
    scene = Scene.model_validate_json(scene_json)
    header = "from manim import *\nimport numpy as np\n\n"
    return header + compile_scene(scene)


@aos_toolset.tool_plain
def compile_code_to_manim(lecture_ir_json: str) -> str:
    """Compile a full LectureIR JSON document to a multi-scene Manim Python module."""
    lecture = LectureIR.model_validate_json(lecture_ir_json)
    return compile_lecture(lecture)
