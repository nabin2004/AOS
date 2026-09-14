"""Type definitions and data models for the Visual Critic subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


@dataclass(frozen=True)
class VisualQuestionDef:
    """Definition of a constrained visual interrogation question."""

    id: str
    question: str
    bad_answer: str  # "yes" or "no" that indicates a defect
    penalty: float
    is_critical: bool
    defect_desc: str
    suggested_fix: str


# The 10 Highly Constrained Visual Questions for Moondream 0.5B and visual critics
TARGETED_VISUAL_QUESTIONS: List[VisualQuestionDef] = [
    VisualQuestionDef(
        id="scene_empty",
        question="Is this image completely blank, pitch black, or empty with no visual content?",
        bad_answer="yes",
        penalty=1.0,
        is_critical=True,
        defect_desc="Scene canvas is completely blank or pitch black with 0 visual elements.",
        suggested_fix="Ensure self.play(Create(...)) or self.add(...) adds elements directly to the canvas.",
    ),
    VisualQuestionDef(
        id="equation_visible",
        question="Is a mathematical formula, equation, or primary text clearly visible on screen?",
        bad_answer="no",
        penalty=0.35,
        is_critical=True,
        defect_desc="Primary equation or core pedagogical text is missing or not visible.",
        suggested_fix="Add the core formula using MathTex or Text and display with self.play(Write(formula)).",
    ),
    VisualQuestionDef(
        id="equation_cutoff",
        question="Is any equation, formula, or text cut off, clipped, or running off the border edges of the screen?",
        bad_answer="yes",
        penalty=0.35,
        is_critical=True,
        defect_desc="Equation, text, or shapes are cut off or clipping off the screen edges.",
        suggested_fix="Scale down width using `formula.scale_to_fit_width(11.5)` or position with `buff=0.4`.",
    ),
    VisualQuestionDef(
        id="objects_overlapping",
        question="Are any text elements, formulas, or shapes overlapping, colliding, or placed directly on top of each other illegibly?",
        bad_answer="yes",
        penalty=0.35,
        is_critical=True,
        defect_desc="Visual objects, formulas, or labels are colliding or overlapping.",
        suggested_fix="Use VGroup.arrange(DOWN, buff=0.35) or `.next_to(..., DOWN, buff=0.4)` to prevent overlap.",
    ),
    VisualQuestionDef(
        id="text_too_small",
        question="Is any text or formula excessively tiny, blurry, or difficult to read comfortably?",
        bad_answer="yes",
        penalty=0.20,
        is_critical=False,
        defect_desc="Text or formula font size is excessively small.",
        suggested_fix="Increase font sizes: title font_size=34, math font_size=36, body font_size>=22.",
    ),
    VisualQuestionDef(
        id="excessive_empty_space",
        question="Is there excessive empty space where the slide looks bare and uninformative?",
        bad_answer="yes",
        penalty=0.15,
        is_critical=False,
        defect_desc="Excessive empty void on the slide without balanced pedagogical elements.",
        suggested_fix="Add definition breakdown cards or geometric visual representations to balance the frame.",
    ),
    VisualQuestionDef(
        id="diagram_appeared",
        question="If coordinate axes, geometric figures, or visual diagrams were intended, are they clearly present?",
        bad_answer="no",
        penalty=0.25,
        is_critical=False,
        defect_desc="Expected geometric diagram, coordinate plane, or plot is missing.",
        suggested_fix="Render intended geometric shapes (e.g. Axes, Circle, NumberPlane) using Create().",
    ),
    VisualQuestionDef(
        id="stuck_frame",
        question="Is the visual animation stuck on an unintended intermediate transition or raw placeholder frame?",
        bad_answer="yes",
        penalty=0.40,
        is_critical=True,
        defect_desc="Animation appears frozen on an incomplete or corrupted transition frame.",
        suggested_fix="Ensure all animations finish cleanly and conclude with a stable self.wait(1.0).",
    ),
    VisualQuestionDef(
        id="labels_readable",
        question="Are all text labels and annotations clearly readable with strong contrast against the background?",
        bad_answer="no",
        penalty=0.25,
        is_critical=False,
        defect_desc="Poor color contrast or unreadable labels against dark background.",
        suggested_fix="Use high-contrast colors: YELLOW, GOLD, TEAL, WHITE on dark backgrounds.",
    ),
    VisualQuestionDef(
        id="layout_coherent",
        question="Is the overall visual layout organized, coherent, and educationally well-balanced?",
        bad_answer="no",
        penalty=0.20,
        is_critical=False,
        defect_desc="Visual layout lacks hierarchy, balance, or pedagogical structure.",
        suggested_fix="Organize with title at top (to_edge(UP)), main formula in center, and details below.",
    ),
]


class VisualCheckItem(BaseModel):
    """Result of an individual targeted visual question check."""

    question_id: str
    question_text: str
    passed: bool
    raw_answer: str = ""
    detail: str = ""


class VisualContext(BaseModel):
    """Contextual metadata provided to the visual critic for intelligent evaluation."""

    slide_num: int = 1
    concept: str = ""
    learning_objective: str = ""
    latex_formula: str = ""
    visible_elements: List[str] = Field(default_factory=list)
    key_definitions: List[str] = Field(default_factory=list)
    manim_code: str = ""


class VisualCriticVerdict(BaseModel):
    """Comprehensive verdict returned by a visual critic."""

    passed: bool
    score: float = Field(ge=0.0, le=1.0, description="Visual quality score between 0.0 and 1.0.")
    critic_model: str = Field(description="Name or identifier of the critic model used.")
    backend: str = Field(description="Critic backend: moondream, openrouter, ollama, hybrid, or heuristic.")
    checks: List[VisualCheckItem] = Field(default_factory=list)
    detected_issues: List[str] = Field(default_factory=list)
    suggested_fixes: List[str] = Field(default_factory=list)
    feedback_for_code_repair: str = Field(
        default="",
        description="Structured instructions formatted for prompt injection into the code repair loop.",
    )
    raw_response: Dict[str, Any] = Field(default_factory=dict)
    keyframe_path: Optional[str] = None
