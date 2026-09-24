"""HITL Skills package: Bundles and adapts local skills as Pydantic AI Capabilities.

Loads copied local skills from app/skills/ into typed Pydantic AI Capabilities
with progressive disclosure and targeted tool execution.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import re

from pydantic_ai.capabilities import Capability

SKILLS_DIR = Path(__file__).resolve().parent


def read_skill_file(skill_name: str, relative_path: str = "SKILL.md") -> str:
    """Read a text file from a local skill directory."""
    path = SKILLS_DIR / skill_name / relative_path
    if not path.is_file():
        raise FileNotFoundError(f"Skill file not found: {path}")
    return path.read_text(encoding="utf-8")


def strip_yaml_frontmatter(text: str) -> str:
    """Strip YAML frontmatter (between --- delimiters) from markdown text."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text.strip()


def get_manim_composer_capability(*, defer_loading: bool = False) -> Capability:
    """Pydantic AI Capability for educational video composition (manim-composer)."""
    instructions = strip_yaml_frontmatter(read_skill_file("manim-composer"))

    cap = Capability(
        id="manim-composer",
        description="Comprehensive pedagogical video planning, narrative hooks, and scenes.md structure.",
        instructions=instructions,
        defer_loading=defer_loading,
    )

    @cap.tool_plain
    def read_composer_template() -> str:
        """Read the canonical scenes.md blueprint template for video structuring."""
        return read_skill_file("manim-composer", "templates/scenes-template.md")

    @cap.tool_plain
    def read_narrative_reference(reference_name: str) -> str:
        """Read composer reference guides ('narrative-patterns', 'visual-techniques', or 'scene-examples')."""
        clean_name = reference_name.removesuffix(".md").strip()
        filename = f"references/{clean_name}.md"
        try:
            return read_skill_file("manim-composer", filename)
        except FileNotFoundError:
            return (
                "Available composer references: 'narrative-patterns', "
                "'visual-techniques', 'scene-examples'."
            )

    return cap


def get_manimce_best_practices_capability(*, defer_loading: bool = False) -> Capability:
    """Pydantic AI Capability for Manim Community Edition best practices and rules."""
    instructions = strip_yaml_frontmatter(read_skill_file("manimce-best-practices"))

    cap = Capability(
        id="manimce-best-practices",
        description="Best practices, positioning, LaTeX styling, animations, and templates for Manim Community Edition.",
        instructions=instructions,
        defer_loading=defer_loading,
    )

    @cap.tool_plain
    def read_manim_rule(topic: str) -> str:
        """Read a specific Manim Community rule file (e.g. 'positioning', 'latex', 'camera', 'axes', 'graphing', 'updaters', 'grouping', 'animation-groups', 'scenes', 'shapes', 'text', 'timing', 'transform-animations')."""
        clean_topic = topic.removesuffix(".md").strip()
        filename = f"rules/{clean_topic}.md"
        try:
            return read_skill_file("manimce-best-practices", filename)
        except FileNotFoundError:
            available = [
                p.stem
                for p in (SKILLS_DIR / "manimce-best-practices" / "rules").glob("*.md")
            ]
            return f"Rule '{topic}' not found. Available rules: {', '.join(sorted(available))}"

    @cap.tool_plain
    def read_manim_example(category: str) -> str:
        """Read a working Manim example script (e.g. 'math_visualization', 'basic_animations', 'updater_patterns', 'graph_plotting', '3d_visualization')."""
        clean_cat = category.removesuffix(".py").strip()
        filename = f"examples/{clean_cat}.py"
        try:
            return read_skill_file("manimce-best-practices", filename)
        except FileNotFoundError:
            available = [
                p.stem
                for p in (SKILLS_DIR / "manimce-best-practices" / "examples").glob("*.py")
            ]
            return f"Example '{category}' not found. Available examples: {', '.join(sorted(available))}"

    @cap.tool_plain
    def read_scene_template(template_name: str) -> str:
        """Read a starter Manim scene template ('basic_scene', 'camera_scene', 'threed_scene')."""
        clean_tmpl = template_name.removesuffix(".py").strip()
        filename = f"templates/{clean_tmpl}.py"
        try:
            return read_skill_file("manimce-best-practices", filename)
        except FileNotFoundError:
            available = [
                p.stem
                for p in (SKILLS_DIR / "manimce-best-practices" / "templates").glob("*.py")
            ]
            return f"Template '{template_name}' not found. Available templates: {', '.join(sorted(available))}"

    return cap


def get_manim_render_capability(*, defer_loading: bool = False) -> Capability:
    """Pydantic AI Capability for Manim rendering and assembly troubleshooting."""
    instructions = strip_yaml_frontmatter(read_skill_file("manim-render"))

    cap = Capability(
        id="manim-render",
        description="Docker container rendering, FFmpeg video/narration assembly, and compiler/mount troubleshooting.",
        instructions=instructions,
        defer_loading=defer_loading,
    )

    @cap.tool_plain
    def get_render_troubleshooting_guide(issue: str = "general") -> str:
        """Troubleshoot Manim rendering, Docker mount errors, LaTeX package errors, or container cleanup."""
        return (
            "Render Troubleshooting Guide:\n"
            "1. Missing LaTeX packages: Use standard LaTeX notation (MathTex). Avoid non-standard \\usepackage dependencies.\n"
            "2. Scene Class Name: Ensure the class name exactly matches the command argument (e.g. `manim -ql scene.py ClassName`).\n"
            "3. Container Cleanup: For orphaned containers run `docker ps --filter 'name=aos-manim-' -q | ForEach-Object { docker rm -f $_ }`.\n"
            "4. Audio Assembly: Stitch audio with `ffmpeg -y -i scene.mp4 -i audio.wav -c:v copy -c:a aac -shortest out.mp4`.\n"
        )

    return cap


__all__ = [
    "SKILLS_DIR",
    "read_skill_file",
    "get_manim_composer_capability",
    "get_manimce_best_practices_capability",
    "get_manim_render_capability",
]
