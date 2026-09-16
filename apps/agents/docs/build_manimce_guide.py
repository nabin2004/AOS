#!/usr/bin/env python3
"""Build a unified single-file ManimCE Master Guide from adithya-s-k/manim_skill.

Extracts all ManimCE best practices, rules, templates, and examples, assembling them
into a single, beautifully organized Markdown reference file.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SOURCE_BASE = Path(r"C:\Users\nabin\.gemini\antigravity-ide\brain\4ad803cf-15c4-49a0-a0c9-f4452d9cfe40\scratch\manim_skill\skills\manimce-best-practices")
OUTPUT_FILE = Path(r"C:\Users\nabin\Desktop\myall\AOS\apps\agents\docs\MANIMCE_SKILL.md")


def strip_frontmatter(content: str) -> str:
    """Strip YAML frontmatter (--- ... ---) from start of markdown."""
    content = content.strip()
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return content


def read_file_safe(path: Path) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def build_unified_markdown() -> str:
    sections = []

    # Header
    sections.append("""# Manim Community Edition (ManimCE) — Complete Unified Skill Guide

> **Source:** Synthesized and unified from [`adithya-s-k/manim_skill`](https://github.com/adithya-s-k/manim_skill) (`manimce-best-practices`).
> **Target Engine:** Manim Community Edition (`manim` / ManimCE `>= v0.18.0`).
> **Purpose:** Single-file comprehensive cheatsheet and best-practices reference for creating high-quality, executable mathematical animations.

---

## Table of Contents

1. [Overview & Core Principles](#1-overview--core-principles)
2. [Scene Fundamentals & Runtime Configuration](#2-scene-fundamentals--runtime-configuration)
   - [2.1 Scene Construction (`rules/scenes.md`)](#21-scene-construction)
   - [2.2 Configuration & Flags (`rules/config.md`)](#22-configuration--flags)
   - [2.3 CLI Usage & Output Management (`rules/cli.md`)](#23-cli-usage--output-management)
   - [2.4 Timing, Pacing & Audio Sync (`rules/timing.md`)](#24-timing-pacing--audio-sync)
3. [Mobjects, Geometry & Styling](#3-mobjects-geometry--styling)
   - [3.1 Mobject Fundamentals (`rules/mobjects.md`)](#31-mobject-fundamentals)
   - [3.2 Positioning, Alignment & Coordinates (`rules/positioning.md`)](#32-positioning-alignment--coordinates)
   - [3.3 Grouping with VGroup (`rules/grouping.md`)](#33-grouping-with-vgroup)
   - [3.4 Colors & Palettes (`rules/colors.md`)](#34-colors--palettes)
   - [3.5 Visual Styling & Strokes (`rules/styling.md`)](#35-visual-styling--strokes)
   - [3.6 2D Shapes & Geometry (`rules/shapes.md`)](#36-2d-shapes--geometry)
   - [3.7 Lines, Vectors & Arrows (`rules/lines.md`)](#37-lines-vectors--arrows)
4. [Typography & Mathematical Notation](#4-typography--mathematical-notation)
   - [4.1 Plain Text & Fonts (`rules/text.md`)](#41-plain-text--fonts)
   - [4.2 LaTeX & MathTex (`rules/latex.md`)](#42-latex--mathtex)
   - [4.3 Text Animations & Highlighting (`rules/text-animations.md`)](#43-text-animations--highlighting)
5. [Coordinate Systems & Data Visualization](#5-coordinate-systems--data-visualization)
   - [5.1 Axes, NumberPlanes & Coordinate Conversion (`rules/axes.md`)](#51-axes-numberplanes--coordinate-conversion)
   - [5.2 Function Graphing, Plotting & Shading (`rules/graphing.md`)](#52-function-graphing-plotting--shading)
6. [3D Visualizations & Dynamic Camera](#6-3d-visualizations--dynamic-camera)
   - [6.1 ThreeDScene & 3D Objects (`rules/3d.md`)](#61-threedscene--3d-objects)
   - [6.2 MovingCameraScene & Viewport Control (`rules/camera.md`)](#62-movingcamerascene--viewport-control)
7. [Animation Engine & Dynamic Behaviors](#7-animation-engine--dynamic-behaviors)
   - [7.1 Core Animation Patterns (`rules/animations.md`)](#71-core-animation-patterns)
   - [7.2 Creation & Revealing Animations (`rules/creation-animations.md`)](#72-creation--revealing-animations)
   - [7.3 Transformations & Interpolations (`rules/transform-animations.md`)](#73-transformations--interpolations)
   - [7.4 Animation Groups, Successions & Staggering (`rules/animation-groups.md`)](#74-animation-groups-successions--staggering)
   - [7.5 Updaters & Continuous Value Tracking (`rules/updaters.md`)](#75-updaters--continuous-value-tracking)
8. [Starter Templates](#8-starter-templates)
   - [8.1 Basic Scene Template (`templates/basic_scene.py`)](#81-basic-scene-template)
   - [8.2 Camera Control Scene Template (`templates/camera_scene.py`)](#82-camera-control-scene-template)
   - [8.3 3D ThreeDScene Template (`templates/threed_scene.py`)](#83-3d-threedscene-template)
9. [End-to-End Implementation Examples](#9-end-to-end-implementation-examples)
   - [9.1 Basic Animation Sequences (`examples/basic_animations.py`)](#91-basic-animation-sequences)
   - [9.2 Mathematical Visualization (`examples/math_visualization.py`)](#92-mathematical-visualization)
   - [9.3 Function & Curve Plotting (`examples/graph_plotting.py`)](#93-function--curve-plotting)
   - [9.4 3D Mathematical Surfaces (`examples/3d_visualization.py`)](#94-3d-mathematical-surfaces)
   - [9.5 Dynamic Updaters & Tracker Patterns (`examples/updater_patterns.py`)](#95-dynamic-updaters--tracker-patterns)
   - [9.6 Lorenz Attractor Simulation (`examples/lorenz_attractor.py`)](#96-lorenz-attractor-simulation)

---
""")

    # Section 1: SKILL.md
    skill_content = strip_frontmatter(read_file_safe(SOURCE_BASE / "SKILL.md"))
    sections.append(f"""## 1. Overview & Core Principles

{skill_content}

---
""")

    # Rule mapping
    rule_groups = [
        ("2. Scene Fundamentals & Runtime Configuration", [
            ("2.1 Scene Construction", "rules/scenes.md"),
            ("2.2 Configuration & Flags", "rules/config.md"),
            ("2.3 CLI Usage & Output Management", "rules/cli.md"),
            ("2.4 Timing, Pacing & Audio Sync", "rules/timing.md"),
        ]),
        ("3. Mobjects, Geometry & Styling", [
            ("3.1 Mobject Fundamentals", "rules/mobjects.md"),
            ("3.2 Positioning, Alignment & Coordinates", "rules/positioning.md"),
            ("3.3 Grouping with VGroup", "rules/grouping.md"),
            ("3.4 Colors & Palettes", "rules/colors.md"),
            ("3.5 Visual Styling & Strokes", "rules/styling.md"),
            ("3.6 2D Shapes & Geometry", "rules/shapes.md"),
            ("3.7 Lines, Vectors & Arrows", "rules/lines.md"),
        ]),
        ("4. Typography & Mathematical Notation", [
            ("4.1 Plain Text & Fonts", "rules/text.md"),
            ("4.2 LaTeX & MathTex", "rules/latex.md"),
            ("4.3 Text Animations & Highlighting", "rules/text-animations.md"),
        ]),
        ("5. Coordinate Systems & Data Visualization", [
            ("5.1 Axes, NumberPlanes & Coordinate Conversion", "rules/axes.md"),
            ("5.2 Function Graphing, Plotting & Shading", "rules/graphing.md"),
        ]),
        ("6. 3D Visualizations & Dynamic Camera", [
            ("6.1 ThreeDScene & 3D Objects", "rules/3d.md"),
            ("6.2 MovingCameraScene & Viewport Control", "rules/camera.md"),
        ]),
        ("7. Animation Engine & Dynamic Behaviors", [
            ("7.1 Core Animation Patterns", "rules/animations.md"),
            ("7.2 Creation & Revealing Animations", "rules/creation-animations.md"),
            ("7.3 Transformations & Interpolations", "rules/transform-animations.md"),
            ("7.4 Animation Groups, Successions & Staggering", "rules/animation-groups.md"),
            ("7.5 Updaters & Continuous Value Tracking", "rules/updaters.md"),
        ]),
    ]

    for group_title, subrules in rule_groups:
        sections.append(f"## {group_title}\n")
        for sub_title, rel_path in subrules:
            file_path = SOURCE_BASE / rel_path
            if file_path.is_file():
                content = strip_frontmatter(read_file_safe(file_path))
                sections.append(f"### {sub_title}\n\n*Source: `{rel_path}`*\n\n{content}\n")
            else:
                print(f"Warning: Missing rule file {file_path}")
        sections.append("---\n")

    # Section 8: Templates
    sections.append("## 8. Starter Templates\n")
    template_files = [
        ("8.1 Basic Scene Template", "templates/basic_scene.py"),
        ("8.2 Camera Control Scene Template", "templates/camera_scene.py"),
        ("8.3 3D ThreeDScene Template", "templates/threed_scene.py"),
    ]
    for title, rel_path in template_files:
        path = SOURCE_BASE / rel_path
        code = read_file_safe(path)
        sections.append(f"### {title}\n\n*File: `{rel_path}`*\n\n```python\n{code.strip()}\n```\n")

    sections.append("---\n")

    # Section 9: Examples
    sections.append("## 9. End-to-End Implementation Examples\n")
    example_files = [
        ("9.1 Basic Animation Sequences", "examples/basic_animations.py"),
        ("9.2 Mathematical Visualization", "examples/math_visualization.py"),
        ("9.3 Function & Curve Plotting", "examples/graph_plotting.py"),
        ("9.4 3D Mathematical Surfaces", "examples/3d_visualization.py"),
        ("9.5 Dynamic Updaters & Tracker Patterns", "examples/updater_patterns.py"),
        ("9.6 Lorenz Attractor Simulation", "examples/lorenz_attractor.py"),
    ]
    for title, rel_path in example_files:
        path = SOURCE_BASE / rel_path
        code = read_file_safe(path)
        sections.append(f"### {title}\n\n*File: `{rel_path}`*\n\n```python\n{code.strip()}\n```\n")

    sections.append("""---

## Summary & Quick CLI Reference

| Command | Action |
|---|---|
| `manim -ql scene.py SceneName` | Fast low-resolution preview (480p, 15fps) |
| `manim -qm scene.py SceneName` | Medium resolution (720p, 30fps) |
| `manim -qh scene.py SceneName` | High resolution production render (1080p, 60fps) |
| `manim -qk scene.py SceneName` | 4K ultra HD render (2160p, 60fps) |
| `manim -ql -p scene.py SceneName` | Preview video automatically in default media player |
| `manim -ql -s scene.py SceneName` | Save the final frame as PNG image |
| `manim -ql --format=gif scene.py SceneName` | Render directly as animated GIF |
| `manim -ql --disable_caching scene.py SceneName` | Force clean render without cached partial frames |
""")

    return "\n".join(sections)


def main() -> int:
    unified_doc = build_unified_markdown()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(unified_doc)

    print(f"Successfully generated unified ManimCE markdown guide: {OUTPUT_FILE}")
    print(f"Total lines: {len(unified_doc.splitlines())}")
    print(f"Total size:  {len(unified_doc.encode('utf-8')) / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
