"""
Metric 4: Coverage Score
============================
Detects pedagogical-quality elements in generated Manim code.

Coverage measures how well the generated animation would serve as an
educational resource.  Four sub-dimensions:

    1. Mathematical Annotations (weight 0.35)
       - Tex / MathTex / equations / formulas
    2. Visual Mapping (weight 0.30)
       - Color usage, labels, arrows, annotations
    3. Numeric Evidence (weight 0.20)
       - DecimalNumber, Integer, NumberLine, TrackedValues
    4. Structural Clarity (weight 0.15)
       - Grouping, sequencing, progressive reveal, wait pauses

Final coverage_score = Σ(dim_weight × dim_score) where each dim_score
is itself a ratio of detected sub-features to expected sub-features.
"""

import re
from typing import Any


# ── Sub-feature detectors per dimension ──────────────────────────────────

_DIM_PATTERNS: dict[str, list[tuple[str, str]]] = {
    "math_annotations": [
        (r'\bTex\s*\(', "Tex object"),
        (r'\bMathTex\s*\(', "MathTex object"),
        (r'\bText\s*\(', "Text object"),
        (r'\bTitle\s*\(', "Title object"),
        (r'\bBraceLabel\s*\(', "BraceLabel annotation"),
        (r'\bBrace\s*\(', "Brace annotation"),
        (r'\\.get_tex_string', "TeX string usage"),
        (r'\\frac|\\int|\\sum|\\prod|\\lim|\\sqrt|\\mathbb|\\mathcal', "LaTeX math"),
        (r'\\\\[a-z]+\{', "LaTeX command"),  # Generic LaTeX
    ],
    "visual_mapping": [
        (r'set_color\s*\(', "explicit color setter"),
        (r'set_fill\s*\(', "fill styling"),
        (r'set_stroke\s*\(', "stroke styling"),
        (r'\bArrow\s*\(', "Arrow indicator"),
        (r'\bDoubleArrow\s*\(', "DoubleArrow"),
        (r'\bDashedLine\s*\(', "DashedLine"),
        (r'\bDot\s*\(', "Dot marker"),
        (r'\.label\s*\(', "label attachment"),
        (r'always_redraw\s*\(', "dynamic redraw"),
        (r'\bSurroundingRectangle\s*\(', "SurroundingRectangle"),
        (r'\bBackgroundRectangle\s*\(', "BackgroundRectangle"),
        (r'color\s*=\s*[A-Z_]+', "named color"),
        (r'\.set_color_by_gradient\s*\(', "gradient coloring"),
        (r'\bLinearGradient|RadialGradient', "gradient object"),
    ],
    "numeric_evidence": [
        (r'\bDecimalNumber\s*\(', "DecimalNumber"),
        (r'\bInteger\s*\(', "Integer display"),
        (r'\bValueTracker\s*\(', "ValueTracker"),
        (r'\bNumberLine\s*\(', "NumberLine"),
        (r'\bAxes\s*\(', "Axes object"),
        (r'\bNumberPlane\s*\(', "NumberPlane"),
        (r'\bget_value\s*\(', "get_value call"),
        (r'\bset_value\s*\(', "set_value call"),
        (r'\bget_area\s*\(', "area computation"),
        (r'\.plot\s*\(', "function plot"),
    ],
    "structural_clarity": [
        (r'\bVGroup\s*\(', "VGroup organization"),
        (r'\bGroup\s*\(', "Group organization"),
        (r'\.arrange\s*\(', "arrange layout"),
        (r'self\.wait\s*\(', "paced wait"),
        (r'\bFadeIn\s*\(', "fade-in reveal"),
        (r'\bFadeOut\s*\(', "fade-out cleanup"),
        (r'\bLaggedStart\s*\(', "lagged sequencing"),
        (r'\bSuccession\s*\(', "succession chaining"),
        (r'\bAnimationGroup\s*\(', "animation grouping"),
        (r'for\s+.*\s+in\s+', "loop-based construction"),
        (r'def\s+\w+\s*\(self', "method decomposition"),
    ],
}

_DIM_WEIGHTS: dict[str, float] = {
    "math_annotations": 0.35,
    "visual_mapping": 0.30,
    "numeric_evidence": 0.20,
    "structural_clarity": 0.15,
}


def compute_coverage(
    code: str,
    coverage_requirements: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Assess pedagogical coverage of generated Manim code.

    Args:
        code: Generated Manim code string
        coverage_requirements: Optional list from the problem spec, each dict
            with "element", "description", "metric" keys.

    Returns:
        {
            "coverage_score": float (0.0–1.0),
            "dimension_scores": {dim_name: float, ...},
            "dimension_details": {dim_name: [matched_features], ...},
            "requirement_coverage": {
                "met": int,
                "total": int,
                "details": [{element, met, evidence}, ...]
            } if coverage_requirements given, else None,
        }
    """
    dim_scores: dict[str, float] = {}
    dim_details: dict[str, list[str]] = {}

    for dim_name, patterns in _DIM_PATTERNS.items():
        matched = []
        for pat, label in patterns:
            if re.search(pat, code):
                matched.append(label)
        dim_scores[dim_name] = len(matched) / max(len(patterns), 1)
        dim_details[dim_name] = matched

    # Weighted aggregate
    coverage_score = sum(
        _DIM_WEIGHTS[dim] * dim_scores[dim]
        for dim in _DIM_WEIGHTS
    )

    result: dict[str, Any] = {
        "coverage_score": round(coverage_score, 4),
        "dimension_scores": {k: round(v, 4) for k, v in dim_scores.items()},
        "dimension_details": dim_details,
        "requirement_coverage": None,
    }

    # ── Optional: problem-specific requirement coverage ──
    if coverage_requirements:
        req_details = []
        met_count = 0
        for req in coverage_requirements:
            # Handle both string and dict formats
            if isinstance(req, str):
                element = req
                description = req
                metric = ""
            else:
                element = req.get("element", "")
                description = req.get("description", "")
                metric = req.get("metric", "")
            met, evidence = _check_requirement(code, element, description, metric)
            if met:
                met_count += 1
            req_details.append({
                "element": element,
                "met": met,
                "evidence": evidence,
            })
        result["requirement_coverage"] = {
            "met": met_count,
            "total": len(coverage_requirements),
            "details": req_details,
        }

    return result


def _check_requirement(
    code: str,
    element: str,
    description: str,
    metric: str,
) -> tuple[bool, str]:
    """
    Check if a specific coverage requirement is met.

    Uses keyword extraction from element + description to search the code.
    """
    combined = f"{element} {description} {metric}"

    # Extract distinctive keywords (4+ chars, not stop words)
    stop = {
        "the", "and", "for", "that", "this", "with", "from", "are",
        "was", "were", "been", "have", "has", "will", "would", "could",
        "should", "each", "then", "than", "when", "where", "which",
        "while", "what", "about", "after", "before", "between", "both",
        "during", "either", "every", "more", "most", "much", "many",
        "only", "other", "some", "such", "also", "just", "like",
        "must", "present", "used", "using", "correctly", "properly",
    }
    words = re.findall(r'[A-Za-z_]\w+', combined)
    keywords = [w for w in words if w.lower() not in stop and len(w) >= 4]

    code_lower = code.lower()
    for kw in keywords:
        if kw.lower() in code_lower:
            return True, f"keyword '{kw}' present"

    # Check Manim-specific object types from element name
    manim_objects = re.findall(r'[A-Z][a-zA-Z]+', element)
    for obj in manim_objects:
        if obj in code:
            return True, f"Manim object '{obj}' found"

    return False, "not detected"
