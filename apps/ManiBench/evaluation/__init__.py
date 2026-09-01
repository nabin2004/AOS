"""
ManiBench Evaluation Framework
================================
Automated evaluation of LLM-generated Manim code using OpenRouter API.

Metrics:
    1. Executability (Pass@1) — binary, does code run in Manim CE?
    2. Version-Conflict Error Rate — % of GL/deprecated API usage
    3. Alignment Score (0–1) — weighted visual event presence + AST heuristics
    4. Coverage Score (0–1) — pedagogical element density

Usage:
    python -m evaluation.run --models gpt-4o claude-3.5-sonnet --trials 3
"""

__version__ = "1.0.0"
