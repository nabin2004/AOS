import pytest
from pathlib import Path

from aos_manim_core import get_theme, set_theme, use_theme
from aos_manim_slides import (
    Slide,
    TitleSlide,
    SectionSlide,
    ContentSlide,
    TwoColumnSlide,
    QuizSlide,
    Card,
    Badge,
    SlideOverflowValidator,
    SlideSpec,
    Paragraph,
    Equation,
    DiagramRef,
    AnimationSlot,
    ListBlock,
    Callout,
    parse_markdown,
    parse_slide_markdown,
    LayoutEngine,
    VStack,
    HStack,
    Rect,
)
from aos_manim_slides.layout.box import LayoutContext, LeafNode
from aos_manim_slides.layout.overflow import OverflowSolver, check_overflow
from aos_manim_slides.diagrams import known_diagrams, DiagramNotFoundError, build_diagram
from manim import Text, VGroup


NEWTON_MD = """---
layout: equation-focus
title: Newton's Method
---

# Newton's Method

Newton's method iteratively improves an estimate of a root.

$$
x_{n+1}=x_n-\\frac{f(x_n)}{f'(x_n)}
$$

:::diagram
newton_method(f=x^2-2)
:::
"""

GD_MD = """---
title: Gradient Descent
layout: two-column
---

# Gradient Descent

We want to minimize:

$$
f(x) = x^2
$$

```diagram
gradient_descent(f=x**2)
```

> Move in the direction of the negative gradient.
"""


def test_card_and_badge_theme_integration():
    set_theme("academic_oxford")
    card = Card(width=5.0, height=3.0)
    assert card.background_rect is not None

    badge = Badge("TEST BADGE")
    assert len(badge) == 2


def test_slide_templates_instantiation():
    with use_theme("nord"):
        title_slide = TitleSlide(
            title="AOS Manim Platform",
            subtitle="Next-Generation Presentation Engine",
            author="DeepMind Research",
            date="2026",
        )
        assert title_slide.title_text is None
        assert len(title_slide.content_group) > 0
        assert title_slide.spec.layout == "title"

        section_slide = SectionSlide("Calculus Visualizations", section_number=1)
        assert len(section_slide.content_group) > 0

        content_slide = ContentSlide(
            title="Core Objectives",
            bullets=["Dynamic Theming", "Precise Computation", "Automated Validation"],
            callout=("Key Takeaway", "LKG and Plugins are cleanly separated."),
        )
        assert len(content_slide.content_group) > 0

        left = VGroup(Text("Left Column"))
        right = VGroup(Text("Right Column"))
        two_col = TwoColumnSlide(title="Comparison", left_content=left, right_content=right)
        assert len(two_col.content_group) >= 1

        quiz = QuizSlide(
            question="What is the derivative of x^2?",
            options=["2x", "x^3 / 3", "2", "x"],
            correct_index=0,
        )
        assert quiz.correct_index == 0


def test_slide_overflow_validator():
    validator = SlideOverflowValidator()
    slide = ContentSlide(
        title="Valid Slide",
        bullets=["Point 1", "Point 2"],
    )
    result = validator.validate(slide)
    assert result.is_valid


def test_markdown_newton_and_gd_ast():
    newton = parse_slide_markdown(NEWTON_MD)
    assert newton.layout == "equation-focus"
    assert newton.title == "Newton's Method"
    assert any(isinstance(b, Equation) for b in newton.blocks)
    diagrams = [b for b in newton.blocks if isinstance(b, DiagramRef)]
    assert diagrams and diagrams[0].name == "newton_method"
    assert "x" in str(diagrams[0].kwargs.get("f", "")).replace(" ", "")

    gd = parse_slide_markdown(GD_MD)
    assert gd.layout == "two-column"
    assert gd.title == "Gradient Descent"
    assert any(isinstance(b, Equation) for b in gd.blocks)
    assert any(isinstance(b, DiagramRef) and b.name == "gradient_descent" for b in gd.blocks)
    assert any(isinstance(b, Callout) for b in gd.blocks)

    deck = parse_markdown(NEWTON_MD + "\n---\n" + GD_MD)
    assert len(deck.slides) >= 2


def test_example_markdown_deck_parses():
    path = Path(__file__).resolve().parents[2] / "examples" / "slides" / "calculus_methods.md"
    if not path.exists():
        pytest.skip("example deck not present")
    presentation = parse_markdown(path.read_text(encoding="utf-8"))
    layouts = {slide.layout for slide in presentation.slides}
    assert "title" in layouts
    assert "two-column" in layouts
    assert "equation-focus" in layouts
    assert "diagram-focus" in layouts
    assert "code-focus" in layouts


def test_vstack_hstack_occupancy():
    theme = get_theme()
    ctx = LayoutContext(theme=theme, spacing=0.2)
    a = LeafNode(lambda c, r: Text("Alpha", font_size=24, color=theme.text_main), align="center")
    b = LeafNode(lambda c, r: Text("Beta", font_size=24, color=theme.text_main), align="center")
    rect = Rect(-4, -2, 8, 4)
    stack = VStack([a, b], spacing=0.2)
    stack.layout(ctx, rect)
    assert stack.mobject is not None
    issues = check_overflow(stack, rect, epsilon=0.2)
    assert issues == []
    assert a.mobject.get_center()[1] > b.mobject.get_center()[1]

    left = LeafNode(lambda c, r: Text("L", font_size=28, color=theme.text_main))
    right = LeafNode(lambda c, r: Text("R", font_size=28, color=theme.text_main))
    row = HStack([left, right], spacing=0.3, ratios=[0.4, 0.6])
    row.layout(ctx, rect)
    assert left.mobject.get_center()[0] < right.mobject.get_center()[0]
    assert check_overflow(row, rect, epsilon=0.2) == []


def test_overflow_solver_priority_tactics():
    spec = SlideSpec(
        title="Crowded",
        layout="two-column",
        left=[
            ListBlock(items=["Overflow item " + str(i) for i in range(4)]),
            Callout(title="Aside", body="Drop me.", role="decoration"),
        ],
        right=[Paragraph(text="Body column text.")],
    )
    engine = LayoutEngine(solver=OverflowSolver(max_attempts=8))
    tiny = Rect(-1.2, -0.8, 2.4, 1.6)
    root, report, ctx = engine.layout_spec(spec, tiny, aspect_ratio=16 / 9)
    assert report.attempts >= 1
    assert report.tactics
    assert root.mobject is not None


def test_responsive_column_collapse():
    spec = SlideSpec(
        title="Wide vs Narrow",
        layout="two-column",
        left=[Paragraph("Explanation of the method.")],
        right=[Paragraph("A diagram stand-in.")],
    )
    engine = LayoutEngine()
    rect = Rect(-5, -2.5, 10, 5)
    ctx_wide = engine.context_from_theme(aspect_ratio=16 / 9, collapse_columns=False)
    assert ctx_wide.collapse_columns is False
    ctx_narrow = engine.context_from_theme(aspect_ratio=4 / 3, collapse_columns=None)
    assert ctx_narrow.aspect_ratio < 1.4
    assert ctx_narrow.collapse_columns is True

    root_wide, _, _ = engine.layout_spec(spec, rect, aspect_ratio=16 / 9)
    root_narrow, _, ctx_n = engine.layout_spec(spec, rect, aspect_ratio=4 / 3)
    assert ctx_n.collapse_columns is True
    assert root_wide.mobject is not None
    assert root_narrow.mobject is not None


def test_unknown_diagram_is_explicit():
    with pytest.raises(DiagramNotFoundError) as exc:
        build_diagram("not_a_real_diagram", 4, 3)
    assert "gradient_descent" in str(exc.value)
    assert "newton_method" in known_diagrams()


def test_slide_from_markdown_and_spec():
    slide = Slide.from_markdown(GD_MD)
    assert slide.spec.layout == "two-column"
    assert len(slide.content_group) > 0

    spec = SlideSpec(
        title="Gradient Descent",
        layout="two-column",
        left=[Paragraph("We minimize a function"), Equation(r"\nabla f(x)")],
        right=[Paragraph("diagram placeholder")],
    )
    built = Slide.from_spec(spec)
    assert built.layout_report is not None
    assert built.get_content_rect().width > 1.0


def test_multiline_voiceover_and_auto_ids():
    md = """---
layout: title-content
title: Chain Rule
voiceover: |
  Intro line.
  <bookmark mark='li0'/>First bullet.
  <bookmark mark='li1'/>Second bullet.
---

# Chain Rule

Some body text.

- Outer derivative
- Inner derivative
"""
    spec = parse_slide_markdown(md)
    assert spec.voiceover is not None
    assert "li0" in spec.voiceover
    assert "First bullet" in spec.voiceover

    from aos_manim_slides import assign_content_ids, auto_script_from_spec, script_for_slide

    assign_content_ids(spec)
    list_blocks = [b for b in spec.blocks if isinstance(b, ListBlock)]
    assert list_blocks
    assert len(list_blocks[0].item_ids) == 2
    assert any(isinstance(b, Equation) is False for b in spec.blocks)

    auto = auto_script_from_spec(spec)
    revealable = [c for c in auto.cues if c.action.value == "reveal"]
    assert len(revealable) >= 3
    authored = script_for_slide(spec)
    marks = [c.mark for c in authored.cues]
    assert "li0" in marks and "li1" in marks


def test_lecture_hide_then_reveal_list_items():
    from aos_manim_core import CueResolver, play_script
    from aos_manim_slides.narration import hide_lecture_body, script_for_slide

    spec = SlideSpec(
        title="Agenda",
        layout="title-content",
        blocks=[ListBlock(items=["Why London", "Mainline", "Jobava"])],
    )
    slide = Slide.from_spec(spec)
    assert "li0" in slide.cue_index
    assert "li1" in slide.cue_index
    hide_lecture_body(slide)
    assert slide.cue_index["li0"].get_fill_opacity() < 0.2

    class Dummy:
        def wait(self, t):
            pass

    script = script_for_slide(slide.spec)
    resolver = CueResolver(targets=slide.cue_index, cueables=slide.cueables, theme=slide.theme)
    play_script(Dummy(), script, resolver, gap=0.0)
    assert slide.cue_index["li0"].get_fill_opacity() > 0.5
    assert slide.cue_index["li2"].get_fill_opacity() > 0.5


class _DummyScene:
    def __init__(self) -> None:
        self.plays = 0

    def play(self, *args, **kwargs) -> None:
        self.plays += 1

    def wait(self, t=0) -> None:
        pass

    def add(self, *args) -> None:
        pass


def test_lecture_templates_construct_and_play():
    from aos_manim_slides import BrandingIntro, BulletBoard, QuoteCard, TwoColumnBullets
    from aos_manim_core import set_theme

    set_theme("academic_oxford")
    brand = BrandingIntro(brand="AOS", lecture_title="Lecture 1", subtitle="Sub")
    assert brand.brand is not None
    dummy = _DummyScene()
    brand.play_on(dummy)
    assert dummy.plays >= 2

    quote = QuoteCard("See the computation.", author="— AOS")
    dummy = _DummyScene()
    quote.play_on(dummy)
    assert dummy.plays >= 2

    board = BulletBoard("Agenda", ["One", "Two", "Three"])
    dummy = _DummyScene()
    board.play_on(dummy)
    assert dummy.plays >= 4
    assert len(board.bullet_mobs) == 3

    cols = TwoColumnBullets("Cols", ["L1", "L2"], ["R1", "R2", "R3"])
    dummy = _DummyScene()
    cols.play_on(dummy)
    assert cols.row_count() == 3
    assert dummy.plays >= 4


def test_content_packs_from_the_top():
    spec = SlideSpec(
        title="Agenda",
        layout="title-content",
        blocks=[ListBlock(items=["Alpha", "Beta", "Gamma"])],
    )
    slide = Slide.from_spec(spec)
    rect = slide.get_content_rect()
    body = slide.content_group[0]
    assert body.get_top()[1] > rect.center_y
    assert abs(body.get_top()[1] - rect.top) < 1.35


def test_animation_slot_markdown_and_placeholder():
    md = """---
layout: diagram-focus
title: Lorenz
---

```animation
lorenz(sigma=10, rho=28)
```
"""
    spec = parse_slide_markdown(md)
    slots = [b for b in spec.blocks if isinstance(b, AnimationSlot)]
    assert slots and slots[0].name == "lorenz"
    assert slots[0].kwargs.get("sigma") == 10
    slide = Slide.from_spec(spec)
    assert len(slide.content_group) > 0

    from aos_manim_slides.typography import slide_tex

    mob = slide_tex("Hello", font_size=24)
    assert getattr(mob, "font", None) != "Sans"


def test_bullet_board_cue_ids_and_auto_voiceover_bookmarks():
    from aos_manim_slides import BulletBoard, auto_script_from_spec

    board = BulletBoard("Agenda", ["One", "Two"])
    assert board.cue_ids == ["li0", "li1"]
    assert "li0" in board.cue_targets()
    script = board.voiceover_script()
    assert "li0" in script and "One" in script

    spec = SlideSpec(
        title="Chain",
        layout="title-content",
        blocks=[ListBlock(items=["Outer", "Inner"])],
    )
    from aos_manim_slides import assign_content_ids, auto_script_from_spec

    auto = auto_script_from_spec(spec)
    marks = [c.mark for c in auto.cues]
    assert any(m.startswith("li") for m in marks)
    assert "<bookmark" in auto.as_voiceover_text()
