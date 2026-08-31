"""Filtering and normalization rules for public API discovery."""

from __future__ import annotations

import types
from typing import Any, List, Optional, Set


def is_public_symbol(name: str, module_all: Optional[List[str]] = None) -> bool:
    """
    Determine if a symbol is part of the public API.
    If module defines __all__, strictly respect it.
    Otherwise, exclude names starting with '_'.
    """
    if module_all is not None:
        return name in module_all

    if name.startswith("_"):
        return False

    return True


def is_deprecated(obj: Any, doc: Optional[str] = None) -> bool:
    """Check if an object or function is marked as deprecated."""
    if hasattr(obj, "__deprecated__"):
        return True
    if doc:
        doc_lower = doc.lower()
        if "deprecated" in doc_lower and ("deprecated in version" in doc_lower or "will be removed" in doc_lower or ".. deprecated::" in doc_lower):
            return True
    return False


def get_canonical_module(obj: Any, current_module_name: str) -> str:
    """Determine the originating or canonical module for an object."""
    if hasattr(obj, "__module__") and obj.__module__:
        return obj.__module__
    return current_module_name


def should_skip_module(module_name: str, skip_patterns: Optional[Set[str]] = None) -> bool:
    """Check if a module should be skipped (e.g. tests, internals, setup, _build)."""
    default_skips = {
        "tests",
        "testing",
        "conftest",
        "_internals",
        "_cython",
        "_cpython",
        "setup",
        "_pytest",
    }
    skips = skip_patterns or default_skips

    parts = module_name.split(".")
    for part in parts:
        if part in skips or part.startswith("_"):
            return True
    return False
