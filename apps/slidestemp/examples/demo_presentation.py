from __future__ import annotations

from manim import *
from aos_manim_core import set_theme, use_theme, MODERN_DARK, ACADEMIC_OXFORD, NORD, CYBERPUNK
from aos_manim_slides import SlideScene, TitleSlide, ContentSlide, TwoColumnSlide
from aos_manim_maths import DerivativeVisualizer, IntegralVisualizer
from aos_manim_algorithms import ArrayMobject, BinarySearchVisualizer
from aos_manim_physics import ProjectileVisualizer, FreeBodyDiagram
from aos_manim_code import CodeWindow
from aos_manim_proofs import DerivationChain, ProofStep, StepType
from aos_manim_chemistry import Molecule2DMobject
from aos_manim_beamer import Block, AlertBlock, ExampleBlock, BeamerFrame


class AOSComprehensiveDemoScene(SlideScene):
    """Demonstrates all 8 plugins working synergistically under a shared theme."""

    def construct(self):
        # Apply Academic Oxford Theme
        set_theme("academic_oxford")

        # 1. Slide Plugin: Title Slide
        title_slide = TitleSlide(
            title="AOS Manim Platform",
            subtitle="Modular Computational Visualization Engine",
            author="Google DeepMind Advanced Agentic Coding",
            date="2026",
            affiliation="Autonomous Scientific Discovery",
        )
        self.show_slide(title_slide, transition="fade")
        self.pause_slide(1.0)

        # 2. Maths Plugin: Derivative
        math_vis = DerivativeVisualizer()
        deriv_mobs = math_vis.build_derivative_mobjects("x**2 - 2*x", 2.0)
        math_slide = ContentSlide(
            title="Calculus Precision: Derivative",
            bullets=[
                "Symbolically computed with SymPy",
                "Evaluates instantaneous rate of change",
                "Verifies tangent line invariants",
            ],
        )
        deriv_group = VGroup(deriv_mobs["axes"], deriv_mobs["curve"], deriv_mobs["tangent_line"], deriv_mobs["point"]).scale(0.7)
        deriv_group.to_corner(RIGHT + DOWN)
        math_slide.add_content(deriv_group)
        self.show_slide(math_slide, transition="wipe")
        self.pause_slide(1.0)

        # 3. Algorithms Plugin: Binary Search
        bs_vis = BinarySearchVisualizer()
        bs_mobs = bs_vis.build_binary_search_mobjects([1, 3, 5, 7, 9, 11, 13], 7)
        algo_slide = ContentSlide(
            title="Reasoning: Binary Search",
            bullets=[
                "Stepped state trace inspection",
                "Pointer bounds halving",
                "Verified sorted monotonic invariant",
            ],
        )
        bs_group = VGroup(bs_mobs["array_mob"], bs_mobs["header"], bs_mobs["status_text"]).scale(0.8)
        bs_group.to_corner(RIGHT + DOWN)
        algo_slide.add_content(bs_group)
        self.show_slide(algo_slide, transition="wipe")
        self.pause_slide(1.0)

        # 4. Physics Plugin: Projectile Motion
        phys_vis = ProjectileVisualizer()
        proj_mobs = phys_vis.build_projectile_mobjects(v0=20.0, theta_deg=45.0)
        phys_slide = ContentSlide(
            title="STEM Physics: Kinematic Trajectory",
            bullets=[
                "Nonlinear differential kinematic integration",
                "Launch angle & velocity decomposition",
                "Verified conservation laws",
            ],
        )
        proj_group = VGroup(proj_mobs["axes"], proj_mobs["curve"], proj_mobs["launch_vector"], proj_mobs["peak_dot"]).scale(0.7)
        proj_group.to_corner(RIGHT + DOWN)
        phys_slide.add_content(proj_group)
        self.show_slide(phys_slide, transition="wipe")
        self.pause_slide(1.0)

        # 5. Chemistry Plugin: Molecular Geometry
        h2o = Molecule2DMobject.create_water().scale(1.3)
        chem_slide = ContentSlide(
            title="STEM Chemistry: Molecular Geometry",
            bullets=[
                "Water (H2O) bent geometry",
                "Standard CPK & theme-aware colors",
                "Valence and bond order verified",
            ],
        )
        h2o.to_corner(RIGHT + DOWN).shift(UP * 0.5 + LEFT * 1.0)
        chem_slide.add_content(h2o)
        self.show_slide(chem_slide, transition="wipe")
        self.pause_slide(1.0)

        # 6. Beamer Plugin: Frame & Blocks
        beamer_frame = BeamerFrame(
            title="Summary & Next Horizons",
            subtitle="Extensible Architecture",
            section="Conclusion",
            frame_number=6,
            total_frames=6,
        )
        b1 = ExampleBlock("Platform Success", "8 modular domain plugins operating on shared protocol.")
        b2 = AlertBlock("LKG Integration Ready", "Machine-readable capability manifests ready for indexing.")
        beamer_group = VGroup(b1, b2).arrange(DOWN, buff=0.4).move_to(beamer_frame.get_content_center())
        beamer_frame.add_content(beamer_group)
        self.show_slide(beamer_frame, transition="zoom")
        self.pause_slide(1.0)
