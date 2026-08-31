"""Data contracts and schemas for Flashcard generation and Anki decks."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CardType(str, Enum):
    BASIC = "basic"
    CLOZE = "cloze"
    VISUAL_INTUITION = "visual_intuition"
    FORMULA = "formula"


class ExportFormat(str, Enum):
    ANKI_TSV = "anki_tsv"
    MARKDOWN = "markdown"
    JSON = "json"


class Flashcard(BaseModel):
    """An individual active-recall flashcard item."""
    card_id: UUID = Field(default_factory=uuid4)
    card_type: CardType = CardType.BASIC
    front: str = Field(..., description="Front question, prompt, or cloze statement")
    back: str = Field(..., description="Back answer, solution, or intuitive explanation")
    cloze_text: str | None = Field(
        default=None,
        description="Optional formatted cloze text containing {{c1::...}} deletions",
    )
    visual_cue: str | None = Field(
        default=None,
        description="Visual reference or geometric intuition from the video animation",
    )
    tags: list[str] = Field(default_factory=list, description="Categorization tags for Anki filtering")


class FlashcardDeck(BaseModel):
    """A complete collection of flashcards for a video, lecture, or course."""
    deck_id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., description="Title of the flashcard deck")
    topic: str = Field(..., description="Core subject / topic")
    course_slug: str | None = None
    lecture_number: int | None = None
    cards: list[Flashcard] = Field(default_factory=list, min_length=1)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def total_cards(self) -> int:
        return len(self.cards)
