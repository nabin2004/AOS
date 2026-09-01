"""
Metric 2: Version-Conflict Error Rate
========================================
Static analysis detecting ManimGL / deprecated API usage in generated code.
Uses regex patterns from config.GL_ONLY_PATTERNS + AST-based checks.

Computation:
    version_conflict_rate = (# conflict patterns found) / (# patterns checked)

Also returns a detailed breakdown for paper tables.
"""

import ast
import re
from typing import Any

from evaluation.config import GL_ONLY_PATTERNS


def detect_version_conflicts(code: str) -> dict[str, Any]:
    """
    Scan generated code for ManimGL / deprecated API patterns.

    Returns:
        {
            "version_conflict_rate": float (0.0–1.0),
            "total_patterns_checked": int,
            "conflicts_found": int,
            "conflict_details": [
                {"pattern": str, "line": int, "match": str, "category": str},
                ...
            ],
            "conflict_categories": {category: count, ...},
            "severity": str  ("none" | "low" | "medium" | "high"),
        }
    """
    conflicts = []
    lines = code.split("\n")

    for pattern_str in GL_ONLY_PATTERNS:
        pattern = re.compile(pattern_str, re.MULTILINE)
        for i, line in enumerate(lines, 1):
            match = pattern.search(line)
            if match:
                category = _categorize_pattern(pattern_str)
                conflicts.append({
                    "pattern": pattern_str,
                    "line": i,
                    "match": match.group(0).strip()[:80],
                    "category": category,
                })

    # Deduplicate by (line, category) to avoid double-counting
    seen = set()
    unique_conflicts = []
    for c in conflicts:
        key = (c["line"], c["category"])
        if key not in seen:
            seen.add(key)
            unique_conflicts.append(c)

    # Category breakdown
    categories: dict[str, int] = {}
    for c in unique_conflicts:
        cat = c["category"]
        categories[cat] = categories.get(cat, 0) + 1

    # Rate: fraction of code lines with at least one conflict
    conflicting_lines = len(set(c["line"] for c in unique_conflicts))
    total_code_lines = len([l for l in lines if l.strip() and not l.strip().startswith("#")])
    rate = conflicting_lines / max(total_code_lines, 1)

    # Severity classification
    if len(unique_conflicts) == 0:
        severity = "none"
    elif len(unique_conflicts) <= 2:
        severity = "low"
    elif len(unique_conflicts) <= 5:
        severity = "medium"
    else:
        severity = "high"

    return {
        "version_conflict_rate": round(rate, 4),
        "total_patterns_checked": len(GL_ONLY_PATTERNS),
        "conflicts_found": len(unique_conflicts),
        "conflict_details": unique_conflicts,
        "conflict_categories": categories,
        "severity": severity,
    }


def detect_specific_conflicts(
    code: str,
    known_incompatibilities: list[str],
) -> dict[str, Any]:
    """
    Check code against problem-specific known incompatibilities.
    Uses the version_conflict_notes.known_incompatibilities from the problem.

    Returns:
        {
            "problem_specific_conflicts": int,
            "total_checked": int,
            "matched": [str, ...],
        }
    """
    matched = []
    for incompat in known_incompatibilities:
        # Extract the "before" part of "X → Y" pattern
        parts = incompat.split("→")
        if parts:
            gl_construct = parts[0].strip()
            # Build a simple regex from the construct name
            # Remove leading/trailing quotes and whitespace
            keywords = re.findall(r'\w+', gl_construct)
            if keywords:
                # Use the most distinctive keyword (longest)
                keyword = max(keywords, key=len)
                if len(keyword) >= 4 and re.search(re.escape(keyword), code):
                    matched.append(incompat)

    return {
        "problem_specific_conflicts": len(matched),
        "total_checked": len(known_incompatibilities),
        "matched": matched,
    }


def _categorize_pattern(pattern_str: str) -> str:
    """Assign a human-readable category to a regex pattern."""
    categories = {
        "import": ["manim_imports_ext", "manimlib", "manim_gl"],
        "deprecated_scene": ["GraphScene", "ReconfigurableScene", "InteractiveScene",
                             "TeacherStudentsScene", "PiCreatureScene", "ExternallyAnimated"],
        "config_dict": ["CONFIG"],
        "deprecated_animation": ["ShowCreation", "FadeInFrom", "FadeOutAndShift"],
        "gl_mobject": ["PiCreature", "Eyes", "GlowDot", "DieFace", "TrueDot"],
        "gl_method": ["embed", "force_skipping", "revert_to_original",
                      "apply_depth_test", "set_shading", "fix_in_frame",
                      "set_backstroke"],
        "gl_camera": ["self\\.frame\\.", "camera_frame"],
        "deprecated_tex": ["OldTex", "TexMobject", "TextMobject"],
        "gl_rendering": ["render_to_movie_file", "set_renderer"],
    }

    for cat, keywords in categories.items():
        for kw in keywords:
            if kw.lower() in pattern_str.lower():
                return cat
    return "other"
