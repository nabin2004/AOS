"""High-level generator service for creating FlashcardDecks from videos and lectures."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from pydantic_ai import Agent, AgentRunResult

from educlaw.courses.contracts import Course, Lecture
from educlaw.flashcards.agents import build_flashcard_agent
from educlaw.flashcards.contracts import FlashcardDeck
from educlaw.settings import Settings


class FlashcardGenerator:
    """Service for generating active-recall flashcard decks."""

    def __init__(
        self,
        agent: Agent[object, FlashcardDeck] | None = None,
        *,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self.agent = agent or build_flashcard_agent(self.settings)

    async def generate_from_prompt(
        self,
        topic: str,
        *,
        title: str | None = None,
        context: str | None = None,
    ) -> FlashcardDeck:
        """Generate flashcards directly from a prompt and optional context."""
        prompt_parts = [
            f"Topic: {topic}",
            f"Deck Title: {title or topic}",
        ]
        if context:
            prompt_parts.append(f"Educational Context:\n{context}")

        prompt_parts.append(
            "Extract 5-10 high-yield flashcards covering foundational definitions, "
            "cloze deletions with {{c1::...}}, mathematical formulas with LaTeX, and geometric visual intuition."
        )

        result: AgentRunResult[FlashcardDeck] = await self.agent.run("\n\n".join(prompt_parts))
        deck = result.output
        if title:
            deck.title = title
        deck.topic = topic
        return deck

    async def generate_from_lecture(
        self,
        course: Course,
        lecture_number: int,
    ) -> FlashcardDeck:
        """Generate flashcards using full multi-modal artifacts from a specific course lecture."""
        lecture = course.get_lecture(lecture_number)
        if lecture is None:
            raise ValueError(f"Lecture {lecture_number} not found in course '{course.slug}'")

        context_blocks = [
            f"Course Title: {course.title}",
            f"Lecture #{lecture.lecture_number}: {lecture.spec.title}",
            f"Lecture Description: {lecture.spec.description}",
            f"Key Concepts: {', '.join(lecture.spec.key_concepts)}",
        ]

        if lecture.final_code:
            context_blocks.append(f"Manim Animation Script:\n```python\n{lecture.final_code.code}\n```")

        if lecture.narration_plan:
            narrations = [step.narration for step in lecture.narration_plan.steps]
            context_blocks.append(f"Voiceover Narration:\n" + "\n".join(narrations))

        if lecture.study_notes:
            context_blocks.append(f"Study Companion Notes:\n{lecture.study_notes}")

        context_str = "\n\n".join(context_blocks)
        deck = await self.generate_from_prompt(
            topic=lecture.spec.title,
            title=f"{course.title} — Lecture {lecture.lecture_number}: {lecture.spec.title}",
            context=context_str,
        )
        deck.course_slug = course.slug
        deck.lecture_number = lecture.lecture_number
        return deck
