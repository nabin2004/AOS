from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from aos_manim_core import Cue


ROLE_PRIORITY: Dict[str, int] = {
    "title": 100,
    "main_equation": 100,
    "main_diagram": 90,
    "body": 50,
    "decoration": 10,
}

VALID_LAYOUTS = (
    "title",
    "title-content",
    "two-column",
    "three-column",
    "image-text",
    "text-image",
    "full-screen",
    "comparison",
    "equation-focus",
    "diagram-focus",
    "code-focus",
    "quiz",
    "section",
)


def resolve_priority(role: str, priority: Optional[int] = None) -> int:
    if priority is not None:
        return priority
    return ROLE_PRIORITY.get(role, 50)


@dataclass
class Block:
    """Semantic content unit. No screen coordinates."""

    role: str = "body"
    priority: Optional[int] = None
    span: str = "full"
    id: Optional[str] = None

    @property
    def resolved_priority(self) -> int:
        return resolve_priority(self.role, self.priority)


@dataclass
class Paragraph(Block):
    text: str = ""


@dataclass
class Heading(Block):
    text: str = ""
    level: int = 2
    role: str = "body"


@dataclass
class Equation(Block):
    latex: str = ""
    role: str = "main_equation"


@dataclass
class CodeBlock(Block):
    code: str = ""
    language: str = "python"
    role: str = "body"


@dataclass
class Callout(Block):
    title: str = "Note"
    body: str = ""
    role: str = "decoration"


@dataclass
class ImageBlock(Block):
    path: str = ""
    caption: str = ""
    role: str = "main_diagram"


@dataclass
class DiagramRef(Block):
    name: str = ""
    kwargs: Dict[str, Any] = field(default_factory=dict)
    role: str = "main_diagram"


@dataclass
class AnimationSlot(Block):
    """Reserved region for a registered programmatic animation (e.g. Lorenz)."""

    name: str = ""
    kwargs: Dict[str, Any] = field(default_factory=dict)
    role: str = "main_diagram"


@dataclass
class ListBlock(Block):
    items: List[str] = field(default_factory=list)
    item_ids: List[str] = field(default_factory=list)
    role: str = "body"


@dataclass
class RawMobject(Block):
    """Already-built Manim mobject (used by legacy template wrappers)."""

    mobject: Any = None
    role: str = "body"


@dataclass
class ColumnGroup(Block):
    columns: List[List[Block]] = field(default_factory=list)
    ratios: Optional[List[float]] = None
    role: str = "body"


ContentBlock = Union[
    Paragraph,
    Heading,
    Equation,
    CodeBlock,
    Callout,
    ImageBlock,
    DiagramRef,
    AnimationSlot,
    ListBlock,
    RawMobject,
    ColumnGroup,
]


@dataclass
class SlideSpec:
    """Declarative slide: content + layout intent, never coordinates."""

    title: Optional[str] = None
    subtitle: Optional[str] = None
    layout: str = "title-content"
    blocks: List[ContentBlock] = field(default_factory=list)
    left: List[ContentBlock] = field(default_factory=list)
    right: List[ContentBlock] = field(default_factory=list)
    columns: List[List[ContentBlock]] = field(default_factory=list)
    ratios: Optional[List[float]] = None
    footer: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    affiliation: Optional[str] = None
    section_number: Optional[Union[int, str]] = None
    question: Optional[str] = None
    options: List[str] = field(default_factory=list)
    correct_index: int = 0
    explanation: Optional[str] = None
    aspect: Optional[float] = None
    voiceover: Optional[str] = None
    cues: List[Cue] = field(default_factory=list)
    total_bookmark_for_this_slide: str = ""
    total_this_slide_bookmark: str = ""
    bookmark_per_slide: Optional[str] = None

    def all_blocks(self) -> List[ContentBlock]:
        collected: List[ContentBlock] = list(self.blocks)
        collected.extend(self.left)
        collected.extend(self.right)
        for col in self.columns:
            collected.extend(col)
        return collected


@dataclass
class Presentation:
    title: Optional[str] = None
    slides: List[SlideSpec] = field(default_factory=list)
    footer: Optional[str] = None
