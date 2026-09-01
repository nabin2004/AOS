"""
Metric 3: Alignment Score
============================
Heuristic detection of required visual events in generated Manim code.

Each problem defines `required_visual_events` with description + weight.
We search the code AST + text for evidence of each event, then compute:

    alignment_score = Σ(weight_i × detected_i) / Σ(weight_i)

Detection is keyword/pattern based — purposefully conservative so the
paper reports a lower bound rather than an inflated score.
"""

import ast
import re
from typing import Any


# ── Keyword banks for common visual-event categories ──────────────────────

_ANIMATION_KEYWORDS: dict[str, list[str]] = {
    "create": ["Create", "Write", "DrawBorderThenFill", "ShowCreation", "FadeIn", "GrowFromCenter"],
    "transform": ["Transform", "ReplacementTransform", "TransformFromCopy", "MoveToTarget",
                   "ApplyMethod", "AnimationGroup", "Succession", "LaggedStart"],
    "fade": ["FadeIn", "FadeOut", "FadeTransform"],
    "indicate": ["Indicate", "Flash", "Circumscribe", "ShowPassingFlash", "Wiggle"],
    "move": ["shift", "move_to", "next_to", "to_edge", "to_corner", "animate"],
    "rotate": ["Rotate", "rotate", "set_angle"],
    "scale": ["scale", "Scale", "ScaleInPlace"],
    "color": ["set_color", "set_fill", "set_stroke", "color", "Color", "YELLOW", "RED",
              "BLUE", "GREEN", "WHITE", "ORANGE", "PURPLE", "GOLD", "TEAL"],
    "label": ["Text", "Tex", "MathTex", "DecimalNumber", "Integer", "label", "title"],
    "graph": ["Axes", "NumberPlane", "CoordinateSystem", "plot", "get_graph"],
    "group": ["VGroup", "Group", "AnimationGroup"],
    "3d": ["ThreeDScene", "ThreeDAxes", "Surface", "ParametricSurface",
           "set_camera_orientation", "begin_ambient_camera_rotation"],
    "updater": ["add_updater", "always_redraw", "ValueTracker"],
    "wait": ["wait", "Wait"],
    "number_line": ["NumberLine", "number_line"],
    "arrow": ["Arrow", "Vector", "DoubleArrow", "DashedLine"],
    "shape": ["Circle", "Square", "Rectangle", "Triangle", "Polygon", "Dot", "Line",
              "Arc", "Annulus", "Sector", "Ellipse", "RegularPolygon", "Star"],
    "brace": ["Brace", "BraceLabel", "BraceBetweenPoints"],
    "matrix": ["Matrix", "DecimalMatrix", "IntegerMatrix"],
    "table": ["Table", "MobjectTable"],
    "code_block": ["Code"],
    "svg": ["SVGMobject", "ImageMobject"],
}


def compute_alignment(
    code: str,
    required_visual_events: list[dict],
) -> dict[str, Any]:
    """
    Detect which required visual events are present in the code.

    Args:
        code: Generated Manim code string
        required_visual_events: List of dicts, each with keys:
            - "event" (str): Short description
            - "description" (str): Detailed explanation
            - "weight" (float): Importance weight

    Returns:
        {
            "alignment_score": float (0.0–1.0),
            "events_detected": int,
            "events_total": int,
            "per_event": [
                {"event": str, "weight": float, "detected": bool, "evidence": str},
                ...
            ],
        }
    """
    if not required_visual_events:
        return {
            "alignment_score": 1.0,
            "events_detected": 0,
            "events_total": 0,
            "per_event": [],
        }

    per_event = []
    total_weight = 0.0
    weighted_detected = 0.0

    for event_spec in required_visual_events:
        event_name = event_spec.get("event", "")
        description = event_spec.get("description", "")
        weight = float(event_spec.get("weight", 1.0))

        detected, evidence = _detect_event(code, event_name, description)
        total_weight += weight
        if detected:
            weighted_detected += weight

        per_event.append({
            "event": event_name,
            "weight": weight,
            "detected": detected,
            "evidence": evidence,
        })

    alignment_score = weighted_detected / max(total_weight, 1e-9)

    return {
        "alignment_score": round(alignment_score, 4),
        "events_detected": sum(1 for e in per_event if e["detected"]),
        "events_total": len(per_event),
        "per_event": per_event,
    }


def _detect_event(code: str, event_name: str, description: str) -> tuple[bool, str]:
    """
    Detect a single visual event in the code.

    Strategy:
    1. Extract keywords from the event name + description
    2. Match against code using keyword banks + raw substring search
    3. Return (detected, evidence_string)
    """
    combined = f"{event_name} {description}".lower()
    code_lower = code.lower()

    # ── Strategy 1: Direct keyword match from event name ──
    event_words = re.findall(r'[A-Za-z_]\w+', event_name)
    for word in event_words:
        if len(word) >= 4 and word.lower() in code_lower:
            return True, f"keyword '{word}' found in code"

    # ── Strategy 2: Match against keyword banks ──
    matched_categories = _match_categories(combined)
    for cat in matched_categories:
        keywords = _ANIMATION_KEYWORDS.get(cat, [])
        for kw in keywords:
            if kw in code:
                return True, f"'{kw}' (category: {cat})"

    # ── Strategy 3: Description-driven heuristic search ──
    # Extract important nouns/verbs from the description
    desc_keywords = _extract_description_keywords(description)
    for kw in desc_keywords:
        if len(kw) >= 5 and kw.lower() in code_lower:
            return True, f"description keyword '{kw}' found"

    # ── Strategy 4: Animation call pattern ──
    # Check if self.play() or self.add() is used (basic animation presence)
    animation_patterns = [
        r'self\.play\(',
        r'self\.add\(',
        r'self\.wait\(',
        r'self\.remove\(',
    ]
    for pat in animation_patterns:
        if re.search(pat, code):
            # Check if the animation relates to event keywords
            for word in event_words:
                if len(word) >= 3:
                    # Find self.play() calls that mention this keyword nearby
                    context_pat = rf'self\.play\([^)]*{re.escape(word)}[^)]*\)'
                    if re.search(context_pat, code, re.IGNORECASE):
                        return True, f"play() call with '{word}'"

    return False, "not detected"


def _match_categories(text: str) -> list[str]:
    """Match event description text to keyword bank categories."""
    category_triggers: dict[str, list[str]] = {
        "create": ["create", "draw", "appear", "show", "display", "render"],
        "transform": ["transform", "morph", "change", "convert", "transition", "evolve"],
        "fade": ["fade", "disappear", "vanish"],
        "indicate": ["highlight", "indicate", "flash", "emphasize", "pulse"],
        "move": ["move", "shift", "position", "slide", "translate", "place"],
        "rotate": ["rotate", "spin", "turn", "angle", "revolve"],
        "scale": ["scale", "grow", "shrink", "resize", "zoom"],
        "color": ["color", "hue", "shade", "tint", "highlight", "gradient"],
        "label": ["label", "text", "title", "annotation", "caption", "equation", "formula"],
        "graph": ["graph", "plot", "axes", "coordinate", "chart", "function"],
        "group": ["group", "arrange", "organize", "layout", "stack"],
        "3d": ["3d", "three-dimensional", "surface", "camera", "perspective", "rotation"],
        "updater": ["update", "track", "dynamic", "real-time", "continuously", "tracker"],
        "wait": ["pause", "wait", "delay"],
        "number_line": ["number line", "numberline", "ruler", "axis"],
        "arrow": ["arrow", "vector", "pointer", "direction"],
        "shape": ["circle", "square", "rectangle", "triangle", "polygon", "dot",
                   "line", "arc", "shape", "geometry"],
        "brace": ["brace", "bracket", "curly"],
        "matrix": ["matrix", "matrices", "grid"],
        "table": ["table", "row", "column"],
    }

    matched = []
    for cat, triggers in category_triggers.items():
        for trigger in triggers:
            if trigger in text:
                matched.append(cat)
                break
    return matched


def _extract_description_keywords(description: str) -> list[str]:
    """Extract likely-important keywords from a description string."""
    # Remove common stop words
    stop = {
        "the", "and", "for", "that", "this", "with", "from", "are", "was",
        "were", "been", "have", "has", "had", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "does", "did",
        "not", "but", "its", "into", "each", "then", "than", "when",
        "where", "which", "while", "what", "about", "after", "before",
        "between", "both", "during", "either", "else", "every", "few",
        "more", "most", "much", "many", "only", "other", "some", "such",
        "also", "just", "like", "over", "under", "very", "too",
    }
    words = re.findall(r'[A-Za-z_]\w+', description)
    return [w for w in words if w.lower() not in stop and len(w) >= 4]
