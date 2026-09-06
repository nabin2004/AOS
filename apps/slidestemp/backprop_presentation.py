from __future__ import annotations

import numpy as np
from manim import (
    BLUE,
    BLUE_C,
    BLUE_E,
    DARK_GRAY,
    DOWN,
    GRAY,
    GREEN,
    GREEN_C,
    GREY_A,
    GREY_B,
    GREY_C,
    LEFT,
    MED_SMALL_BUFF,
    ORANGE,
    ORIGIN,
    PURPLE,
    PURPLE_C,
    RED,
    RED_C,
    RIGHT,
    TEAL,
    TEAL_C,
    UP,
    WHITE,
    YELLOW,
    AddTextLetterByLetter,
    Arrow,
    Axes,
    Circle,
    Create,
    CurvedArrow,
    Dot,
    FadeIn,
    FadeOut,
    Group,
    Indicate,
    Line,
    MathTex,
    MoveAlongPath,
    Polygon,
    ReplacementTransform,
    RoundedRectangle,
    SurroundingRectangle,
    Text,
    Transform,
    VGroup,
    Write,
)
from aos_manim_slides import VoiceoverSlideScene


class BrandedBackpropDeck(VoiceoverSlideScene):
    """Extreme great quality educational video with branded intro, opening audio,
    persistent chrome transitions (zero blackout cuts), particle backpropagation,
    letter-by-letter quotes, dynamic graph tracing, and term-by-term calculus.
    """

    voice: str = "alba"
    voiceover_cache: str = "voiceover_cache"
    opening_sound: str = "audio/brand_intro.mp3"

    def construct(self):
        # 1. Enable resident voiceover service
        self.enable_voiceover(voice=self.voice, cache_dir=self.voiceover_cache)

        # 2. Opening Branding Intro with Audio & Zero Title Overlap
        self.play_branding_intro()

        # 3. Slide 1: The Learning Paradigm (Establishes Persistent Chrome)
        self.play_slide_1_learning_paradigm()

        # 4. Slide 2: Optimization Landscape (Smooth Morphing & Dynamic Parabola)
        self.play_slide_2_optimization_landscape()

        # 5. Slide 3: Credit Assignment (Particle Flow Backpropagation via MoveAlongPath)
        self.play_slide_3_credit_assignment()

        # 6. Slide 4: First-Principles Understanding (Letter-by-Letter Feynman Quote)
        self.play_slide_4_feynman_approach()

        # 7. Slide 5: Summary & Next Steps (Term-by-term Matrix Calculus & Zero Dead Time)
        self.play_slide_5_summary_and_next_steps()

    # -------------------------------------------------------------------------
    # Helper: Persistent Chrome Management
    # -------------------------------------------------------------------------
    def init_chrome(self, slide_num: str, title: str, category: str = "FOUNDATIONS"):
        """Initialize the persistent header chrome and footer elements."""
        self.cat_badge_text = Text(category, font_size=16, color=TEAL_C, weight="BOLD")
        self.badge_box = SurroundingRectangle(self.cat_badge_text, color=TEAL, buff=0.08, corner_radius=0.05, stroke_width=1.2)
        self.badge_group = VGroup(self.badge_box, self.cat_badge_text).to_corner(UP + LEFT, buff=0.45)

        self.header_title = Text(f"{slide_num}  |  {title}", font_size=26, color=WHITE, weight="BOLD")
        self.header_title.next_to(self.badge_group, RIGHT, buff=0.4)

        self.divider = Line(LEFT * 6.5, RIGHT * 6.5, color=DARK_GRAY, stroke_width=1.5).shift(UP * 2.7)
        
        self.footer_brand = Text("AOS Lecture Series  •  Backpropagation", font_size=14, color=GRAY).to_corner(DOWN + LEFT, buff=0.4)
        self.footer_page = Text(slide_num, font_size=14, color=GRAY).to_corner(DOWN + RIGHT, buff=0.4)

        self.chrome_group = VGroup(self.badge_group, self.header_title, self.divider, self.footer_brand, self.footer_page)

    def morph_chrome_and_exit(self, next_num: str, next_title_text: str, next_category: str, old_content: VGroup):
        """Seamlessly morph the persistent chrome and slide out previous contents without blacking out."""
        new_title = Text(f"{next_num}  |  {next_title_text}", font_size=26, color=WHITE, weight="BOLD").next_to(self.badge_group, RIGHT, buff=0.4)
        new_badge = Text(next_category, font_size=16, color=TEAL_C, weight="BOLD").move_to(self.cat_badge_text)
        new_box = SurroundingRectangle(new_badge, color=TEAL, buff=0.08, corner_radius=0.05, stroke_width=1.2)
        new_page = Text(next_num, font_size=14, color=GRAY).to_corner(DOWN + RIGHT, buff=0.4)

        self.play(
            Transform(self.header_title, new_title),
            Transform(self.cat_badge_text, new_badge),
            Transform(self.badge_box, new_box),
            Transform(self.footer_page, new_page),
            FadeOut(old_content, shift=LEFT * 0.8),
            run_time=0.6,
        )

    # -------------------------------------------------------------------------
    # 1. Branding Intro (Zero Overlap & Staggered Cinematic Motion)
    # -------------------------------------------------------------------------
    def play_branding_intro(self):
        try:
            self.add_sound(self.opening_sound)
        except Exception:
            pass

        # Step 1: RUKUMINI Brand Screen
        brand = Text("RUKUMINI", font_size=68, color=BLUE_C, weight="BOLD")
        box = SurroundingRectangle(brand, color=WHITE, buff=0.3, corner_radius=0.1, stroke_width=2.5)
        nabin = Text("by Nabin", font_size=28, color=GREY_A).next_to(box, DOWN, buff=0.35)

        self.play(Write(brand), run_time=0.9)
        self.play(Create(box), FadeIn(nabin, shift=UP * 0.2), run_time=0.7)
        self.wait(1.0)

        # Step 2: COMPLETE EXIT OF BRAND BEFORE TITLE APPEARS (NO OVERLAP)
        self.play(FadeOut(VGroup(brand, box, nabin), shift=UP * 0.35), run_time=0.6)
        self.clear()
        self.wait(0.2)

        # Step 3: Title Card
        lec_badge = Text("LECTURE 01", font_size=20, color=TEAL, weight="BOLD").shift(UP * 1.5)
        lec_box = SurroundingRectangle(lec_badge, color=TEAL, buff=0.1, corner_radius=0.08, stroke_width=1.5)
        topic = Text("Backpropagation", font_size=56, color=WHITE, weight="BOLD").next_to(lec_box, DOWN, buff=0.4)
        subtitle = Text("Teaching a Neural Network to Learn", font_size=26, color=BLUE_C).next_to(topic, DOWN, buff=0.35)
        title_group = VGroup(lec_box, lec_badge, topic, subtitle)

        self.play(FadeIn(VGroup(lec_box, lec_badge), shift=DOWN * 0.2), Write(topic), FadeIn(subtitle, shift=UP * 0.2), run_time=1.1)
        self.wait(1.3)

        # Step 4: Clean fade out of title card before Slide 1
        self.play(FadeOut(title_group, shift=UP * 0.3), run_time=0.5)
        self.clear()

    # -------------------------------------------------------------------------
    # 2. Slide 1: The Learning Paradigm (Establishes Persistent Chrome)
    # -------------------------------------------------------------------------
    def play_slide_1_learning_paradigm(self):
        self.init_chrome("01", "The Learning Paradigm", "FOUNDATIONS")
        self.play(FadeIn(self.chrome_group), run_time=0.5)

        # Card 1: Forward Propagation
        c1_box = RoundedRectangle(corner_radius=0.12, width=3.8, height=4.2, color=BLUE_E, fill_opacity=0.15, stroke_width=2).shift(LEFT * 4.2 + DOWN * 0.3)
        c1_title = Text("1. Forward Pass", font_size=22, color=BLUE_C, weight="BOLD").next_to(c1_box.get_top(), DOWN, buff=0.35)
        c1_eq = MathTex(r"\hat{\mathbf{y}} = \sigma(\mathbf{W}\mathbf{x} + \mathbf{b})", font_size=24, color=WHITE).next_to(c1_title, DOWN, buff=0.4)
        c1_desc = Text("Propagates inputs through\nlayers of weights to\ngenerate predictions.", font_size=17, color=GREY_B, line_spacing=1.2).next_to(c1_eq, DOWN, buff=0.4)
        card1 = VGroup(c1_box, c1_title, c1_eq, c1_desc)

        # Card 2: Loss Function
        c2_box = RoundedRectangle(corner_radius=0.12, width=3.8, height=4.2, color=RED_C, fill_opacity=0.15, stroke_width=2).shift(DOWN * 0.3)
        c2_title = Text("2. Loss Evaluation", font_size=22, color=RED_C, weight="BOLD").next_to(c2_box.get_top(), DOWN, buff=0.35)
        c2_eq = MathTex(r"\mathcal{L} = \frac{1}{2}\|\hat{\mathbf{y}} - \mathbf{y}\|^2", font_size=24, color=WHITE).next_to(c2_title, DOWN, buff=0.4)
        c2_desc = Text("Measures the exact\npenalty for mistake against\nground-truth targets.", font_size=17, color=GREY_B, line_spacing=1.2).next_to(c2_eq, DOWN, buff=0.4)
        card2 = VGroup(c2_box, c2_title, c2_eq, c2_desc)

        # Card 3: Optimizer
        c3_box = RoundedRectangle(corner_radius=0.12, width=3.8, height=4.2, color=GREEN_C, fill_opacity=0.15, stroke_width=2).shift(RIGHT * 4.2 + DOWN * 0.3)
        c3_title = Text("3. Parameter Update", font_size=22, color=GREEN_C, weight="BOLD").next_to(c3_box.get_top(), DOWN, buff=0.35)
        c3_eq = MathTex(r"\mathbf{W} \leftarrow \mathbf{W} - \eta \nabla_{\mathbf{W}}\mathcal{L}", font_size=24, color=WHITE).next_to(c3_title, DOWN, buff=0.4)
        c3_desc = Text("Updates weights in the\nopposite direction of\nthe loss gradient.", font_size=17, color=GREY_B, line_spacing=1.2).next_to(c3_eq, DOWN, buff=0.4)
        card3 = VGroup(c3_box, c3_title, c3_eq, c3_desc)

        self.slide1_content = VGroup(card1, card2, card3)

        narration_text = (
            "In deep learning, neural networks act as universal function approximators. Today we will uncover how they learn. "
            "<bookmark mark='p1'/> First, signals propagate forward to generate predictions. "
            "<bookmark mark='p2'/> Next, a loss function computes the exact penalty for mistakes. "
            "<bookmark mark='p3'/> Finally, the optimizer updates internal weights to minimize future error."
        )

        with self.voiceover(text=narration_text):
            self.wait_until_bookmark("p1")
            self.play(FadeIn(card1, shift=UP * 0.3), Write(c1_eq), run_time=0.8)

            self.wait_until_bookmark("p2")
            self.play(FadeIn(card2, shift=UP * 0.3), Write(c2_eq), run_time=0.8)

            self.wait_until_bookmark("p3")
            self.play(FadeIn(card3, shift=UP * 0.3), Write(c3_eq), run_time=0.8)

        self.wait(0.5)

    # -------------------------------------------------------------------------
    # 3. Slide 2: Optimization Landscape (Smooth Morphing & Dynamic Parabola)
    # -------------------------------------------------------------------------
    def play_slide_2_optimization_landscape(self):
        # Morph Chrome without blackout!
        self.morph_chrome_and_exit("02", "Optimization Landscape - Gradient Descent", "CALCULUS", self.slide1_content)

        # Coordinate Axes
        axes = Axes(
            x_range=[-1.0, 3.5, 1.0],
            y_range=[0, 4.5, 1.0],
            x_length=6.0,
            y_length=4.0,
            axis_config={"color": GREY_C, "stroke_width": 2},
        ).shift(LEFT * 3.0 + DOWN * 0.4)

        x_lbl = Text("Weight (w)", font_size=16, color=GREY_A).next_to(axes.x_axis, DOWN, buff=0.2)
        y_lbl = Text("Loss L(w)", font_size=16, color=GREY_A).next_to(axes.y_axis, UP, buff=0.2)
        axes_group = VGroup(axes, x_lbl, y_lbl)

        def loss_fn(w):
            return (w - 1.2) ** 2 + 0.4

        parabola = axes.plot(loss_fn, x_range=[-0.6, 3.0], color=TEAL_C, stroke_width=3.5)
        curve_label = MathTex(r"\mathcal{L}(w) = (w - w^*)^2 + \mathcal{L}_{\min}", font_size=22, color=TEAL_C).next_to(axes, UP, buff=0.2).shift(RIGHT * 0.5)

        # Starting Point
        w0 = 2.6
        p0 = axes.c2p(w0, loss_fn(w0))
        dot = Dot(p0, radius=0.12, color=RED)
        dot_label = MathTex(r"w_0 \text{ (Initial)}", font_size=20, color=RED).next_to(dot, RIGHT, buff=0.2)

        # Tangent Slope
        tangent = Line(
            axes.c2p(w0 - 0.4, loss_fn(w0) - 2.8 * 0.4),
            axes.c2p(w0 + 0.4, loss_fn(w0) + 2.8 * 0.4),
            color=YELLOW,
            stroke_width=2.5,
        )
        grad_label = MathTex(r"\nabla \mathcal{L} > 0 \text{ (Steepest Ascent)}", font_size=20, color=YELLOW).next_to(tangent, UP + RIGHT, buff=0.1)

        # Right Panel
        info_box = RoundedRectangle(corner_radius=0.12, width=4.8, height=4.2, color=BLUE_E, fill_opacity=0.12, stroke_width=1.8).shift(RIGHT * 3.6 + DOWN * 0.4)
        info_title = Text("Gradient Descent Rule", font_size=22, color=BLUE_C, weight="BOLD").next_to(info_box.get_top(), DOWN, buff=0.35)
        info_rule = MathTex(r"w_{t+1} = w_t - \eta \frac{\partial \mathcal{L}}{\partial w}", font_size=26, color=WHITE).next_to(info_title, DOWN, buff=0.35)
        
        info_bullet1 = Text("• Loss defines the mountain height.", font_size=18, color=GREY_B).next_to(info_rule, DOWN, buff=0.35, aligned_edge=LEFT).shift(LEFT * 0.3)
        info_bullet2 = Text("• Gradient points steepest uphill.", font_size=18, color=GREY_B).next_to(info_bullet1, DOWN, buff=0.25, aligned_edge=LEFT)
        info_bullet3 = Text("• Step opposite to reach the valley.", font_size=18, color=GREY_B).next_to(info_bullet2, DOWN, buff=0.25, aligned_edge=LEFT)
        info_group = VGroup(info_box, info_title, info_rule, info_bullet1, info_bullet2, info_bullet3)

        narration_text = (
            "Imagine standing on a foggy hillside. That hill is our loss surface. <bookmark mark='p1'/> "
            "The loss represents the height of the mountain we must descend. <bookmark mark='p2'/> "
            "The gradient tells us the steepest uphill slope under our feet. <bookmark mark='p3'/> "
            "By taking controlled steps in the exact opposite direction, we reach the optimal valley."
        )

        with self.voiceover(text=narration_text):
            # Dynamic curve tracing
            self.play(Create(axes_group), Create(parabola, run_time=1.3), Write(curve_label), run_time=1.3)

            self.wait_until_bookmark("p1")
            self.play(FadeIn(dot, scale=1.3), Write(dot_label), FadeIn(info_group, shift=LEFT * 0.3), run_time=0.9)

            self.wait_until_bookmark("p2")
            self.play(Create(tangent), Write(grad_label), run_time=0.8)

            self.wait_until_bookmark("p3")
            w1 = 1.8
            p1 = axes.c2p(w1, loss_fn(w1))
            arrow1 = Arrow(p0, p1, color=ORANGE, buff=0.08, stroke_width=3, max_tip_length_to_length_ratio=0.25)
            self.play(Create(arrow1), dot.animate.move_to(p1), FadeOut(dot_label), FadeOut(tangent), FadeOut(grad_label), run_time=0.8)

            w_opt = 1.2
            p_opt = axes.c2p(w_opt, loss_fn(w_opt))
            arrow2 = Arrow(p1, p_opt, color=GREEN, buff=0.08, stroke_width=3, max_tip_length_to_length_ratio=0.25)
            min_label = MathTex(r"w^* \text{ (Global Minimum)}", font_size=20, color=GREEN_C).next_to(axes.c2p(w_opt, loss_fn(w_opt)), DOWN, buff=0.35)
            self.play(Create(arrow2), dot.animate.move_to(p_opt), Write(min_label), run_time=0.8)

        self.wait(0.5)
        self.slide2_content = VGroup(axes_group, parabola, curve_label, dot, arrow1, arrow2, min_label, info_group)

    # -------------------------------------------------------------------------
    # 4. Slide 3: Credit Assignment (Particle Flow via MoveAlongPath)
    # -------------------------------------------------------------------------
    def play_slide_3_credit_assignment(self):
        # Morph Chrome without blackout!
        self.morph_chrome_and_exit("03", "Credit Assignment - The Chain Rule", "ARCHITECTURE", self.slide2_content)

        # Neural Network Graph
        x1 = Circle(radius=0.32, color=BLUE, fill_opacity=0.3).shift(LEFT * 5.0 + UP * 0.9)
        x2 = Circle(radius=0.32, color=BLUE, fill_opacity=0.3).shift(LEFT * 5.0 + DOWN * 0.9)
        x1_lbl = MathTex("x_1", font_size=22, color=WHITE).move_to(x1)
        x2_lbl = MathTex("x_2", font_size=22, color=WHITE).move_to(x2)
        in_tag = Text("Inputs", font_size=16, color=BLUE_C).next_to(x1, UP, buff=0.4)

        h1 = Circle(radius=0.35, color=TEAL, fill_opacity=0.3).shift(LEFT * 2.5 + UP * 0.9)
        h2 = Circle(radius=0.35, color=TEAL, fill_opacity=0.3).shift(LEFT * 2.5 + DOWN * 0.9)
        h1_lbl = MathTex("h_1", font_size=22, color=WHITE).move_to(h1)
        h2_lbl = MathTex("h_2", font_size=22, color=WHITE).move_to(h2)
        hid_tag = Text("Hidden Layer", font_size=16, color=TEAL_C).next_to(h1, UP, buff=0.4)

        y_hat = Circle(radius=0.38, color=PURPLE, fill_opacity=0.3).shift(ORIGIN + RIGHT * 0.0)
        y_lbl = MathTex(r"\hat{y}", font_size=24, color=WHITE).move_to(y_hat)
        out_tag = Text("Output", font_size=16, color=PURPLE_C).next_to(y_hat, UP, buff=0.4)

        loss_box = RoundedRectangle(corner_radius=0.08, width=0.9, height=0.7, color=RED, fill_opacity=0.3).shift(RIGHT * 2.0)
        loss_lbl = MathTex(r"\mathcal{L}", font_size=24, color=WHITE).move_to(loss_box)
        loss_tag = Text("Loss", font_size=16, color=RED_C).next_to(loss_box, UP, buff=0.4)

        lines_ih = [
            Line(x1.get_right(), h1.get_left(), color=DARK_GRAY, stroke_width=2),
            Line(x1.get_right(), h2.get_left(), color=DARK_GRAY, stroke_width=2),
            Line(x2.get_right(), h1.get_left(), color=DARK_GRAY, stroke_width=2),
            Line(x2.get_right(), h2.get_left(), color=DARK_GRAY, stroke_width=2),
        ]
        lines_ho = [
            Line(h1.get_right(), y_hat.get_left(), color=DARK_GRAY, stroke_width=2),
            Line(h2.get_right(), y_hat.get_left(), color=DARK_GRAY, stroke_width=2),
        ]
        line_ol = Line(y_hat.get_right(), loss_box.get_left(), color=DARK_GRAY, stroke_width=2)

        network_group = VGroup(
            *lines_ih, *lines_ho, line_ol,
            x1, x2, x1_lbl, x2_lbl, in_tag,
            h1, h2, h1_lbl, h2_lbl, hid_tag,
            y_hat, y_lbl, out_tag,
            loss_box, loss_lbl, loss_tag
        ).shift(DOWN * 0.3)

        chain_card = RoundedRectangle(corner_radius=0.12, width=11.5, height=1.6, color=BLUE_E, fill_opacity=0.15, stroke_width=1.8).shift(DOWN * 2.2)
        chain_title = Text("Multivariable Chain Rule Decomposition:", font_size=18, color=TEAL_C, weight="BOLD").next_to(chain_card.get_top(), DOWN, buff=0.15)
        chain_eq = MathTex(
            r"\frac{\partial \mathcal{L}}{\partial w_1} = "
            r"\underbrace{\frac{\partial \mathcal{L}}{\partial \hat{y}}}_{\text{Loss Gradient}} \;\cdot\; "
            r"\underbrace{\frac{\partial \hat{y}}{\partial h_1}}_{\text{Hidden Weight}} \;\cdot\; "
            r"\underbrace{\frac{\partial h_1}{\partial w_1}}_{\text{Input Activation}}",
            font_size=23,
            color=WHITE,
        ).next_to(chain_title, DOWN, buff=0.15)
        chain_group = VGroup(chain_card, chain_title, chain_eq)

        # Explicit backward directed paths for MoveAlongPath
        path_loss_to_y = Line(loss_box.get_left(), y_hat.get_right())
        path_y_to_h1 = Line(y_hat.get_left(), h1.get_right())
        path_h1_to_x1 = Line(h1.get_left(), x1.get_right())

        narration_text = (
            "How do we know which specific weight caused the mistake? Calculus gives us the answer through the chain rule. <bookmark mark='p1'/> "
            "Because neural networks are compositions of functions, derivatives multiply backwards. <bookmark mark='p2'/> "
            "Each layer passes gradients to the previous layer recursively. <bookmark mark='p3'/> "
            "This allows every single neuron to receive credit proportional to its influence."
        )

        with self.voiceover(text=narration_text):
            self.play(FadeIn(network_group, shift=RIGHT * 0.4), run_time=0.9)

            self.wait_until_bookmark("p1")
            # Forward signal pulse
            fwd_pulse = Dot(x1.get_center(), radius=0.12, color=BLUE_C)
            self.play(MoveAlongPath(fwd_pulse, Line(x1.get_right(), h1.get_left())), run_time=0.5)
            self.play(MoveAlongPath(fwd_pulse, Line(h1.get_right(), y_hat.get_left())), run_time=0.5)
            self.remove(fwd_pulse)
            self.play(FadeIn(chain_card), Write(chain_title), Write(chain_eq), run_time=0.9)

            self.wait_until_bookmark("p2")
            # DYNAMIC BACKWARD PROPAGATION VIA MOVEALONGPATH (ACTIVE PARTICLES)
            back_pulse1 = Dot(loss_box.get_left(), radius=0.14, color=RED)
            back_pulse2 = Dot(y_hat.get_left(), radius=0.14, color=ORANGE)
            back_pulse3 = Dot(h1.get_left(), radius=0.14, color=YELLOW)

            self.play(MoveAlongPath(back_pulse1, path_loss_to_y), Indicate(y_hat, color=RED), run_time=0.6)
            self.remove(back_pulse1)
            self.play(MoveAlongPath(back_pulse2, path_y_to_h1), Indicate(h1, color=ORANGE), run_time=0.6)
            self.remove(back_pulse2)
            self.play(MoveAlongPath(back_pulse3, path_h1_to_x1), Indicate(x1, color=YELLOW), run_time=0.6)
            self.remove(back_pulse3)

            self.wait_until_bookmark("p3")
            # Micro-interaction: Neural sensitivity glow & pulse
            self.play(
                h1.animate.scale(1.15).set_color(GREEN_C),
                x1.animate.scale(1.15).set_color(GREEN_C),
                y_hat.animate.scale(1.15).set_color(GREEN_C),
                run_time=0.7,
            )
            self.play(
                h1.animate.scale(1/1.15),
                x1.animate.scale(1/1.15),
                y_hat.animate.scale(1/1.15),
                run_time=0.5,
            )

        self.wait(0.5)
        self.slide3_content = VGroup(network_group, chain_group)

    # -------------------------------------------------------------------------
    # 5. Slide 4: First-Principles Understanding (Letter-by-Letter Quote)
    # -------------------------------------------------------------------------
    def play_slide_4_feynman_approach(self):
        # Morph Chrome without blackout!
        self.morph_chrome_and_exit("04", "The Feynman Approach", "PEDAGOGY", self.slide3_content)

        # Quote Box
        q_box = RoundedRectangle(corner_radius=0.15, width=11.5, height=2.0, color=BLUE_E, fill_opacity=0.15, stroke_width=2).shift(UP * 1.0)
        quote_mark = Text("“", font_size=50, color=TEAL_C).next_to(q_box.get_top() + LEFT * 5.2, DOWN, buff=0.1)
        quote_text = Text(
            "Study what interests you in the most undisciplined, irreverent\nand original manner possible.",
            font_size=23,
            color=WHITE,
            line_spacing=1.3,
            slant="ITALIC",
        ).move_to(q_box.get_center() + RIGHT * 0.2)
        quote_author = Text("— Richard P. Feynman", font_size=18, color=TEAL_C, weight="BOLD").next_to(q_box.get_bottom() + RIGHT * 4.0, UP, buff=0.2)
        quote_frame = VGroup(q_box, quote_mark, quote_author)

        # 3 Takeaway Cards
        p1_box = RoundedRectangle(corner_radius=0.1, width=3.6, height=2.6, color=TEAL_C, fill_opacity=0.12, stroke_width=1.5).shift(LEFT * 3.9 + DOWN * 1.7)
        p1_num = Text("01", font_size=20, color=TEAL_C, weight="BOLD").next_to(p1_box.get_top(), DOWN, buff=0.25)
        p1_t = Text("First Principles", font_size=18, color=WHITE, weight="BOLD").next_to(p1_num, DOWN, buff=0.15)
        p1_d = Text("Build mathematical\nintuition from scratch\nrather than memorizing.", font_size=15, color=GREY_B, line_spacing=1.2).next_to(p1_t, DOWN, buff=0.2)
        card1 = VGroup(p1_box, p1_num, p1_t, p1_d)

        p2_box = RoundedRectangle(corner_radius=0.1, width=3.6, height=2.6, color=BLUE_C, fill_opacity=0.12, stroke_width=1.5).shift(DOWN * 1.7)
        p2_num = Text("02", font_size=20, color=BLUE_C, weight="BOLD").next_to(p2_box.get_top(), DOWN, buff=0.25)
        p2_t = Text("Deconstruct Layers", font_size=18, color=WHITE, weight="BOLD").next_to(p2_num, DOWN, buff=0.15)
        p2_d = Text("Never mistake complex\nnotation for real\nunderstanding.", font_size=15, color=GREY_B, line_spacing=1.2).next_to(p2_t, DOWN, buff=0.2)
        card2 = VGroup(p2_box, p2_num, p2_t, p2_d)

        p3_box = RoundedRectangle(corner_radius=0.1, width=3.6, height=2.6, color=PURPLE_C, fill_opacity=0.12, stroke_width=1.5).shift(RIGHT * 3.9 + DOWN * 1.7)
        p3_num = Text("03", font_size=20, color=PURPLE_C, weight="BOLD").next_to(p3_box.get_top(), DOWN, buff=0.25)
        p3_t = Text("Transparent AI", font_size=18, color=WHITE, weight="BOLD").next_to(p3_num, DOWN, buff=0.15)
        p3_d = Text("When chain rule is\nclear, deep learning\nbecomes fully lucid.", font_size=15, color=GREY_B, line_spacing=1.2).next_to(p3_t, DOWN, buff=0.2)
        card3 = VGroup(p3_box, p3_num, p3_t, p3_d)

        narration_text = (
            "As the legendary physicist Richard Feynman once reminded us. <bookmark mark='p1'/> "
            "Genuine mastery requires genuine curiosity. <bookmark mark='p2'/> "
            "Study what interests you with an open and irreverent mind. <bookmark mark='p3'/> "
            "Build mental models from ground truth rather than memorizing formulas. "
            "When you understand backpropagation from first principles, modern AI becomes completely transparent."
        )

        with self.voiceover(text=narration_text):
            self.play(FadeIn(quote_frame, shift=DOWN * 0.2), run_time=0.6)
            # Letter-by-letter typing animation for quotation
            self.play(AddTextLetterByLetter(quote_text, run_time=2.2))

            self.wait_until_bookmark("p1")
            self.play(FadeIn(card1, shift=UP * 0.2), Write(p1_t), run_time=0.7)

            self.wait_until_bookmark("p2")
            self.play(FadeIn(card2, shift=UP * 0.2), Write(p2_t), run_time=0.7)

            self.wait_until_bookmark("p3")
            self.play(FadeIn(card3, shift=UP * 0.2), Write(p3_t), run_time=0.7)

        self.wait(0.5)
        self.slide4_content = VGroup(quote_frame, quote_text, card1, card2, card3)

    # -------------------------------------------------------------------------
    # 6. Slide 5: Summary & Next Steps (Term-by-term Matrix Calculus)
    # -------------------------------------------------------------------------
    def play_slide_5_summary_and_next_steps(self):
        # Morph Chrome without blackout!
        self.morph_chrome_and_exit("05", "Summary & Next Steps", "CONCLUSION", self.slide4_content)

        # 3 Pillar Summary Cards
        s1_box = RoundedRectangle(corner_radius=0.12, width=3.7, height=2.4, color=BLUE_E, fill_opacity=0.15, stroke_width=1.8).shift(LEFT * 4.0 + UP * 0.9)
        s1_title = Text("1. Forward Pass", font_size=20, color=BLUE_C, weight="BOLD").next_to(s1_box.get_top(), DOWN, buff=0.25)
        s1_eq = MathTex(r"\hat{\mathbf{y}} = f(\mathbf{W}\mathbf{x} + \mathbf{b})", font_size=22, color=WHITE).next_to(s1_title, DOWN, buff=0.2)
        s1_desc = Text("Maps inputs to predictions.", font_size=15, color=GREY_B).next_to(s1_eq, DOWN, buff=0.2)
        card1 = VGroup(s1_box, s1_title, s1_eq, s1_desc)

        s2_box = RoundedRectangle(corner_radius=0.12, width=3.7, height=2.4, color=RED_C, fill_opacity=0.15, stroke_width=1.8).shift(UP * 0.9)
        s2_title = Text("2. Chain Rule", font_size=20, color=RED_C, weight="BOLD").next_to(s2_box.get_top(), DOWN, buff=0.25)
        s2_eq = MathTex(r"\frac{\partial \mathcal{L}}{\partial \mathbf{W}} = \boldsymbol{\delta} \cdot \mathbf{a}^T", font_size=22, color=WHITE).next_to(s2_title, DOWN, buff=0.2)
        s2_desc = Text("Assigns error credit backwards.", font_size=15, color=GREY_B).next_to(s2_eq, DOWN, buff=0.2)
        card2 = VGroup(s2_box, s2_title, s2_eq, s2_desc)

        s3_box = RoundedRectangle(corner_radius=0.12, width=3.7, height=2.4, color=GREEN_C, fill_opacity=0.15, stroke_width=1.8).shift(RIGHT * 4.0 + UP * 0.9)
        s3_title = Text("3. Gradient Descent", font_size=20, color=GREEN_C, weight="BOLD").next_to(s3_box.get_top(), DOWN, buff=0.25)
        s3_eq = MathTex(r"\mathbf{W} \leftarrow \mathbf{W} - \eta \nabla \mathcal{L}", font_size=22, color=WHITE).next_to(s3_title, DOWN, buff=0.2)
        s3_desc = Text("Steps towards the minimum.", font_size=15, color=GREY_B).next_to(s3_eq, DOWN, buff=0.2)
        card3 = VGroup(s3_box, s3_title, s3_eq, s3_desc)

        top_cards = VGroup(card1, card2, card3)

        # Bottom Announcement Banner
        banner_box = RoundedRectangle(corner_radius=0.15, width=11.7, height=2.0, color=TEAL, fill_opacity=0.18, stroke_width=2.0).shift(DOWN * 1.8)
        next_badge = Text("UPCOMING NEXT SESSION", font_size=15, color=TEAL_C, weight="BOLD").next_to(banner_box.get_top(), DOWN, buff=0.2)
        next_title = Text("Deriving Full Matrix Equations & Pure Python Implementation", font_size=23, color=WHITE, weight="BOLD").next_to(next_badge, DOWN, buff=0.15)
        
        # Sequentially written matrix formula
        next_code = MathTex(
            r"\mathbf{dW} = \frac{1}{m} \mathbf{dZ} \cdot \mathbf{A}^{[l-1]T}, \quad \mathbf{db} = \frac{1}{m} \sum \mathbf{dZ}",
            font_size=22,
            color=YELLOW,
        ).next_to(next_title, DOWN, buff=0.15)

        narration_text = (
            "That concludes our conceptual foundation of backpropagation. <bookmark mark='p1'/> "
            "In our upcoming session, we will derive the exact matrix equations <bookmark mark='p2'/> "
            "and write the backward pass in pure Python."
        )

        with self.voiceover(text=narration_text):
            self.play(FadeIn(top_cards, shift=DOWN * 0.2), Write(s1_eq), Write(s2_eq), Write(s3_eq), run_time=0.9)

            self.wait_until_bookmark("p1")
            self.play(FadeIn(banner_box), Write(next_badge), Write(next_title), run_time=0.8)

            self.wait_until_bookmark("p2")
            # Write matrix calculus sequentially to guide the viewer's eye
            self.play(Write(next_code, run_time=1.3), Indicate(banner_box, color=TEAL_C), run_time=1.3)

        self.wait(1.0)
        # Final graceful exit of entire presentation
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.8)
        self.clear()
        self.wait(0.5)
