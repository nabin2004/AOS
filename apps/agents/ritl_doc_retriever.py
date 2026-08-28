"""RITL-DOC API Document Retrieval Module for ManimAgent.

Bypasses vector databases by directly inspecting API function calls in failing Manim scripts,
extracting function signatures, parameter lists, and docstrings from the local `manim` package.
"""

from __future__ import annotations

import ast
import inspect
import logging
from typing import Dict, List, Set, Optional

logger = logging.getLogger(__name__)


def extract_manim_api_calls(script_code: str) -> Set[str]:
    """Parse Python AST to extract all function and class name references."""
    api_calls: Set[str] = set()
    try:
        tree = ast.parse(script_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                api_calls.add(node.id)
            elif isinstance(node, ast.Attribute):
                api_calls.add(node.attr)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    api_calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    api_calls.add(node.func.attr)
    except SyntaxError:
        pass
    return api_calls


def retrieve_manim_docstrings(api_names: Set[str]) -> Dict[str, str]:
    """Reflects over installed manim module to retrieve signatures and docstrings for requested symbols."""
    doc_registry: Dict[str, str] = {}
    try:
        import manim
    except ImportError:
        logger.warning("Manim package is not installed; docstring retrieval falling back to standard registry.")
        return doc_registry

    for name in api_names:
        if hasattr(manim, name):
            obj = getattr(manim, name)
            try:
                sig = str(inspect.signature(obj)) if callable(obj) else ""
                doc = inspect.getdoc(obj) or "No documentation available."
                # Truncate docstring to first 3 paragraphs for concise prompt injection
                doc_summary = "\n".join(doc.split("\n\n")[:3])
                doc_registry[name] = f"Symbol: {name}{sig}\nDocstring: {doc_summary}"
            except Exception:
                continue

    return doc_registry


def generate_ritl_doc_prompt_injection(script_code: str, error_traceback: str) -> str:
    """Combines API symbol extraction and docstring retrieval into a RITL prompt block."""
    api_calls = extract_manim_api_calls(script_code)
    doc_map = retrieve_manim_docstrings(api_calls)

    if not doc_map:
        return ""

    doc_blocks: List[str] = []
    for symbol, doc_text in doc_map.items():
        if symbol.lower() in error_traceback.lower() or symbol in script_code:
            doc_blocks.append(f"--- API Reference: `{symbol}` ---\n{doc_text}")

    if not doc_blocks:
        return ""

    return "### RITL-DOC Target API Documentation\n" + "\n\n".join(doc_blocks[:5])
