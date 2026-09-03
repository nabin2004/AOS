"""Visual Component Library for Pedagogical Manim scene generation."""

from __future__ import annotations

from typing import Dict, List
from pydantic import BaseModel, Field


class ComponentSnippet(BaseModel):
    """Reusable Manim visual component template for prompt injection."""

    name: str = Field(description="Name of the component snippet")
    description: str = Field(description="Explanation of pedagogical use case")
    code_template: str = Field(description="Executable Python/Manim template code")


MATH_CALLOUT = ComponentSnippet(
    name="MathCalloutCard",
    description="Highlighted card container with title, LaTeX formula, and explanation note.",
    code_template="""\
def create_math_callout(title_text: str, formula_tex: str, note_text: str = "") -> VGroup:
    title = Text(title_text, font_size=24, color=PRIMARY_COLOR, weight=BOLD)
    formula = MathTex(formula_tex, font_size=32, color=MATH_COLOR)
    card_content = VGroup(title, formula)
    if note_text:
        note = Text(note_text, font_size=18, color=SUBTEXT_COLOR)
        card_content.add(note)
    card_content.arrange(DOWN, aligned_edge=LEFT, buff=0.25)
    
    box = SurroundingRectangle(card_content, buff=0.3, corner_radius=0.15)
    box.set_stroke(color=PRIMARY_COLOR, width=2, opacity=0.8)
    box.set_fill(color=BG_COLOR, opacity=0.85)
    return VGroup(box, card_content)
""",
)

PROOF_CONTAINER = ComponentSnippet(
    name="ProofContainer",
    description="Step-by-step visual mathematical deduction container.",
    code_template="""\
def create_proof_step(step_number: int, claim_tex: str, reason_text: str) -> VGroup:
    badge = Text(f"{step_number}", font_size=18, color=BG_COLOR, weight=BOLD)
    circle = Circle(radius=0.22, color=SECONDARY_COLOR, fill_opacity=1.0)
    badge.move_to(circle.get_center())
    step_indicator = VGroup(circle, badge)
    
    claim = MathTex(claim_tex, font_size=28, color=TEXT_COLOR)
    reason = Text(reason_text, font_size=18, color=SUBTEXT_COLOR)
    body = VGroup(claim, reason).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
    
    return VGroup(step_indicator, body).arrange(RIGHT, buff=0.3, aligned_edge=UP)
""",
)

CODE_WINDOW = ComponentSnippet(
    name="CodeWindow",
    description="Code editor container with macOS-style window controls and syntax highlighting.",
    code_template="""\
def create_code_window(code_str: str, language: str = "python", title: str = "main.py") -> VGroup:
    code_block = Code(
        code=code_str,
        tab_width=4,
        background="window",
        language=language,
        font="Monospace",
        insert_line_no=True,
        style="monokai",
    )
    header_bar = Rectangle(
        width=code_block.width,
        height=0.4,
        fill_color="#181824",
        fill_opacity=1.0,
        stroke_width=0,
    ).next_to(code_block, UP, buff=0)
    
    dots = VGroup(*[
        Dot(radius=0.06, color=c)
        for c in ["#FF5F56", "#FFBD2E", "#27C93F"]
    ]).arrange(RIGHT, buff=0.12).next_to(header_bar.get_left(), RIGHT, buff=0.2)
    
    win_title = Text(title, font_size=16, color="#8888AA").move_to(header_bar.get_center())
    return VGroup(code_block, header_bar, dots, win_title)
""",
)

DYNAMIC_NUMBER_LINE = ComponentSnippet(
    name="DynamicNumberLine",
    description="Styled numerical axis with custom intervals, pointers, and value indicators.",
    code_template="""\
def create_highlighted_number_line(x_min: float, x_max: float, step: float = 1.0) -> NumberLine:
    nl = NumberLine(
        x_range=[x_min, x_max, step],
        length=8,
        color=TEXT_COLOR,
        include_numbers=True,
        font_size=20,
    )
    nl.numbers.set_color(SUBTEXT_COLOR)
    return nl
""",
)

COMPONENT_REGISTRY: Dict[str, ComponentSnippet] = {
    "MathCalloutCard": MATH_CALLOUT,
    "ProofContainer": PROOF_CONTAINER,
    "CodeWindow": CODE_WINDOW,
    "DynamicNumberLine": DYNAMIC_NUMBER_LINE,
}


def get_component_gallery() -> List[ComponentSnippet]:
    """Retrieve all available component snippets."""
    return list(COMPONENT_REGISTRY.values())


def get_components_prompt_injection() -> str:
    """Generate formatting guidelines and reusable helper snippets for Coder prompt context."""
    blocks = [
        "### Pre-Engineered Pedagogical Visual Components:",
        "You can define and use these modular visual components to build beautiful, non-overlapping layouts:\n",
    ]
    for comp in COMPONENT_REGISTRY.values():
        blocks.append(f"#### {comp.name}: {comp.description}")
        blocks.append(f"```python\n{comp.code_template}```\n")
    return "\n".join(blocks)
