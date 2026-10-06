"""Compiler for translating ManimGram YAML/JSON specifications into ManimCE Python code."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from motiongram.manimgram.layout import render_layout_statements
from motiongram.manimgram.schema import (
    ManimGramScene,
    MobjectSpec,
    TimelineActionSpec,
    VoiceoverBlockSpec,
)
from motiongram.manimgram.selectors import EMBEDDED_SELECTOR_RESOLVER_CODE

TEMPLATES_DIR = Path(__file__).parent / "templates"
_REVEAL_ACTIONS = {"Create", "Write", "FadeIn"}
_REMOVE_ACTIONS = {"Unwrite", "FadeOut"}
_REPLACE_ACTIONS = {"ReplacementTransform", "TransformMatchingTex", "TransformMatchingShapes", "RoutedTransform"}


def _safe_mobject_id(value: str | None, known_ids: set[str]) -> str | None:
    """Only emit references to declared Python-identifier mobjects."""
    if not value:
        return None
    root = value.split(".", 1)[0]
    return root if root in known_ids and re.fullmatch(r"[A-Za-z_]\w*", root) else None


def _active_cleanup_lines(active: str, exclude: str | None = None) -> list[str]:
    condition = f"mob is not {exclude}" if exclude else "True"
    return [
        f"{active} = [mob for mob in {active} if any(mob is current for current in self.mobjects) and {condition}]",
        f"if {active}:",
        f"    self.play(*[FadeOut(mob) for mob in {active}])",
        f"{active} = []",
    ]


def _format_py_value(val: Any) -> str:
    """Format Python values into valid Python source code."""
    if isinstance(val, str):
        # Check if it's a known Manim constant like BLUE, UP, DEGREES
        if val in (
            "UP", "DOWN", "LEFT", "RIGHT", "UL", "UR", "DL", "DR", "IN", "OUT", "ORIGIN",
            "WHITE", "BLACK", "RED", "GREEN", "BLUE", "YELLOW", "ORANGE", "PURPLE",
            "PINK", "GREY", "GRAY", "TEAL", "GOLD", "MAROON", "LIGHT_GREY", "DARK_GREY"
        ):
            return val
        # Check if string starts with color hex #
        if val.startswith("#"):
            return f'"{val}"'
        # Regular string
        return f'"{val}"'
    elif isinstance(val, (int, float, bool)):
        return str(val)
    elif isinstance(val, list):
        items = ", ".join(_format_py_value(x) for x in val)
        return f"[{items}]"
    elif isinstance(val, tuple):
        items = ", ".join(_format_py_value(x) for x in val)
        return f"({items})"
    elif isinstance(val, dict):
        entries = ", ".join(f'"{k}": {_format_py_value(v)}' for k, v in val.items())
        return f"{{{entries}}}"
    return str(val)


def render_mobject_instantiation(mob: MobjectSpec) -> str:
    """Generate the constructor call for a mobject."""
    props = dict(mob.props)
    m_type = mob.type

    # Specific handling for common types
    if m_type in ("Matrix", "IntegerMatrix", "DecimalMatrix", "MobjectMatrix"):
        matrix_data = props.pop("matrix", [[0]])
        if "bracket_color" in props:
            b_color = props.pop("bracket_color")
            props["bracket_config"] = {"color": b_color}
        kwargs_parts = [f"{k}={_format_py_value(v)}" for k, v in props.items()]
        kwargs_str = f", {', '.join(kwargs_parts)}" if kwargs_parts else ""
        return f"{mob.id} = {m_type}({matrix_data}{kwargs_str})"

    elif m_type in ("MathTex", "Tex"):
        tex_content = props.pop("tex", props.pop("text", props.pop("expression", "")))
        kwargs_parts = [f"{k}={_format_py_value(v)}" for k, v in props.items()]
        kwargs_str = f", {', '.join(kwargs_parts)}" if kwargs_parts else ""
        return f'{mob.id} = {m_type}(r"{tex_content}"{kwargs_str})'

    elif m_type == "Text":
        text_content = props.pop("text", "")
        kwargs_parts = [f"{k}={_format_py_value(v)}" for k, v in props.items()]
        kwargs_str = f", {', '.join(kwargs_parts)}" if kwargs_parts else ""
        return f'{mob.id} = Text("{text_content}"{kwargs_str})'

    elif m_type == "Axes":
        x_range = props.pop("x_range", [-5, 5, 1])
        y_range = props.pop("y_range", [-3, 3, 1])
        kwargs_parts = [f"x_range={x_range}", f"y_range={y_range}"]
        kwargs_parts.extend(f"{k}={_format_py_value(v)}" for k, v in props.items())
        return f"{mob.id} = Axes({', '.join(kwargs_parts)})"

    elif m_type == "ThreeDAxes":
        x_range = props.pop("x_range", [-3, 3, 1])
        y_range = props.pop("y_range", [-3, 3, 1])
        z_range = props.pop("z_range", [-2, 2, 1])
        kwargs_parts = [f"x_range={x_range}", f"y_range={y_range}", f"z_range={z_range}"]
        kwargs_parts.extend(f"{k}={_format_py_value(v)}" for k, v in props.items())
        return f"{mob.id} = ThreeDAxes({', '.join(kwargs_parts)})"

    elif m_type == "Surface":
        resolution = props.pop("resolution", None)
        kwargs_parts = []
        if resolution:
            kwargs_parts.append(f"resolution=((10, 10) if PREVIEW else {tuple(resolution)})")
        else:
            kwargs_parts.append("resolution=((10, 10) if PREVIEW else (30, 30))")
        kwargs_parts.extend(f"{k}={_format_py_value(v)}" for k, v in props.items())
        return f"{mob.id} = Surface({', '.join(kwargs_parts)})"

    elif m_type == "DecimalNumber":
        val = props.pop("number", props.pop("value", 0))
        num_decimal_places = props.pop("num_decimal_places", 2)
        kwargs_parts = [f"number={val}", f"num_decimal_places={num_decimal_places}"]
        kwargs_parts.extend(f"{k}={_format_py_value(v)}" for k, v in props.items())
        return f"{mob.id} = DecimalNumber({', '.join(kwargs_parts)})"

    # Default constructor with keyword arguments
    kwargs_parts = [f"{k}={_format_py_value(v)}" for k, v in props.items()]
    return f"{mob.id} = {m_type}({', '.join(kwargs_parts)})"


def render_state_statements(mob_id: str, mob: MobjectSpec) -> list[str]:
    """Generate state initialization statements (e.g. opacity, visibility)."""
    stmts: list[str] = []
    if mob.state is not None:
        if not mob.state.visible or (mob.state.opacity is not None and mob.state.opacity == 0):
            stmts.append(f"{mob_id}.set_opacity(0)")
        elif mob.state.opacity is not None:
            stmts.append(f"{mob_id}.set_opacity({mob.state.opacity})")
        if mob.state.scale is not None:
            stmts.append(f"{mob_id}.scale({mob.state.scale})")
    return stmts


def render_action_code(action: TimelineActionSpec, action_idx: int) -> tuple[str, str]:
    """Generate execution code for a timeline action.
    
    Returns (action_name, python_code).
    """
    act = action.action

    if act == "WaitUntilBookmark":
        mark = action.mark or action.params.get("mark", "")
        return "WaitUntilBookmark", f'self.wait_until_bookmark("{mark}")'

    if act == "Wait":
        duration = action.duration if action.duration is not None else action.run_time
        if action.params.get("adaptive", False):
            return "Wait", f"self.wait({duration} * (0.25 if PREVIEW else 1.0))"
        return "Wait", f"self.wait({duration})"

    common_create_actions = (
        "Create", "Write", "Unwrite", "FadeIn", "FadeOut",
        "Circumscribe", "Indicate", "Wiggle", "Flash",
    )
    if act in common_create_actions:
        target = action.target or "None"
        run_time_arg = f", run_time={action.run_time}" if action.run_time != 1.0 else ""
        rate_arg = f", rate_func={action.rate_func}" if action.rate_func else ""
        return act, f"self.play({act}({target}{run_time_arg}{rate_arg}))"

    transform_actions = (
        "Transform", "ReplacementTransform", "TransformMatchingTex", "TransformMatchingShapes",
    )
    if act in transform_actions:
        src = action.source or "None"
        tgt = action.target or "None"
        run_time_arg = f", run_time={action.run_time}" if action.run_time != 1.0 else ""
        rate_arg = f", rate_func={action.rate_func}" if action.rate_func else ""
        return act, f"self.play({act}({src}, {tgt}{run_time_arg}{rate_arg}))"

    if act == "RoutedTransform":
        lines: list[str] = [f"anims_{action_idx} = []"]
        routes = action.routes or []
        for r_idx, route in enumerate(routes):
            # Parse from
            from_raw = route.from_selector
            if "." in from_raw:
                src_mob, src_sel = from_raw.split(".", 1)
            else:
                src_mob, src_sel = (action.source or "source"), from_raw

            # Parse to
            to_raw = route.to_selector
            if "." in to_raw:
                tgt_mob, tgt_sel = to_raw.split(".", 1)
            elif action.target and any(
                sel in to_raw for sel in ("[", "bracket", "axis", "term")
            ):
                tgt_mob, tgt_sel = action.target, to_raw
            else:
                tgt_mob, tgt_sel = to_raw, ""

            lines.append(f'src_{action_idx}_{r_idx} = resolve_submobject({src_mob}, "{src_sel}")')
            lines.append(f'tgt_{action_idx}_{r_idx} = resolve_submobject({tgt_mob}, "{tgt_sel}")')
            anim_type = route.animation or "ReplacementTransform"
            anim_stmt = (
                f"anims_{action_idx}.append("
                f"{anim_type}(src_{action_idx}_{r_idx}, tgt_{action_idx}_{r_idx}))"
            )
            lines.append(anim_stmt)

        run_time_arg = f", run_time={action.run_time}" if action.run_time != 1.0 else ""
        lines.append(f"self.play(*anims_{action_idx}{run_time_arg})")
        return "RoutedTransform", "\n".join(lines)

    if act == "CameraAction" or act in ("Orbit", "Focus", "Pan", "Zoom", "ResetView"):
        cam_type = action.params.get("type", act)
        if cam_type == "Orbit":
            rate = action.params.get("rate", 0.2)
            if action.params.get("adaptive", False):
                return (
                    "Orbit",
                    f"if not PREVIEW:\n"
                    f"    self.begin_ambient_camera_rotation(rate={rate})\n"
                    f"self.wait({action.run_time} * (0.25 if PREVIEW else 1.0))\n"
                    f"if not PREVIEW:\n"
                    f"    self.stop_ambient_camera_rotation()",
                )
            return (
                "Orbit",
                f"self.begin_ambient_camera_rotation(rate={rate})\n"
                f"self.wait({action.run_time})\n"
                f"self.stop_ambient_camera_rotation()",
            )
        elif cam_type == "Focus":
            zoom = action.params.get("zoom", 1.5)
            target = action.target or "ORIGIN"
            return (
                "Focus",
                f"self.move_camera(frame_center={target}, zoom={zoom}, run_time={action.run_time})",
            )
        elif cam_type in ("Pan", "Zoom"):
            kwargs = [f"run_time={action.run_time}"]
            if "phi" in action.params:
                kwargs.append(f"phi={action.params['phi']} * DEGREES")
            if "theta" in action.params:
                kwargs.append(f"theta={action.params['theta']} * DEGREES")
            if "zoom" in action.params:
                kwargs.append(f"zoom={action.params['zoom']}")
            return cam_type, f"self.move_camera({', '.join(kwargs)})"

    # Generic animation fallback
    target = action.target or ""
    return act, f"self.play({act}({target}), run_time={action.run_time})"


def compile_dsl(spec_data: str | dict[str, Any] | ManimGramScene) -> str:
    """Compile a ManimGram YAML/JSON/Dict specification into executable ManimCE Python code."""
    if isinstance(spec_data, str):
        raw_dict = yaml.safe_load(spec_data)
        scene_spec = ManimGramScene.model_validate(raw_dict)
    elif isinstance(spec_data, dict):
        scene_spec = ManimGramScene.model_validate(spec_data)
    elif isinstance(spec_data, ManimGramScene):
        scene_spec = spec_data
    else:
        raise TypeError(f"Unsupported spec input type: {type(spec_data)}")

    # Pre-render mobjects
    rendered_mobjects: list[dict[str, Any]] = []
    for mob in scene_spec.mobjects:
        rendered_mobjects.append({
            "id": mob.id,
            "type": mob.type,
            "instantiation_code": render_mobject_instantiation(mob),
            "layout_statements": render_layout_statements(mob.id, mob.layout),
            "state_statements": render_state_statements(mob.id, mob),
        })

    # Determine voiceover requirements
    has_voiceover = (scene_spec.scene.type == "VoiceoverScene") or any(
        isinstance(item, VoiceoverBlockSpec) or getattr(item, "type", None) == "voiceover_block"
        for item in scene_spec.timeline
    )
    voice = getattr(scene_spec.scene.config, "voice", "alba")
    backend = getattr(scene_spec.scene.config, "backend", "pocket-tts")
    model = getattr(scene_spec.scene.config, "model", None)
    cache_dir = getattr(scene_spec.scene.config, "cache_dir", "voiceover_cache")
    if scene_spec.scene.voiceover is not None:
        voice = scene_spec.scene.voiceover.voice or voice
        backend = scene_spec.scene.voiceover.backend or backend
        model = scene_spec.scene.voiceover.model or model
        cache_dir = scene_spec.scene.voiceover.cache_dir or cache_dir
    voiceover_config = {"voice": voice, "backend": backend, "model": model, "cache_dir": cache_dir}

    # Pre-render timeline actions
    rendered_timeline: list[dict[str, Any]] = []
    known_ids = {mob.id for mob in scene_spec.mobjects}
    for idx, item in enumerate(scene_spec.timeline):
        if isinstance(item, VoiceoverBlockSpec) or getattr(item, "type", None) == "voiceover_block":
            active = f"_motiongram_active_{idx}"
            block_lines = [
                f"{active} = []",
                "# MotionGram timeline mode: reveal-first; previous visuals are cleaned automatically.",
            ]
            for sub_idx, sub_act in enumerate(item.actions):
                # Bookmark waits outside the voiceover context can deadlock.
                if sub_act.action == "WaitUntilBookmark":
                    block_lines.append("# WaitUntilBookmark omitted in reveal-first mode.")
                    continue
                target = _safe_mobject_id(sub_act.target, known_ids)
                source = _safe_mobject_id(sub_act.source, known_ids)
                if sub_act.action in _REVEAL_ACTIONS and not sub_act.params.get("keep_previous", False):
                    block_lines.extend(_active_cleanup_lines(active, target))
                sub_name, sub_code = render_action_code(sub_act, f"{idx}_{sub_idx}")
                for line in sub_code.splitlines():
                    block_lines.append(line)
                if sub_act.action in _REMOVE_ACTIONS and target:
                    block_lines.append(f"{active} = [mob for mob in {active} if mob is not {target}]")
                elif sub_act.action in _REPLACE_ACTIONS and source:
                    block_lines.append(f"{active} = [mob for mob in {active} if mob is not {source}]")
                    if target:
                        block_lines.append(f"if not any(mob is {target} for mob in {active}): {active}.append({target})")
                elif sub_act.action not in ("Wait", "WaitUntilBookmark", "Transform") and target:
                    block_lines.append(f"if any(mob is {target} for mob in self.mobjects) and not any(mob is {target} for mob in {active}): {active}.append({target})")
            block_lines.extend([f"with self.voiceover(text={json.dumps(item.text)}) as tracker:", "    pass"])
            if idx < len(scene_spec.timeline) - 1:
                block_lines.extend(_active_cleanup_lines(active))
            rendered_timeline.append({
                "name": f"voiceover_block ({item.text[:28]}...)",
                "code": "\n".join(block_lines),
            })
        else:
            act_name, act_code = render_action_code(item, idx)
            rendered_timeline.append({
                "name": act_name,
                "code": act_code,
            })

    # Setup Jinja environment
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("manim_scene.py.jinja")

    rendered_py = template.render(
        scene=scene_spec.scene,
        camera=scene_spec.camera,
        rendered_mobjects=rendered_mobjects,
        rendered_timeline=rendered_timeline,
        embedded_resolver=EMBEDDED_SELECTOR_RESOLVER_CODE,
        has_voiceover=has_voiceover,
        voiceover_config=voiceover_config,
    )

    # Validate Python syntax via ast.parse
    try:
        ast.parse(rendered_py)
    except SyntaxError as e:
        msg = (
            f"Compiled Python code contains a syntax error at line {e.lineno}: {e.msg}\n\n"
            f"Generated code:\n{rendered_py}"
        )
        raise ValueError(msg) from e

    return rendered_py


def compile_file(input_file: Path, output_file: Path | None = None) -> Path:
    """Compile a ManimGram YAML/JSON file into a Python Manim script."""
    input_file = Path(input_file)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file '{input_file}' not found")

    content = input_file.read_text(encoding="utf-8")
    compiled_code = compile_dsl(content)

    resolved_output = input_file.with_suffix(".py") if output_file is None else Path(output_file)

    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    resolved_output.write_text(compiled_code, encoding="utf-8")
    return resolved_output
