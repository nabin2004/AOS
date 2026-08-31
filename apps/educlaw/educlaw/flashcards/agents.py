"""Agent factories for Flashcard generation."""

from __future__ import annotations

from typing import Any
from uuid import uuid4
from pydantic_ai import Agent

from educlaw.flashcards.contracts import CardType, FlashcardDeck
from educlaw.flashcards.prompts import FLASHCARD_ARCHITECT_INSTRUCTIONS
from educlaw.settings import Settings


def _default_test_deck() -> dict[str, Any]:
    return {
        "title": "Educational Flashcard Deck",
        "topic": "Fundamentals",
        "cards": [
            {
                "card_type": "basic",
                "front": "What is the core intuition behind this concept?",
                "back": "It decomposes complex continuous systems into harmonic or orthogonal components.",
                "cloze_text": None,
                "visual_cue": "Animated rotating vectors in the complex plane.",
                "tags": ["education", "foundations"],
            },
            {
                "card_type": "cloze",
                "front": "The {{c1::eigenvalue}} equation is expressed as {{c2::A \\vec{v} = \\lambda \\vec{v}}}.",
                "back": "Where \\(\\vec{v}\\) is the eigenvector and \\(\\lambda\\) is the scaling factor.",
                "cloze_text": "The {{c1::eigenvalue}} equation is expressed as {{c2::A \\vec{v} = \\lambda \\vec{v}}}.",
                "visual_cue": "Vector \\(\\vec{v}\\) does not change direction, only length.",
                "tags": ["math::linear-algebra", "cloze"],
            },
            {
                "card_type": "formula",
                "front": "What is the mathematical definition of the derivative?",
                "back": "\\[ f'(x) = \\lim_{h \\to 0} \\frac{f(x+h) - f(x)}{h} \\]",
                "cloze_text": None,
                "visual_cue": "Secant line rotating into the tangent line as \\(h \\to 0\\).",
                "tags": ["math::calculus"],
            },
        ],
    }


def _is_test_mode(settings: Settings | None, model: str | object | None) -> bool:
    if model == "test":
        return True
    if settings and settings.test_model:
        return True
    return False


def build_flashcard_agent(
    settings: Settings | None = None,
    *,
    model: str | object | None = None,
) -> Agent[object, FlashcardDeck]:
    """Build the Flashcard Architect Agent."""
    if _is_test_mode(settings, model):
        from pydantic_ai.models.test import TestModel

        resolved_model = TestModel(custom_output_args=_default_test_deck())
    elif model is not None:
        resolved_model = model
    elif settings and settings.model:
        resolved_model = settings.model
    else:
        resolved_model = "openrouter:openai/gpt-4o-mini"

    return Agent(
        model=resolved_model,
        name="FlashcardArchitectAgent",
        output_type=FlashcardDeck,
        instructions=FLASHCARD_ARCHITECT_INSTRUCTIONS,
    )
