"""Seeing the Computation — lecture templates from need_to_implement.py.

Render:
  .venv\\Scripts\\manim -ql examples/ecosystem_lecture.py AOSEcosystemLecture
"""

from __future__ import annotations

from manim import DOWN, RIGHT, Create, FadeIn, FadeOut, Indicate, RoundedRectangle, Text, VGroup

from aos_manim_algorithms import BinarySearchVisualizer
from aos_manim_beamer import AlertBlock, BeamerBulletFrame, BeamerFrame, ExampleBlock
from aos_manim_chemistry import Molecule2DMobject
from aos_manim_code import CodeWindow
from aos_manim_core import Cue, CueAction, get_theme, set_theme
from aos_manim_maths import DerivativeVisualizer, RootFindingVisualizer
from aos_manim_physics import ProjectileVisualizer
from aos_manim_proofs import DerivationChain, ProofStep, StepType
from aos_manim_slides import (
    BrandingIntro,
    CodeReveal,
    CopyExplain,
    QuoteCard,
    TwoColumnBullets,
    VoiceoverSlideScene,
)


BS_CODE = """def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1"""


class AOSEcosystemLecture(VoiceoverSlideScene):
    """Lecture-quality tour using reusable branding / quote / bullet / copy templates."""

    def construct(self):
        set_theme("academic_oxford")
        self.lecture_gap = 0.5
        self.camera.background_color = get_theme().background
        self._on_stage = None

        self._branding()
        self._quote()
        self._agenda()
        self._derivative()
        self._newton()
        self._projectile()
        self._water()
        self._binary_search()
        self._code()
        self._proof()
        self._close()

    def _swap(self, mob) -> None:
        if self._on_stage is not None:
            self.play(FadeOut(self._on_stage), run_time=0.4)
        self.add(mob)
        self._on_stage = mob

    def _branding(self) -> None:
        intro = BrandingIntro(
            brand="AOS Manim",
            byline="Eight plugins. One theme.",
            lecture_title="Seeing the Computation",
            subtitle="Models, motion, molecules, and proofs",
        )
        self.add(intro)
        self._on_stage = intro
        intro.play_on(self)

    def _quote(self) -> None:
        card = QuoteCard(
            "What I cannot create,\nI do not understand.",
            author="— Richard Feynman",
            font_size=44,
        )
        self._swap(card)
        self.beats(
            "A lecture is a computation you can see. "
            "<bookmark mark='Q0'/>Feynman: what I cannot create, I do not understand.",
            [("Q0", lambda: card.play_on(self))],
        )

    def _agenda(self) -> None:
        board = TwoColumnBullets(
            "Today's agenda",
            [
                "Slope of a smooth curve",
                "Newton's method",
                "The same calculus in flight",
                "Geometry of water",
                "Halving a search",
            ],
            [
                "The code that searches",
                "A short derivation",
                "One shared theme",
                "What to take with you",
                "Thank you",
            ],
            font_size=28,
        )
        for row in board.left_mobs:
            row.set_opacity(0)
        for row in board.right_mobs:
            row.set_opacity(0)
        self._swap(board)
        n = board.row_count()
        spoken = "Here is the path. <bookmark mark='At'/>The title. " + " ".join(
            f"<bookmark mark='A{i}'/>Next." for i in range(n)
        )
        self.beats(
            spoken,
            [("At", lambda: board.play_title(self))]
            + [(f"A{i}", lambda k=i: board.play_row(self, k)) for i in range(n)],
        )

    def _derivative(self) -> None:
        vis = DerivativeVisualizer()
        packed = vis.build_derivative_mobjects("x**2 - 2*x", 2.0, axes_width=5.0, axes_height=3.0)
        graph = VGroup(packed["axes"], packed["curve"], packed["tangent_line"], packed["point"]).scale(0.7)
        panel = CopyExplain(
            "The slope of a curve",
            ["The curve is smooth", "The tangent is the derivative at a point"],
            [graph],
            font_size=28,
        )
        for d in panel.diagrams:
            d.set_opacity(0)
        for row in panel.bullet_mobs:
            row.set_opacity(0)
        self._swap(panel)
        self.beats(
            "Start with a derivative. "
            "<bookmark mark='D0'/>The title. "
            "<bookmark mark='D1'/>A smooth curve. "
            "<bookmark mark='D2'/>The tangent is the slope. "
            "<bookmark mark='D3'/>Copy the idea onto the plot.",
            [
                ("D0", lambda: panel.play_title(self)),
                ("D1", lambda: panel.play_item(self, 0)),
                ("D2", lambda: panel.play_item(self, 1)),
                ("D3", lambda: panel.play_copy(self, 0)),
            ],
        )
        self.play(Indicate(packed["tangent_line"], color=get_theme().highlight_a), run_time=0.6)

    def _newton(self) -> None:
        vis = RootFindingVisualizer()
        newton = vis.build_cueable_root_finding(
            "x**2 - 2", 1.5, axes_width=5.0, axes_height=3.0, show_all_steps=False
        ).scale(0.68)
        panel = CopyExplain(
            "Newton's method",
            ["Ride the tangent to the next guess", "Near a simple root it converges"],
            [newton],
            font_size=28,
        )
        for d in panel.diagrams:
            d.set_opacity(0)
        for row in panel.bullet_mobs:
            row.set_opacity(0)
        newton.base.set_opacity(0)
        for g in newton.step_groups:
            g.set_opacity(0)
        self._swap(panel)

        def reveal_plot():
            self.play(FadeIn(panel.bullet_mobs[0], shift=RIGHT), run_time=0.35)
            newton.apply_cue(self, Cue(mark="Nb", target_id="n", action=CueAction.REVEAL))

        n_steps = min(newton.step_count(), 4)
        step_beats = []
        for i in range(n_steps):
            step_beats.append(
                (
                    f"Ns{i}",
                    lambda k=i: newton.apply_cue(
                        self, Cue(mark=f"Ns{k}", target_id="n", action=CueAction.STEP, payload={"i": k})
                    ),
                )
            )
        self.beats(
            "Newton rides the tangent. "
            "<bookmark mark='N0'/>The idea. "
            "<bookmark mark='Nb'/>The curve."
            + "".join(f" <bookmark mark='Ns{i}'/>Next iterate." for i in range(n_steps))
            + " <bookmark mark='Ntip'/>It converges near a simple root.",
            [
                ("N0", lambda: panel.play_title(self)),
                ("Nb", reveal_plot),
                *step_beats,
                ("Ntip", lambda: self.play(FadeIn(panel.bullet_mobs[1], shift=RIGHT), run_time=0.35)),
            ],
        )

    def _projectile(self) -> None:
        vis = ProjectileVisualizer()
        packed = vis.build_projectile_mobjects(v0=20.0, theta_deg=45.0, axes_width=5.2, axes_height=3.0)
        graph = VGroup(packed["axes"], packed["curve"], packed["launch_vector"], packed["peak_dot"]).scale(0.65)
        packed["curve"].set_opacity(0)
        packed["peak_dot"].set_opacity(0)
        packed["launch_vector"].set_opacity(0)
        panel = CopyExplain(
            "The same calculus in flight",
            ["Launch at forty-five degrees", "The peak is where vertical speed vanishes"],
            [graph],
            font_size=28,
        )
        for row in panel.bullet_mobs:
            row.set_opacity(0)
        packed["axes"].set_opacity(1)
        self._swap(panel)

        def launch():
            self.play(FadeIn(panel.bullet_mobs[0], shift=RIGHT), run_time=0.35)
            self.play(FadeIn(packed["launch_vector"]), Create(packed["curve"]), run_time=0.9)

        def peak():
            self.play(FadeIn(panel.bullet_mobs[1], shift=RIGHT), run_time=0.35)
            self.play(FadeIn(packed["peak_dot"]), Indicate(packed["peak_dot"], color=get_theme().highlight_a), run_time=0.6)

        self.beats(
            "That derivative lives in a trajectory. "
            "<bookmark mark='P0'/>The title. "
            "<bookmark mark='P1'/>Launch. "
            "<bookmark mark='P2'/>The peak.",
            [
                ("P0", lambda: panel.play_title(self)),
                ("P1", launch),
                ("P2", peak),
            ],
        )

    def _water(self) -> None:
        water = Molecule2DMobject.create_water().scale(1.25)
        box = RoundedRectangle(width=4.2, height=2.6, corner_radius=0.2, color=get_theme().primary)
        diagram = VGroup(box, water.move_to(box.get_center()))
        panel = CopyExplain(
            "Geometry of water",
            ["Bent, not linear", "Oxygen, then the two hydrogens"],
            [diagram],
            font_size=28,
        )
        for row in panel.bullet_mobs:
            row.set_opacity(0)
        diagram.set_opacity(0)
        self._swap(panel)
        self.beats(
            "A molecule is a computation too. "
            "<bookmark mark='W0'/>The title. "
            "<bookmark mark='W1'/>Bent water. "
            "<bookmark mark='W2'/>Indicate the atoms.",
            [
                ("W0", lambda: panel.play_title(self)),
                ("W1", lambda: (self.play(FadeIn(panel.bullet_mobs[0], shift=RIGHT), run_time=0.35), panel.play_copy(self, 0))),
                (
                    "W2",
                    lambda: (
                        self.play(FadeIn(panel.bullet_mobs[1], shift=RIGHT), run_time=0.3),
                        self.play(Indicate(water.atoms[0], color=get_theme().highlight_a), run_time=0.5),
                    ),
                ),
            ],
        )

    def _binary_search(self) -> None:
        vis = BinarySearchVisualizer()
        search = vis.build_cueable_binary_search([1, 3, 5, 7, 9, 11, 13], 7).scale(0.68)
        panel = CopyExplain(
            "Halving the search",
            ["A sorted array; the target is seven", "Each step throws away half the work"],
            [search],
            font_size=26,
        )
        for row in panel.bullet_mobs:
            row.set_opacity(0)
        search.base.set_opacity(0)
        self._swap(panel)
        n = search.step_count()
        steps = [
            (
                f"Bs{i}",
                lambda k=i: search.apply_cue(
                    self, Cue(mark=f"Bs{k}", target_id="b", action=CueAction.STEP, payload={"i": k})
                ),
            )
            for i in range(n)
        ]
        self.beats(
            "Now search. "
            "<bookmark mark='B0'/>The title. "
            "<bookmark mark='B1'/>The array."
            + "".join(f" <bookmark mark='Bs{i}'/>Halve." for i in range(n))
            + " <bookmark mark='Btip'/>Half the work is gone.",
            [
                ("B0", lambda: panel.play_title(self)),
                (
                    "B1",
                    lambda: (
                        self.play(FadeIn(panel.bullet_mobs[0], shift=RIGHT), run_time=0.3),
                        search.apply_cue(self, Cue(mark="B1", target_id="b", action=CueAction.REVEAL)),
                    ),
                ),
                *steps,
                ("Btip", lambda: self.play(FadeIn(panel.bullet_mobs[1], shift=RIGHT), run_time=0.35)),
            ],
        )

    def _code(self) -> None:
        win = CodeWindow(code=BS_CODE, filename="search.py", width=7.0, height=4.2).scale(0.85)
        reveal = CodeReveal(win, title="The code that searches")
        self._swap(reveal)
        self.beats(
            "Here is the same idea in Python. "
            "<bookmark mark='C0'/>Create the listing. "
            "<bookmark mark='C3'/>The loop. "
            "<bookmark mark='C4'/>The midpoint. "
            "<bookmark mark='C5'/>A hit returns.",
            [
                ("C0", lambda: reveal.play_on(self)),
                ("C3", lambda: reveal.highlight_line(self, 3)),
                ("C4", lambda: reveal.highlight_line(self, 4)),
                ("C5", lambda: reveal.highlight_line(self, 5)),
            ],
        )

    def _proof(self) -> None:
        chain = DerivationChain(
            theorem=r"x_{n+1}=x_n-\frac{f(x_n)}{f'(x_n)}",
            steps=[
                ProofStep("s1", r"f'(x_n)\neq 0", "local slope", StepType.ASSUMPTION),
                ProofStep("s2", r"y=f(x_n)+f'(x_n)(x-x_n)", "tangent", StepType.INFERENCE, ["s1"]),
                ProofStep("s3", r"0=f(x_n)+f'(x_n)(x_{n+1}-x_n)", "intercept", StepType.QED, ["s2"]),
            ],
            width=10.0,
        ).scale(0.82)
        header = chain.submobjects[0]
        rows = chain.submobjects[1] if len(chain.submobjects) > 1 else VGroup()
        for row in rows:
            row.set_opacity(0)
        title = Text("A short derivation", font_size=36, color=get_theme().primary, weight="BOLD")
        group = VGroup(title, chain).arrange(DOWN, buff=0.35)
        self._swap(group)
        self.beats(
            "Why the update? "
            "<bookmark mark='R0'/>The theorem. "
            "<bookmark mark='R1'/>A nonzero slope. "
            "<bookmark mark='R2'/>The tangent. "
            "<bookmark mark='R3'/>The intercept is the next guess.",
            [
                ("R0", lambda: None),
                ("R1", lambda: self.play(FadeIn(rows[0]), run_time=0.4) if len(rows) else None),
                ("R2", lambda: self.play(FadeIn(rows[1]), run_time=0.4) if len(rows) > 1 else None),
                ("R3", lambda: self.play(FadeIn(rows[2]), run_time=0.4) if len(rows) > 2 else None),
            ],
        )

    def _close(self) -> None:
        frame = BeamerBulletFrame(
            "What to take with you",
            [
                "You saw slope, Newton, flight, water, search, code, and a proof",
                "Every plugin shared one theme and one cue language",
            ],
            section="Close",
            frame_number=10,
            total_frames=10,
        )
        for row in frame.board.bullet_mobs:
            row.set_opacity(0)
        self._swap(frame)
        b1 = ExampleBlock("You saw the computation", "Timed to speech, not dumped on screen.", width=10.0, body_height=1.2)
        b2 = AlertBlock("One protocol", "Theme tokens, validators, and bookmark cues.", width=10.0, body_height=1.2)
        extras = VGroup(b1, b2).arrange(DOWN, buff=0.25).scale(0.85)
        extras.next_to(frame.board, DOWN, buff=0.3)
        extras.set_opacity(0)
        frame.add(extras)
        thanks = Text("Thank you", font_size=44, color=get_theme().text_main, weight="BOLD")
        thanks.move_to(frame.get_content_center())
        thanks.set_opacity(0)
        frame.add(thanks)
        self.beats(
            "You now have the whole arc. "
            "<bookmark mark='Z0'/>The bullets. "
            "<bookmark mark='Z1'/>The stack is one protocol. "
            "<bookmark mark='Z2'/>Thank you.",
            [
                ("Z0", lambda: frame.play_on(self)),
                ("Z1", lambda: self.play(FadeIn(extras), run_time=0.5)),
                ("Z2", lambda: self.play(FadeOut(extras), FadeOut(frame.board), FadeIn(thanks), run_time=0.8)),
            ],
        )
        self.wait(1.0)
        self.play(FadeOut(frame), run_time=0.5)
