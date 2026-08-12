"""Per-domain concept registry factory (shared by math/physics/dsa)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from manim import DOWN, GREY_B, Text, VGroup, WHITE


@dataclass
class ConceptSpec:
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


class ConceptRegistry:
    """Isolated registry so each domain plugin has its own concept namespace."""

    def __init__(self) -> None:
        self._registry: dict[str, ConceptSpec] = {}

    def register_concept(
        self,
        *,
        id: str,
        domain: str,
        chapter: str,
        title: str,
        description: str = "",
        stub: bool = False,
        tags: list[str] | None = None,
    ) -> Callable[[Callable[..., VGroup]], Callable[..., VGroup]]:
        def deco(fn: Callable[..., VGroup]) -> Callable[..., VGroup]:
            self._registry[id] = ConceptSpec(
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

    def get_concept(self, concept_id: str) -> ConceptSpec:
        if concept_id not in self._registry:
            known = ", ".join(sorted(self._registry)[:20])
            raise KeyError(
                f"Unknown concept {concept_id!r}. "
                f"Try list_concepts(). Sample ids: {known}..."
            )
        return self._registry[concept_id]

    def list_concepts(self, domain: str | None = None, *, include_stubs: bool = True) -> list[ConceptSpec]:
        items = list(self._registry.values())
        if domain is not None:
            items = [c for c in items if c.domain == domain]
        if not include_stubs:
            items = [c for c in items if not c.stub]
        return sorted(items, key=lambda c: (c.chapter, c.id))

    def domains(self) -> list[str]:
        return sorted({c.domain for c in self._registry.values()})

    def stub_concept(
        self,
        *,
        id: str,
        domain: str,
        chapter: str,
        title: str,
        description: str = "",
        tags: list[str] | None = None,
    ) -> None:
        @self.register_concept(
            id=id,
            domain=domain,
            chapter=chapter,
            title=title,
            description=description or f"Stub: {title}",
            stub=True,
            tags=tags,
        )
        def _stub() -> VGroup:
            return VGroup(
                Text(title, font_size=28, color=WHITE),
                Text("(coming soon)", font_size=20, color=GREY_B),
            ).arrange(DOWN, buff=0.25)
