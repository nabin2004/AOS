"""Registry for d2l curriculum concepts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from manim import VGroup


@dataclass
class ConceptSpec:
    """Registered visualizer for one curriculum concept."""

    id: str
    domain: str
    chapter: str
    title: str
    builder: Callable[..., VGroup]
    description: str = ""
    stub: bool = False
    tags: list[str] = field(default_factory=list)

    def build(self, **kwargs: Any) -> VGroup:
        return self.builder(**kwargs)


_REGISTRY: dict[str, ConceptSpec] = {}


def register_concept(
    *,
    id: str,
    domain: str,
    chapter: str,
    title: str,
    description: str = "",
    stub: bool = False,
    tags: list[str] | None = None,
) -> Callable[[Callable[..., VGroup]], Callable[..., VGroup]]:
    """Decorator that registers a VGroup builder under a stable concept id."""

    def deco(fn: Callable[..., VGroup]) -> Callable[..., VGroup]:
        _REGISTRY[id] = ConceptSpec(
            id=id,
            domain=domain,
            chapter=chapter,
            title=title,
            builder=fn,
            description=description,
            stub=stub,
            tags=list(tags or []),
        )
        return fn

    return deco


def get_concept(concept_id: str) -> ConceptSpec:
    if concept_id not in _REGISTRY:
        known = ", ".join(sorted(_REGISTRY)[:20])
        raise KeyError(
            f"Unknown concept {concept_id!r}. "
            f"Try list_concepts(). Sample ids: {known}..."
        )
    return _REGISTRY[concept_id]


def list_concepts(domain: str | None = None, *, include_stubs: bool = True) -> list[ConceptSpec]:
    items = list(_REGISTRY.values())
    if domain is not None:
        items = [c for c in items if c.domain == domain]
    if not include_stubs:
        items = [c for c in items if not c.stub]
    return sorted(items, key=lambda c: (c.chapter, c.id))


def domains() -> list[str]:
    return sorted({c.domain for c in _REGISTRY.values()})
