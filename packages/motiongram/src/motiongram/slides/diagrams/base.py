"""Base class for all ManimGram slide diagram components."""

from __future__ import annotations

import re
from typing import Any

from manim import Mobject, VGroup


class SlideDiagram(VGroup):
    """Base VGroup composite exposing semantic selector resolution."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._selectors: dict[str, Mobject] = {}

    def register_selector(self, key: str, mobject: Mobject) -> None:
        """Register a named semantic selector pointing to an internal submobject."""
        self._selectors[key] = mobject

    def get_selector(self, selector_str: str) -> Mobject:
        """Resolve a semantic selector query into an actual Manim Mobject.

        Examples:
            - "node[input]"
            - "edge[a->b]"
            - "entry[0,0]"
            - "token[cat]"
        """
        # Exact match
        if selector_str in self._selectors:
            return self._selectors[selector_str]

        # Normalized lookup (strip whitespace)
        clean_key = re.sub(r"\s+", "", selector_str)
        for k, mob in self._selectors.items():
            if re.sub(r"\s+", "", k) == clean_key:
                return mob

        # Fallback to entire diagram if not found
        return self
