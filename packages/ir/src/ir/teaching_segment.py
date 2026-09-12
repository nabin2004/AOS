"""Teaching Segment Intermediate Representation for Decoupled Audio-Visual Pedagogy.

Defines the core data structures where visual animation duration and teaching
narration duration are independent. A TeachingSegment pairs a concise visual
anchor (rendered once via Manim) with a comprehensive pedagogical narration
whose authoritative TTS duration drives the final segment duration via visual-state hold.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class VisualAnchor(BaseModel):
    """The visual anchor defining what is shown on screen for a teaching segment."""

    type: str = Field(
        default="formula",
        description="Type of visual anchor: formula, diagram, geometry, code, plot, or concept card.",
    )
    title: Optional[str] = Field(
        default=None,
        description="Visible title on the slide.",
    )
    latex: Optional[str] = Field(
        default=None,
        description="Primary LaTeX or mathematical formula displayed.",
    )
    visible_elements: List[str] = Field(
        default_factory=list,
        description="List of individual symbols or labels visible on screen (e.g. ['e', 'i', 'theta', 'cos', 'sin']).",
    )
    key_definitions: List[str] = Field(
        default_factory=list,
        description="Key definitions and symbol explanations visible on the slide (e.g. ['e: Euler number ≈ 2.718', 'i: imaginary unit (i² = -1)']).",
    )
    layout_type: str = Field(
        default="annotated_formula",
        description="Layout structure: annotated_formula, geometric_projection, constants_breakdown, split_screen, or concept_card.",
    )
    visual_states: List[str] = Field(
        default_factory=list,
        description="Ordered sequence of visual states from introduction to static hold.",
    )
    visual_purpose: str = Field(
        default="",
        description="The pedagogical purpose of this visual anchor.",
    )


class SemanticEvent(BaseModel):
    """Optional semantic action synchronized with narration during visual hold or animation."""

    target_element: str = Field(
        description="Target symbol or element on the slide (e.g. 'i', 'theta').",
    )
    action: str = Field(
        default="highlight",
        description="Action type: highlight, indicate, circumscribe, or focus.",
    )
    time_offset: float = Field(
        default=0.0,
        description="Timestamp offset in seconds relative to segment start.",
    )
    purpose: str = Field(
        default="",
        description="Pedagogical reason for the visual emphasis.",
    )


class TeachingSegment(BaseModel):
    """A decoupled educational unit combining a visual anchor and a detailed teaching narration."""

    segment_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
        description="Unique identifier for the segment.",
    )
    slide_num: int = Field(
        description="1-based index of this slide segment within the lesson.",
    )
    concept: str = Field(
        description="The mathematical or scientific concept being taught.",
    )
    learning_objective: str = Field(
        default="",
        description="Specific learning objective for this segment.",
    )
    visual_anchor: VisualAnchor = Field(
        description="The visual anchor specifications visible on screen.",
    )
    manim_code: str = Field(
        default="",
        description="Self-contained Manim animation code that constructs the visual anchor.",
    )
    narration: str = Field(
        default="",
        description="In-depth pedagogical teaching script explaining the concept and symbols.",
    )
    visual_duration: float = Field(
        default=0.0,
        description="Authoritative rendered duration of the Manim visual animation in seconds.",
    )
    narration_duration: float = Field(
        default=0.0,
        description="Authoritative duration of synthesized Pocket TTS audio in seconds.",
    )
    semantic_events: List[SemanticEvent] = Field(
        default_factory=list,
        description="Optional list of semantic visual events.",
    )
    visual_path: Optional[str] = Field(
        default=None,
        description="Filesystem path to the rendered visual animation MP4.",
    )
    audio_path: Optional[str] = Field(
        default=None,
        description="Filesystem path to the synthesized narration audio WAV.",
    )
    chunk_path: Optional[str] = Field(
        default=None,
        description="Filesystem path to the combined segment MP4 (animation + hold + audio).",
    )

    @property
    def total_duration(self) -> float:
        """The total segment duration is governed authoritatively by the teaching narration."""
        return max(self.visual_duration, self.narration_duration)

    @property
    def hold_duration(self) -> float:
        """The duration in seconds the final visual frame must be frozen to cover narration."""
        return max(0.0, self.narration_duration - self.visual_duration)
