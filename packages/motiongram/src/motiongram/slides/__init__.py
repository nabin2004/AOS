"""ManimGram Slides — Declarative narrated presentation and diagram system."""

from motiongram.slides.schema import (
    DeckOutputSpec,
    DeckPaletteSpec,
    DeckSpec,
    DeckStyleSpec,
    DeckTypographySpec,
    DiagramSpec,
    NarrationSpec,
    SlideSpec,
    TimelineActionSpec,
)
from motiongram.slides.validation import extract_bookmarks, validate_deck, validate_slide_bookmarks

__all__ = [
    "DeckOutputSpec",
    "DeckPaletteSpec",
    "DeckSpec",
    "DeckStyleSpec",
    "DeckTypographySpec",
    "DiagramSpec",
    "NarrationSpec",
    "SlideSpec",
    "TimelineActionSpec",
    "extract_bookmarks",
    "validate_deck",
    "validate_slide_bookmarks",
]
