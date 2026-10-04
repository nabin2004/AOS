"""Pydantic data models for ManimGram Slides (DeckSpec DSL)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DeckPaletteSpec(BaseModel):
    """Color palette for presentation slide deck."""
    background: str = "#1C1C1C"
    primary: str = "#58C4DD"
    secondary: str = "#83C167"
    accent: str = "#FFFF00"
    warning: str = "#FF6666"
    text: str = "#FFFFFF"


class DeckTypographySpec(BaseModel):
    """Typography hierarchy for slide text elements."""
    title_font_size: int = 56
    heading_font_size: int = 44
    body_font_size: int = 30
    caption_font_size: int = 24
    equation_font_size: int = 40


class DeckStyleSpec(BaseModel):
    """Global presentation style settings."""
    palette: DeckPaletteSpec = Field(default_factory=DeckPaletteSpec)
    typography: DeckTypographySpec = Field(default_factory=DeckTypographySpec)
    default_run_time: float = 1.2
    stagger_lag: float = 0.15


class DeckOutputSpec(BaseModel):
    """Render dimensions and output format."""
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    format: str = "mp4"


class NarrationSpec(BaseModel):
    """Narration text containing embedded bookmark tags."""
    text: str
    voice: str | None = None


class DiagramSpec(BaseModel):
    """Reusable diagram component specification."""
    component: str
    props: dict[str, Any] = Field(default_factory=dict)


class TimelineActionSpec(BaseModel):
    """Discrete animation action triggered by time or narration bookmarks."""
    id: str | None = None
    at: str  # e.g. "start", "bookmark:SHOW_TITLE", "after:action_1"
    action: str  # e.g. "write", "create", "fade_in", "highlight", "indicate", "transform"
    target: str | None = None
    source: str | None = None
    run_time: float | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class SlideSpec(BaseModel):
    """Specification for an individual presentation slide."""
    id: str
    template: str
    title: str | None = None
    subtitle: str | None = None
    caption: str | None = None
    section_number: str | None = None
    items: list[str] | None = None
    equations: list[str] | None = None
    diagram: DiagramSpec | None = None
    left: dict[str, Any] | None = None
    right: dict[str, Any] | None = None
    narration: NarrationSpec | None = None
    timeline: list[TimelineActionSpec] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class DeckSpec(BaseModel):
    """Complete multi-slide presentation specification."""
    id: str
    title: str
    author: str = "ManimGram Slides"
    voice: str = "alba"
    output: DeckOutputSpec = Field(default_factory=DeckOutputSpec)
    style: DeckStyleSpec = Field(default_factory=DeckStyleSpec)
    slides: list[SlideSpec] = Field(default_factory=list)
