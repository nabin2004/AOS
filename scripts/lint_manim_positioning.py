#!/usr/bin/env python3
"""CLI utility to lint Manim Community Edition code for layout and positioning issues.

Usage:
    uv run python scripts/lint_manim_positioning.py apps/ui/aos/backend/hitl_workspace/scene.py
    python scripts/lint_manim_positioning.py path/to/scene.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add backend directory to sys.path so we can import positioning_linter
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "apps" / "ui" / "aos" / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.positioning_linter import lint_manim_file, lint_manim_positioning


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Static positioning linter for Manim Community Edition scenes."
    )
    parser.add_argument(
        "file",
        nargs="?",
        default=str(backend_dir / "hitl_workspace" / "scene.py"),
        help="Path to the Manim Python file to lint (default: hitl_workspace/scene.py)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero exit code if any warnings are detected.",
    )

    args = parser.parse_args()
    target_path = Path(args.file)

    if not target_path.exists():
        print(f"Error: Target file not found: {target_path}", file=sys.stderr)
        return 1

    print(f"Linting Manim positioning in: {target_path.resolve()}")
    report = lint_manim_file(target_path)

    print("-" * 70)
    print(report.format_feedback())
    print("-" * 70)

    if report.has_errors or (args.strict and report.has_warnings):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
