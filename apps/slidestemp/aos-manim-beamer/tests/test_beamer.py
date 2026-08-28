import pytest
from aos_manim_core import get_theme, set_theme
from aos_manim_beamer import (
    Block,
    AlertBlock,
    ExampleBlock,
    BeamerFrame,
    BeamerColumns,
    BeamerColumn,
    BeamerPresentation,
    BeamerFrameOverflowValidator,
)


def test_beamer_blocks():
    set_theme("academic_oxford")
    b1 = Block("Definition 1.1", "A group (G, *) is a set...")
    assert len(b1) == 3

    b2 = AlertBlock("Caution", "Division by zero is undefined.")
    assert len(b2) == 3

    b3 = ExampleBlock("Example 1", "Consider the set of integers modulo n.")
    assert len(b3) == 3


def test_beamer_frame_and_presentation():
    pres = BeamerPresentation("Abstract Algebra", theme="nord")
    f1 = pres.frame("Group Theory", subtitle="Basic Axioms", section="Introduction")
    assert len(pres) == 1
    assert f1.title_text is not None

    b = Block("Closure Axiom", "For all a, b in G, a * b in G.")
    f1.add_content(b)

    val = BeamerFrameOverflowValidator()
    res = val.validate(f1)
    assert res.is_valid


def test_beamer_lecture_frames():
    set_theme("academic_oxford")
    from aos_manim_beamer import BeamerBulletFrame, BeamerQuoteFrame

    bullets = BeamerBulletFrame("Outline", ["Alpha", "Beta"])
    assert len(bullets.board.bullet_mobs) == 2
    quote = BeamerQuoteFrame("Epigraph", "See the computation.", author="— AOS")
    assert quote.card.quote is not None

    class Dummy:
        def play(self, *a, **k):
            pass

        def wait(self, t=0):
            pass

        def add(self, *a):
            pass

    bullets.play_on(Dummy())
    quote.play_on(Dummy())
