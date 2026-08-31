"""Flashcard and Anki Deck generation module for EduClaw."""

from educlaw.flashcards.agents import build_flashcard_agent
from educlaw.flashcards.contracts import (
    CardType,
    ExportFormat,
    Flashcard,
    FlashcardDeck,
)
from educlaw.flashcards.exporters import (
    export_deck,
    export_to_anki_tsv,
    export_to_markdown,
)
from educlaw.flashcards.generator import FlashcardGenerator

__all__ = [
    "CardType",
    "ExportFormat",
    "Flashcard",
    "FlashcardDeck",
    "FlashcardGenerator",
    "build_flashcard_agent",
    "export_deck",
    "export_to_anki_tsv",
    "export_to_markdown",
]
