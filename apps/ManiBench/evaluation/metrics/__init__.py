"""
ManiBench Evaluation — Metrics
================================
Four-tier scoring system:
  1. Executability — binary, does code run in Manim CE?
  2. Version-Conflict Error Rate — static analysis for GL/deprecated patterns
  3. Alignment Score — weighted visual event detection via AST + heuristics
  4. Coverage Score — pedagogical element density via code analysis
"""

from evaluation.metrics.executability import compute_executability
from evaluation.metrics.version_conflict import detect_version_conflicts, detect_specific_conflicts
from evaluation.metrics.alignment import compute_alignment
from evaluation.metrics.coverage import compute_coverage

__all__ = [
    "compute_executability",
    "detect_version_conflicts",
    "detect_specific_conflicts",
    "compute_alignment",
    "compute_coverage",
]
