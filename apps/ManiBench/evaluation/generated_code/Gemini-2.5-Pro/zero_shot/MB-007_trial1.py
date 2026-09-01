from manim import *

class BayesTheoremBox(Scene):
    def construct(self):
        # --- CONFIGURATION ---
        # Probabilities and Population
        POPULATION = 10000
        PREVALENCE = 0.01  # P(Sick)
        SENSITIVITY = 0.95  # P(+ | Sick) - True Positive Rate
        SPECIFICITY = 0.95  # P(- | Not Sick) - True Negative Rate

        # Derived Probabilities
        FALSE_POSITIVE_RATE = 1 - SPECIFICITY  # P(+ | Not Sick)
        FALSE_NEGATIVE_RATE = 1 - SENSITIVITY  # P(- | Sick)

        # Calculate counts
        num_sick = int(POPULATION * PREVALENCE)
        num_not_sick = int(POPULATION * (1 - PREVALENCE))
        num_tp = int(num_sick * SENSITIVITY)          # True Positives
        num_fn = int(num_sick * FALSE_NEGATIVE_RATE) # False Negatives
        num_fp = int(num_not_sick * FALSE_POSITIVE_RATE) # False Positives
        num_tn = int(num_not_sick * SPECIFICITY)     # True Negatives

        # Colors
        SICK_COLOR = RED_D
        NOT_SICK_COLOR = GREEN_D
        POSITIVE_COLOR = BLUE_B
        NEGATIVE_COLOR = GREY_BROWN
        BOX_STROKE_COLOR = WHITE

        # --- SCENE SETUP ---
        title = Tex("Bayes' Theorem: The Paradox of Rare Diseases").to_edge(UP)
        self.play(Write(title))
        self.wait(1)

        # --- 1. CREATE THE POPULATION BOX ---
        main_box = Rectangle(width=10, height=6, stroke_color=BOX_STROKE_COLOR).shift(DOWN * 0.5)
        pop_label = VGroup(
            Tex(f"Total Population = {POPULATION:,}"),
            Integer(POPULATION).scale(1.5)
        ).arrange(DOWN).next_to(main_box, UP, buff=0.5)
        pop_label[1].set_value(0)

        self.play(Create(main_box), Write(pop_label[0]))
        self.play(ChangeDecimalToValue(pop_label[1], POPULATION), run_time=2)
        self.play(FadeOut(pop_label))

        # --- 2. DIVIDE BY PREVALENCE (SICK vs NOT SICK) ---
        # Create areas proportional to prevalence
        sick_area = Rectangle(
            width=main_box.width * PREVALENCE,
            height=main_box.height,
            fill_color=SICK_COLOR,
            fill_opacity=0.7,
            stroke_width=0
        ).align_to(main_box, LEFT + UP)

        not_sick_area = Rectangle(
            width=main_box.width * (1 - PREVALENCE),
            height=main_box.height,
            fill_color=NOT_SICK_COLOR,
            fill_opacity=0.7,
            stroke_width=0
        ).align_to(main_box, RIGHT + UP)

        v_line = Line(main_box.get_top(), main_box.get_bottom()).move_to(sick_area.get_right())

        sick_label = VGroup(Tex("Sick"), Integer(num_sick)).arrange(DOWN).move_to(sick_area)
        not_sick_label = VGroup(Tex("Not Sick"), Integer(num_not_sick)).arrange(DOWN).move_to(not_sick_area)

        self.play(
            FadeIn(sick_area),
            FadeIn(not_sick_area),
            Create(v_line)
        )
        self.play(
            Write(sick_label),
            Write(not_sick_label)
        )
        self.wait(2)

        # --- 3. DIVIDE BY TEST RESULT (+ vs -) ---
        # Create the four quadrants
        tp_area = Rectangle(
            width=sick_area.width, height=sick_area.height * SENSITIVITY,
            fill_color=SICK_COLOR, fill_opacity=0.8, stroke_width=2, stroke_color=POSITIVE_COLOR
        ).align_to(sick_area, UP)
        fn_area = Rectangle(
            width=sick_area.width, height=sick_area.height * FALSE_NEGATIVE_RATE,
            fill_color=SICK_COLOR, fill_opacity=0.5, stroke_width=2, stroke_color=NEGATIVE_COLOR
        ).align_to(sick_area, DOWN)

        fp_area = Rectangle(
            width=not_sick_area.width, height=not_sick_area.height * FALSE_POSITIVE_RATE,
            fill_color=NOT_SICK_COLOR, fill_opacity=0.8, stroke_width=2, stroke_color=POSITIVE_COLOR
        ).align_to(not_sick_area, UP)
        tn_area = Rectangle(
            width=not_sick_area.width, height=not_sick_area.height * SPECIFICITY,
            fill_color=NOT_SICK_COLOR, fill_opacity=0.5, stroke_width=2, stroke_color=NEGATIVE_COLOR
        ).align_to(not_sick_area, DOWN)

        # Horizontal dividing lines
        h_line_sick = Line(sick_area.get_left(), sick_area.get_right()).move_to(tp_area.get_bottom())
        h_line_not_sick = Line(not_sick_area.get_left(), not_sick_area.get_right()).move_to(fp_area.get_bottom())

        # Labels for test results
        pos_label = Tex("Test +").scale(0.8).next_to(main_box, LEFT, buff=0.5).align_to(fp_area, UP)
        neg_label = Tex("Test $-$").scale(0.8).next_to(main_box, LEFT, buff=0.5).align_to(tn_area, DOWN)

        self.play(
            FadeOut(sick_label, not_sick_label, sick_area, not_sick_area),
            FadeIn(tp_area, fn_area, fp_area, tn_area),
            Create(h_line_sick),
            Create(h_line_not_sick),
            Write(pos_label),
            Write(neg_label)
        )
        self.wait(1)

        # Add counts to each quadrant
        tp_group = VGroup(tp_area, Tex(f"Sick, Test +\\(True Positive)", font_size=24), Integer(num_tp)).arrange(DOWN, buff=0.2).move_to(tp_area)
        fn_group = VGroup(fn_area, Tex(f"Sick, Test $-\\(False Negative)", font_size=24), Integer(num_fn)).arrange(DOWN, buff=0.2).move_to(fn_area)
        fp_group = VGroup(fp_area, Tex(f"Not Sick, Test +\\(False Positive)", font_size=32), Integer(num_fp)).arrange(DOWN, buff=0.3).move_to(fp_area)
        tn_group = VGroup(tn_area, Tex(f"Not Sick, Test $-\\(True Negative)", font_size=32), Integer(num_tn)).arrange(DOWN, buff=0.3).move_to(tn_area)

        self.play(
            Write(tp_group[1:]),
            Write(fn_group[1:]),
            Write(fp_group[1:]),
            Write(tn_group[1:])
        )
        self.wait(3)

        # --- 4. HIGHLIGHT POSITIVE RESULTS ---
        question = Tex("Given a positive test, what is the chance you are sick?").next_to(title, DOWN)
        self.play(Write(question))
        self.wait(1)

        # Fade out negative results
        self.play(
            fn_group.animate.set_opacity(0.2),
            tn_group.animate.set_opacity(0.2),
            neg_label.animate.set_opacity(0.2)
        )

        # Highlight the positive results row
        positive_row_highlight = SurroundingRectangle(
            VGroup(tp_area, fp_area),
            buff=0.1,
            color=YELLOW
        )
        self.play(Create(positive_row_highlight))
        self.wait(2)

        # --- 5. SHOW THE CALCULATION ---
        all_mobjects = VGroup(*self.mobjects)
        self.play(all_mobjects.animate.scale(0.7).to_edge(LEFT, buff=0.5))

        # Formula
        calc_group = VGroup(
            MathTex(r"P(\text{Sick} | +) = \frac{\text{True Positives}}{\text{All Positives}}"),
            MathTex(r"= \frac{\text{True Positives}}{\text{True Positives} + \text{False Positives}}"),
            MathTex(r"= \frac{95}{95 + 495}"),
            MathTex(r"= \frac{95}{590}"),
            MathTex(r"\approx 0.161 = 16.1\%")
        ).arrange(DOWN, align=LEFT).scale(0.9).to_edge(RIGHT, buff=1)

        self.play(Write(calc_group[0]))
        self.wait(1)
        self.play(Write(calc_group[1]))
        self.wait(1)

        # Animate numbers moving to formula
        tp_num_copy = tp_group[2].copy()
        fp_num_copy = fp_group[2].copy()
        self.play(
            tp_num_copy.animate.move_to(calc_group[2][0][2:4]),
            fp_num_copy.animate.move_to(calc_group[2][0][8:11]),
            tp_group[2].copy().animate.move_to(calc_group[2][0][5:7])
        )
        self.play(Transform(calc_group[1], calc_group[2]))
        self.play(FadeOut(tp_num_copy, fp_num_copy))
        self.wait(1)

        self.play(Transform(calc_group[2], calc_group[3]))
        self.wait(1)

        self.play(Transform(calc_group[3], calc_group[4]))
        self.wait(2)

        # --- 6. EXPLAIN THE PARADOX ---
        final_highlight = SurroundingRectangle(calc_group[4], color=YELLOW)
        self.play(Create(final_highlight))

        explanation = VGroup(
            Tex("Even with a 95% accurate test..."),
            Tex("...a positive result only means a ~16% chance of being sick."),
            Tex("Why? The disease is so rare that the vast majority of", " positive tests", " are ", "false positives", "."),
        ).arrange(DOWN, align=LEFT).scale(0.7).next_to(calc_group, DOWN, buff=0.5)
        
        explanation[2][1].set_color(POSITIVE_COLOR)
        explanation[2][3].set_color(YELLOW)

        self.play(Write(explanation[0]))
        self.wait(1)
        self.play(Write(explanation[1]))
        self.wait(2)
        self.play(Write(explanation[2]))
        self.wait(5)