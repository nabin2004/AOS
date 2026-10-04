"""Compiler for ManimGram Slides transforming DeckSpec into ManimCE VoiceoverScenes."""

from __future__ import annotations

import json
from pathlib import Path

import jinja2

from motiongram.slides.schema import DeckSpec, SlideSpec, TimelineActionSpec
from motiongram.slides.templates.catalog import get_template_layout
from motiongram.slides.validation import validate_deck

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates_jinja"


def _resolve_target(target: str | None) -> str:
    """Resolve target names and diagram selectors into Python expressions."""
    if not target:
        return "None"
    if target.startswith("diagram."):
        selector = target[len("diagram."):].strip()
        return f'diagram.get_selector("{selector}")'
    return target


def _render_action(action: TimelineActionSpec) -> dict[str, str]:
    """Generate execution code for an action inside a slide."""
    lines: list[str] = []

    # 1. Bookmark trigger
    if action.at.startswith("bookmark:"):
        bm_name = action.at.split("bookmark:", 1)[1].strip()
        lines.append(f'self.wait_until_bookmark("{bm_name}")')

    target_expr = _resolve_target(action.target)
    source_expr = _resolve_target(action.source)
    rt_arg = f", run_time={action.run_time}" if action.run_time is not None else ""

    act = action.action.lower()
    if act == "write":
        lines.append(f"self.play(Write({target_expr}{rt_arg}))")
    elif act == "create":
        lines.append(f"self.play(Create({target_expr}{rt_arg}))")
    elif act in ("fade_in", "reveal_part"):
        lines.append(f"self.play(FadeIn({target_expr}{rt_arg}))")
    elif act == "fade_out":
        lines.append(f"self.play(FadeOut({target_expr}{rt_arg}))")
    elif act in ("highlight", "indicate"):
        lines.append(f"self.play(Indicate({target_expr}{rt_arg}))")
    elif act == "circumscribe":
        lines.append(f"self.play(Circumscribe({target_expr}{rt_arg}))")
    elif act == "transform":
        lines.append(f"self.play(Transform({source_expr}, {target_expr}{rt_arg}))")
    elif act == "replacement_transform":
        lines.append(f"self.play(ReplacementTransform({source_expr}, {target_expr}{rt_arg}))")
    elif act == "wait":
        duration = action.params.get("duration", action.run_time or 1.0)
        lines.append(f"self.wait({duration})")
    else:
        # Fallback to direct play call
        lines.append(f"self.play({action.action}({target_expr}{rt_arg}))")

    return {
        "name": f"{action.action} ({action.target or 'scene'})",
        "code": "\n".join(lines),
    }


def compile_slide(slide: SlideSpec, deck: DeckSpec) -> str:
    """Compile a single slide specification into executable ManimCE Python code."""
    # 1. Generate template layout
    layout = get_template_layout(slide, deck.style)
    mobjects_code = list(layout.mobjects_init_code)

    # 2. Add diagram instantiation if present
    if slide.diagram:
        comp_name = slide.diagram.component
        props_json = json.dumps(slide.diagram.props)
        mobjects_code.extend([
            f"diagram = {comp_name}(**{props_json})",
            "diagram.move_to(ORIGIN + DOWN * 0.2)",
        ])

    # 3. Compile timeline actions
    actions_to_render = slide.timeline if slide.timeline else layout.default_timeline
    rendered_actions = [_render_action(act) for act in actions_to_render]

    # 4. Check voiceover presence
    has_voiceover = bool(slide.narration and slide.narration.text.strip())
    voice = slide.narration.voice if (slide.narration and slide.narration.voice) else deck.voice

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    tmpl = env.get_template("slide_scene.py.jinja")

    # Sanitize slide id for Python class name
    safe_id = "".join(c if c.isalnum() else "_" for c in slide.id)
    class_name = f"Slide_{safe_id}"

    return tmpl.render(
        scene_class_name=class_name,
        has_voiceover=has_voiceover,
        voice=voice,
        cache_dir="voiceover_cache",
        background_color=deck.style.palette.background,
        mobjects_code=mobjects_code,
        narration_text=slide.narration.text if slide.narration else "",
        timeline_actions=rendered_actions,
    )


def compile_deck(deck: DeckSpec, output_dir: Path | None = None) -> list[Path]:
    """Compile a full presentation deck into individual Python slide scene files."""
    is_valid, errors, _ = validate_deck(deck)
    if not is_valid:
        raise ValueError("DeckSpec validation failed with errors:\n" + "\n".join(errors))

    base_dir = output_dir or Path(f"output/decks/{deck.id}")
    slides_dir = base_dir / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

    generated_paths: list[Path] = []
    for idx, slide in enumerate(deck.slides):
        safe_id = "".join(c if c.isalnum() else "_" for c in slide.id)
        out_file = slides_dir / f"slide_{idx:03d}_{safe_id}.py"
        script_code = compile_slide(slide, deck)
        out_file.write_text(script_code, encoding="utf-8")
        generated_paths.append(out_file)

    return generated_paths
