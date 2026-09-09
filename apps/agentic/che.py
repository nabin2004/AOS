from manim import *

class PedagogicalScene(Scene):
    def construct(self):
        self.camera.background_color = "#0E1117"

        # --- 1. Allocate Mobjects (Prop Master) ---
        title = Title("Limit Definition of a Derivative")  # Introduces the topic of the scene.
        axes = Axes(x_range=[-1, 4, 1], y_range=[-1, 5, 1], x_length=6.0, y_length=4.0)  # Provides a coordinate system for plotting the function.
        func_graph = FunctionGraph(lambda x: x**2, color=YELLOW)  # Represents the function f(x) for which the derivative is being explained.
        h_tracker = ValueTracker(2.0)  # Drives the animation of 'h' approaching zero, making the secant line dynamic.
        deriv_formula = MathTex(r"f'(x) = \lim_{h \to 0} \frac{f(x+h)-f(x)}{h}")  # Displays the mathematical limit definition of the derivative.
        secant_line = Line(color=RED)  # Represents the secant line connecting two points on the function curve.
        dot_x = Dot(radius=0.08, color=BLUE)  # Marks the fixed point (x, f(x)) on the function curve.     
        dot_x_plus_h = Dot(radius=0.08, color=GREEN)  # Marks the moving point (x+h, f(x+h)) on the function curve.
        label_x_fx = MathTex(r"(x, f(x))", color=BLUE)  # Label for the fixed point (x, f(x)).
        label_x_plus_h_fx_plus_h = MathTex(r"(x+h, f(x+h))", color=GREEN)  # Label for the moving point (x+h, f(x+h)).
        label_h = MathTex(r"h", color=ORANGE)  # Label to indicate the distance 'h' between x and x+h.     

        # --- 1b. VGroups (auto-generated from group_name) ---
        labels = VGroup(label_x_fx, label_x_plus_h_fx_plus_h, label_h)

        # --- 2. Deterministic Positioning (Layout Critic) ---
        title.scale_to_fit_width(5.5)
        title.move_to([0.0, 2.95, 0])
        axes.scale_to_fit_width(5.5)
        axes.to_edge(RIGHT, buff=0.6)
        func_graph.move_to([2.0, -1.65, 0])
        deriv_formula.scale_to_fit_width(5.5)
        deriv_formula.move_to([-3.56, 0.0, 0])
        secant_line.move_to([0.0, -3.35, 0])
        dot_x.move_to([0.0, -3.32, 0])
        dot_x_plus_h.move_to([0.0, -3.32, 0])
        label_x_fx.next_to(deriv_formula, DOWN, buff=0.6, aligned_edge=LEFT)
        label_x_plus_h_fx_plus_h.next_to(label_x_fx, DOWN, buff=0.6, aligned_edge=LEFT)
        label_h.move_to([-5.59, -3.0, 0])

        # --- 3. Choreography (Choreographer) ---
        self.play(Write(title), run_time=1.0)  # Bookmark: <bookmark mark='start_title'/>
        self.wait(1.0)
        self.play(FadeOut(title))  # Cleanup
        self.play(Create(axes), run_time=1.0)  # Bookmark: <bookmark mark='show_axes'/>
        self.wait(0.5)
        self.play(Create(func_graph), run_time=1.0)  # Bookmark: <bookmark mark='show_func_graph'/>        
        self.wait(0.5)
        self.play(GrowFromCenter(dot_x), run_time=1.0)  # Bookmark: <bookmark mark='show_dot_x'/>
        self.wait(0.3)
        self.play(Write(label_x_fx), run_time=1.0)  # Bookmark: <bookmark mark='show_label_x_fx'/>
        self.wait(0.8)
        self.play(GrowFromCenter(dot_x_plus_h), run_time=1.0)  # Bookmark: <bookmark mark='show_dot_x_plus_h'/>
        self.wait(0.3)
        self.play(Write(label_x_plus_h_fx_plus_h), run_time=1.0)  # Bookmark: <bookmark mark='show_label_x_plus_h_fx_plus_h'/>
        self.wait(0.8)
        self.play(Write(label_h), run_time=1.0)  # Bookmark: <bookmark mark='show_label_h'/>
        self.wait(0.8)
        self.play(Create(secant_line), run_time=1.0)  # Bookmark: <bookmark mark='show_secant_line'/>      
        self.wait(0.8)
        self.play(Indicate(label_h), run_time=1.5, rate_func=there_and_back)  # Bookmark: <bookmark mark='indicate_h'/>
        self.wait(0.5)
        self.play(Indicate(secant_line), run_time=1.5, rate_func=there_and_back)  # Bookmark: <bookmark mark='indicate_secant'/>
        self.wait(1.5)
        self.play(FadeOut(dot_x), FadeOut(dot_x_plus_h), FadeOut(secant_line), FadeOut(label_x_fx), FadeOut(label_x_plus_h_fx_plus_h), FadeOut(label_h))  # Cleanup
        self.play(Write(deriv_formula), run_time=1.0)  # Bookmark: <bookmark mark='show_formula'/>
        self.wait(1.5)
        self.play(Indicate(deriv_formula), run_time=1.0, rate_func=there_and_back)  # Bookmark: <bookmark mark='highlight_formula'/>
        self.wait(1.0)
        self.wait(1)


from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService
import numpy as np

class AOSTrajectoryScene29(VoiceoverScene):
    def construct(self):
        self.set_speech_service(AOSSpeechService(voice="alba", cache_dir="voiceover_cache"))

        # Show the hierarchical feature extraction: low-level (characters) → mid-level (morphology) → high-level (semantics).
        title = Title("Show the hierarchical feature extraction")
        ax = Axes(x_range=[-3, 3, 1], y_range=[-1, 5, 1], x_length=6, y_length=4)
        curve = ax.plot(lambda x: 1 / (1 + np.exp(-x)), color=BLUE)
        label = MathTex(r'\sigma(x) = \frac{1}{1 + e^{-x}}').to_corner(UR)
        dot = Dot(ax.c2p(0, 0.5), color=RED)

        with self.voiceover(
            text="We begin by setting up our coordinate system <bookmark mark='show_curve'/> and plotting the sigmoid activation function, which is defined as sigma of x equals one over one plus e to the negative x. <bookmark mark='show_dot'/> We also place a red dot at the center of the curve."
        ) as tracker:
            self.play(Write(title), Create(ax))
            self.wait_until_bookmark("show_curve")
            self.play(Create(curve), Write(label))
            self.wait_until_bookmark("show_dot")
            self.play(FadeIn(dot))

        with self.voiceover(
            text="Now, let us observe how the dot moves along the curve as the input value increases towards two."
        ) as tracker:
            self.play(dot.animate.move_to(ax.c2p(2, 1 / (1 + np.exp(-2)))), run_time=tracker.duration)

        self.wait(1)


from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService
import numpy as np

class AOSTrajectoryScene293(VoiceoverScene):
    def construct(self):
        self.set_speech_service(AOSSpeechService(voice="alba", cache_dir="voiceover_cache"))

        # Visualize the effective rank of activations, showing how many dimensions are actually used by the layer.
        title = Title("Visualize the effective rank of activati")
        ax = Axes(x_range=[-3, 3, 1], y_range=[-1, 5, 1], x_length=6, y_length=4)
        curve = ax.plot(lambda x: 1 / (1 + np.exp(-x)), color=BLUE)
        label = MathTex(r'\sigma(x) = \frac{1}{1 + e^{-x}}').to_corner(UR)
        dot = Dot(ax.c2p(0, 0.5), color=RED)

        with self.voiceover(
            text="We begin by setting up our coordinate axes to visualize the activation function. "
            "<bookmark mark='show_curve'/> Here, we plot the sigmoid function, which maps any real-valued number to a value between zero and one. "
            "<bookmark mark='show_label'/> The mathematical formula is sigma of x equals one divided by the quantity, one plus e to the negative x. "
            "<bookmark mark='show_dot'/> We also place a red dot at the center, where the input is zero and the output is zero point five."
        ) as tracker:
            self.play(Write(title), Create(ax))
            self.wait_until_bookmark("show_curve")
            self.play(Create(curve))
            self.wait_until_bookmark("show_label")
            self.play(Write(label))
            self.wait_until_bookmark("show_dot")
            self.play(FadeIn(dot))

        with self.voiceover(
            text="Now, let us observe how the activation value changes as we increase the input. "
            "<bookmark mark='move_dot'/> As the input moves to two, the sigmoid activation approaches one."
        ) as tracker:
            self.wait_until_bookmark("move_dot")
            self.play(dot.animate.move_to(ax.c2p(2, 1 / (1 + np.exp(-2)))), run_time=2)

        self.wait(1)


from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService
import numpy as np

class AOSTrajectoryScene201(VoiceoverScene):
    def construct(self):
        self.set_speech_service(AOSSpeechService(voice="alba", cache_dir="voiceover_cache"))

        # Animate the Tanh activation function curve mapping input logits (-inf, inf) to outputs (-1, 1), showing saturation zones in red.
        title = Title("Animate the Tanh activation function cur")
        ax = Axes(x_range=[-3, 3, 1], y_range=[-1, 5, 1], x_length=6, y_length=4)
        curve = ax.plot(lambda x: 1 / (1 + np.exp(-x)), color=BLUE)
        label = MathTex(r'\sigma(x) = \frac{1}{1 + e^{-x}}').to_corner(UR)
        dot = Dot(ax.c2p(0, 0.5), color=RED)

        with self.voiceover(
            text="Let us visualize the sigmoid activation function, which maps input values to a range between zero and one. "
            "<bookmark mark='show_elements'/> Here, we plot the curve defined by sigma of x equals one divided by one plus e to the power of negative x. "
            "<bookmark mark='move_dot'/> Watch how the red dot moves along the curve as the input increases, showing how the output approaches one."
        ) as tracker:
            self.wait_until_bookmark("show_elements")
            self.play(Write(title), Create(ax), Create(curve), Write(label), FadeIn(dot))
            self.wait_until_bookmark("move_dot")
            self.play(dot.animate.move_to(ax.c2p(2, 1 / (1 + np.exp(-2)))), run_time=2)

        self.wait(1)



from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService
import numpy as np 


class AOSTrajectoryScene239(VoiceoverScene):

    def construct(self):

        self.set_speech_service(AOSSpeechService(voice="alba", cache_dir="voiceover_cache"))

        title = Title("Animate the formula for NLL loss step-by")
        ax = Axes(x_range=[-3, 3, 1], y_range=[-1, 5, 1], x_length=6, y_length=4)
        curve = ax.plot(lambda x: 1 / (1 + np.exp(-x)), color=BLUE)
        label = MathTex(r'\sigma(x) = \frac{1}{1 + e^{-x}}').to_corner(UR)
        dot = Dot(ax.c2p(0, 0.5), color=RED)

        with self.voiceover(
            text="We begin by setting up our coordinate system <bookmark mark='show_elements'/> and plotting the sigmoid activation function, defined as sigma of x equals one divided by, one plus e to the power of negative x. <bookmark mark='move_dot'/> Let's observe how a point moves along this curve as the input value increases."
        ) as tracker:
            self.play(Write(title))
            self.wait_until_bookmark("show_elements")
            self.play(Create(ax), Create(curve), Write(label), FadeIn(dot))
            self.wait_until_bookmark("move_dot")
            self.play(dot.animate.move_to(ax.c2p(2, 1 / (1 + np.exp(-2)))), run_time=2)

        self.wait(1)


from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService
import numpy as np

class GatedActivationsScene(VoiceoverScene):
    def construct(self):
        self.set_speech_service(
            AOSSpeechService(voice="alba", cache_dir="voiceover_cache")
        )

        # ===== 1. TITLE =====
        title = Text("Gated Activations in Neural Networks", font_size=40)
        subtitle = Text("Tanh magnitude × Sigmoid gate", font_size=24, color=GRAY)
        title_group = VGroup(title, subtitle).arrange(DOWN, buff=0.3)

        with self.voiceover(text="Gated activations combine a candidate value with a sigmoid gate. The tanh activation provides the magnitude, while the sigmoid controls how much of that information passes through.") as tracker:
            self.play(Write(title_group), run_time=tracker.duration)

        self.wait(1)
        self.play(FadeOut(title_group))

        # ===== 2. ELEMENT-WISE GATED ACTIVATION =====
        section_label = Text("Element-wise gated activation", font_size=30).to_edge(UP, buff=0.5)

        tanh_text = MathTex(r"\tanh(z)", font_size=38, color=BLUE)
        multiply = MathTex(r"\odot", font_size=42)
        sigmoid_text = MathTex(r"\sigma(z)", font_size=38, color=YELLOW)
        equals = MathTex(r"=", font_size=38)
        gated_text = MathTex(r"\tanh(z)\odot\sigma(z)", font_size=38, color=GREEN)

        formula = VGroup(
            tanh_text,
            multiply,
            sigmoid_text,
            equals,
            gated_text
        ).arrange(RIGHT, buff=0.25).move_to(UP * 1.5)

        tanh_label = Text("magnitude", font_size=20, color=BLUE).next_to(tanh_text, DOWN, buff=0.2)
        gate_label = Text("gate strength", font_size=20, color=YELLOW).next_to(sigmoid_text, DOWN, buff=0.2)
        output_label = Text("information passed", font_size=20, color=GREEN).next_to(gated_text, DOWN, buff=0.2)

        with self.voiceover(text="For each neuron, tanh produces the magnitude of the candidate activation. The sigmoid produces a gate between zero and one. Their element-wise product determines how much information is passed.") as tracker:
            self.play(Write(section_label), run_time=0.5)
            self.play(Write(tanh_text), Write(multiply), Write(sigmoid_text), run_time=tracker.duration * 0.35)
            self.play(Write(equals), Write(gated_text), run_time=tracker.duration * 0.25)
            self.play(Write(tanh_label), Write(gate_label), Write(output_label), run_time=tracker.duration * 0.25)

        self.wait(0.5)
        self.play(
            FadeOut(section_label),
            FadeOut(formula),
            FadeOut(tanh_label),
            FadeOut(gate_label),
            FadeOut(output_label)
        )

        # ===== 3. PER-NEURON BAR GRAPHS =====
        section_label = Text("Per-neuron activations", font_size=30).to_edge(UP, buff=0.5)

        neuron_labels = ["N1", "N2", "N3", "N4", "N5", "N6"]
        tanh_values = np.array([0.9, -0.6, 0.4, -0.8, 0.7, 0.3])
        gate_values = np.array([0.9, 0.2, 0.75, 0.35, 0.55, 0.8])
        gated_values = tanh_values * gate_values

        axes = Axes(
            x_range=[-0.5, 5.5, 1],
            y_range=[-1.0, 1.0, 0.5],
            x_length=9,
            y_length=4.5,
            axis_config={"include_tip": False},
        ).shift(DOWN * 0.3)

        x_labels = VGroup(*[
            Text(label, font_size=18).next_to(
                axes.c2p(i, 0), DOWN, buff=0.15
            )
            for i, label in enumerate(neuron_labels)
        ])

        tanh_bars = VGroup()
        gate_overlays = VGroup()
        gated_bars = VGroup()

        for i, (tanh_value, gate_value, gated_value) in enumerate(
            zip(tanh_values, gate_values, gated_values)
        ):
            x = axes.c2p(i, 0)
            tanh_top = axes.c2p(i, tanh_value)
            gated_top = axes.c2p(i, gated_value)

            tanh_bar = Rectangle(
                width=0.55,
                height=max(abs(tanh_top[1] - x[1]), 0.05),
                fill_color=BLUE,
                fill_opacity=0.45,
                stroke_color=BLUE,
            )

            tanh_bar.move_to(
                np.array([x[0], (x[1] + tanh_top[1]) / 2, 0])
            )

            gate_height = abs(tanh_top[1] - x[1]) * gate_value
            gate_overlay = Rectangle(
                width=0.55,
                height=max(gate_height, 0.05),
                fill_color=YELLOW,
                fill_opacity=0.65,
                stroke_color=YELLOW,
            )

            gate_overlay.move_to(
                np.array([
                    x[0],
                    x[1] + np.sign(tanh_value) * gate_height / 2,
                    0
                ])
            )

            gated_bar = Rectangle(
                width=0.55,
                height=max(abs(gated_top[1] - x[1]), 0.05),
                fill_color=GREEN,
                fill_opacity=0.75,
                stroke_color=GREEN,
            )

            gated_bar.move_to(
                np.array([x[0], (x[1] + gated_top[1]) / 2, 0])
            )

            tanh_bars.add(tanh_bar)
            gate_overlays.add(gate_overlay)
            gated_bars.add(gated_bar)

        legend = VGroup(
            VGroup(
                Square(side_length=0.18, fill_color=BLUE, fill_opacity=0.45, stroke_color=BLUE),
                Text("Tanh magnitude", font_size=18)
            ).arrange(RIGHT, buff=0.12),
            VGroup(
                Square(side_length=0.18, fill_color=YELLOW, fill_opacity=0.65, stroke_color=YELLOW),
                Text("Sigmoid gate", font_size=18)
            ).arrange(RIGHT, buff=0.12),
            VGroup(
                Square(side_length=0.18, fill_color=GREEN, fill_opacity=0.75, stroke_color=GREEN),
                Text("Gated output", font_size=18)
            ).arrange(RIGHT, buff=0.12),
        ).arrange(RIGHT, buff=0.5).to_edge(DOWN, buff=0.35)

        with self.voiceover(text="Each bar represents one neuron. Blue shows the tanh magnitude, yellow shows the sigmoid gate strength, and green shows the resulting gated activation after the element-wise product.") as tracker:
            self.play(Write(section_label), run_time=0.5)
            self.play(Create(axes), Write(x_labels), run_time=tracker.duration * 0.2)
            self.play(Create(tanh_bars), run_time=tracker.duration * 0.3)
            self.play(Create(gate_overlays), run_time=tracker.duration * 0.2)
            self.play(Create(gated_bars), run_time=tracker.duration * 0.2)
            self.play(Write(legend), run_time=tracker.duration * 0.1)

        self.wait(0.5)

        self.play(
            FadeOut(section_label),
            FadeOut(axes),
            FadeOut(x_labels),
            FadeOut(tanh_bars),
            FadeOut(gate_overlays),
            FadeOut(gated_bars),
            FadeOut(legend)
        )

        # ===== 4. GATE MODULATES INFORMATION FLOW =====
        section_label = Text("The gate modulates information flow", font_size=30).to_edge(UP, buff=0.5)

        source = Circle(radius=0.35, color=BLUE)
        source_label = Text("Tanh", font_size=20, color=BLUE).next_to(source, DOWN, buff=0.2)

        gate = Rectangle(
            width=1.2,
            height=1.2,
            fill_color=YELLOW,
            fill_opacity=0.25,
            stroke_color=YELLOW
        ).shift(ORIGIN)

        gate_value = DecimalNumber(0.2, num_decimal_places=2, font_size=28, color=YELLOW)
        gate_value.add_updater(
            lambda m: m.set_value(float(gate_value.get_value()))
        )
        gate_value.move_to(gate.get_center())

        output = Circle(radius=0.35, color=GREEN)
        output_label = Text("Output", font_size=20, color=GREEN).next_to(output, DOWN, buff=0.2)

        source.shift(LEFT * 4)
        source_label.shift(LEFT * 4)

        output.shift(RIGHT * 4)
        output_label.shift(RIGHT * 4)

        arrow_in = Arrow(source.get_right(), gate.get_left(), buff=0.2, color=WHITE)
        arrow_out = Arrow(gate.get_right(), output.get_left(), buff=0.2, color=WHITE)

        with self.voiceover(text="A strong gate allows more of the tanh activation to pass. A weak gate suppresses the activation. The gate therefore controls information flow on a neuron by neuron basis.") as tracker:
            self.play(Write(section_label), run_time=0.5)
            self.play(Create(source), Write(source_label), Create(gate), Write(gate_value), run_time=tracker.duration * 0.25)
            self.play(Create(arrow_in), Create(arrow_out), Create(output), Write(output_label), run_time=tracker.duration * 0.25)
            self.play(
                gate_value.animate.set_value(0.9),
                gate.animate.set_fill(opacity=0.8),
                run_time=tracker.duration * 0.25
            )
            self.play(
                gate_value.animate.set_value(0.2),
                gate.animate.set_fill(opacity=0.25),
                run_time=tracker.duration * 0.25
            )

        self.wait(0.5)
        self.play(
            FadeOut(section_label),
            FadeOut(source),
            FadeOut(source_label),
            FadeOut(gate),
            FadeOut(gate_value),
            FadeOut(output),
            FadeOut(output_label),
            FadeOut(arrow_in),
            FadeOut(arrow_out)
        )

        # ===== 5. TRAINING STEPS =====
        section_label = Text("Training changes the gate", font_size=30).to_edge(UP, buff=0.5)

        axes = Axes(
            x_range=[0, 6, 1],
            y_range=[0, 1, 0.2],
            x_length=9,
            y_length=4.5,
            axis_config={"include_tip": False},
        ).shift(DOWN * 0.2)

        x_axis_label = Text("Training step", font_size=20).next_to(axes.x_axis, DOWN, buff=0.3)
        y_axis_label = Text("Gate strength", font_size=20).next_to(axes.y_axis, LEFT, buff=0.3).rotate(PI / 2)

        steps = np.arange(0, 7)
        gate_history = [0.2, 0.32, 0.45, 0.58, 0.7, 0.8, 0.88]

        graph = axes.plot_line_graph(
            steps,
            gate_history,
            line_color=YELLOW,
            vertex_dot_radius=0.08,
            add_vertex_dots=True
        )

        step_text = Text("Step 0", font_size=24).to_edge(DOWN, buff=0.5)
        current_gate = DecimalNumber(0.2, num_decimal_places=2, font_size=28, color=YELLOW)
        current_gate.add_updater(lambda m: m.next_to(step_text, RIGHT, buff=0.3))

        gradient_text = MathTex(r"\frac{\partial L}{\partial g}", font_size=32, color=RED)
        gradient_text.next_to(current_gate, RIGHT, buff=0.5)

        with self.voiceover(text="During training, gradients update the parameters that control the gate. As the model learns, the gate can become stronger or weaker depending on whether passing more information improves the loss.") as tracker:
            self.play(Write(section_label), run_time=0.5)
            self.play(Create(axes), Write(x_axis_label), Write(y_axis_label), run_time=tracker.duration * 0.2)
            self.play(Create(graph), run_time=tracker.duration * 0.4)

            for i, value in enumerate(gate_history):
                self.play(
                    step_text.animate.become(Text(f"Step {i}", font_size=24).to_edge(DOWN, buff=0.5)),
                    current_gate.animate.set_value(value),
                    run_time=tracker.duration * 0.4 / len(gate_history)
                )

        self.wait(0.5)
        self.play(
            FadeOut(section_label),
            FadeOut(axes),
            FadeOut(x_axis_label),
            FadeOut(y_axis_label),
            FadeOut(graph),
            FadeOut(step_text),
            FadeOut(current_gate),
            FadeOut(gradient_text)
        )

        # ===== 6. COMPLETE LAYER VIEW =====
        section_label = Text("Across a layer, every neuron gets its own gate", font_size=30).to_edge(UP, buff=0.5)

        neuron_positions = [
            LEFT * 4.5 + UP * 1.2,
            LEFT * 4.5 + DOWN * 0.2,
            LEFT * 4.5 + DOWN * 1.6
        ]

        gate_positions = [
            ORIGIN + UP * 1.2,
            ORIGIN + DOWN * 0.2,
            ORIGIN + DOWN * 1.6
        ]

        output_positions = [
            RIGHT * 4.5 + UP * 1.2,
            RIGHT * 4.5 + DOWN * 0.2,
            RIGHT * 4.5 + DOWN * 1.6
        ]

        input_nodes = VGroup()
        gate_nodes = VGroup()
        output_nodes = VGroup()
        layer_arrows = VGroup()

        for i, (input_pos, gate_pos, output_pos) in enumerate(
            zip(neuron_positions, gate_positions, output_positions)
        ):
            input_node = Circle(radius=0.3, color=BLUE).move_to(input_pos)
            gate_node = Circle(radius=0.35, color=YELLOW).move_to(gate_pos)
            output_node = Circle(radius=0.3, color=GREEN).move_to(output_pos)

            input_label = Text(f"T{i+1}", font_size=16, color=BLUE).move_to(input_node)
            gate_label = Text(f"G{i+1}", font_size=16, color=YELLOW).move_to(gate_node)
            output_label = Text(f"O{i+1}", font_size=16, color=GREEN).move_to(output_node)

            input_nodes.add(VGroup(input_node, input_label))
            gate_nodes.add(VGroup(gate_node, gate_label))
            output_nodes.add(VGroup(output_node, output_label))

            layer_arrows.add(
                Arrow(
                    input_node.get_right(),
                    gate_node.get_left(),
                    buff=0.2,
                    color=WHITE
                )
            )

            layer_arrows.add(
                Arrow(
                    gate_node.get_right(),
                    output_node.get_left(),
                    buff=0.2,
                    color=WHITE
                )
            )

        with self.voiceover(text="The same mechanism operates across an entire layer. Each neuron can have a different tanh magnitude and a different sigmoid gate. This allows the network to selectively preserve or suppress information across the layer.") as tracker:
            self.play(Write(section_label), run_time=0.5)
            self.play(Create(input_nodes), Create(gate_nodes), Create(output_nodes), run_time=tracker.duration * 0.25)
            self.play(Create(layer_arrows), run_time=tracker.duration * 0.25)

            self.play(
                gate_nodes[0].animate.set_opacity(1.0),
                gate_nodes[1].animate.set_opacity(0.35),
                gate_nodes[2].animate.set_opacity(0.7),
                run_time=tracker.duration * 0.25
            )

            self.play(
                output_nodes[0].animate.set_opacity(1.0),
                output_nodes[1].animate.set_opacity(0.35),
                output_nodes[2].animate.set_opacity(0.7),
                run_time=tracker.duration * 0.25
            )

        self.wait(0.5)
        self.play(
            FadeOut(section_label),
            FadeOut(input_nodes),
            FadeOut(gate_nodes),
            FadeOut(output_nodes),
            FadeOut(layer_arrows)
        )

        # ===== 7. TAKEAWAYS =====
        takeaways_label = Text("Key Takeaways", font_size=34).to_edge(UP, buff=0.5)

        left_col = VGroup(
            Text("1. Tanh provides activation magnitude", font_size=22),
            Text("2. Sigmoid produces a gate from 0 to 1", font_size=22),
            Text("3. Element-wise product controls information", font_size=22),
        ).arrange(DOWN, buff=0.35, aligned_edge=LEFT)

        right_col = VGroup(
            Text("4. Each neuron can have a different gate", font_size=22),
            Text("5. Gradients update gate parameters", font_size=22),
            Text("6. Gates learn what information to pass", font_size=22),
        ).arrange(DOWN, buff=0.35, aligned_edge=LEFT)

        columns = VGroup(left_col, right_col).arrange(RIGHT, buff=1.0).center().shift(DOWN * 0.2)

        box = SurroundingRectangle(columns, color=BLUE, buff=0.3, corner_radius=0.1)

        with self.voiceover(text="To recap, tanh provides the magnitude, sigmoid provides the gate, and their element-wise product controls information flow. During training, gradients change the gate parameters so the network learns which information to pass.") as tracker:
            self.play(Write(takeaways_label), run_time=0.5)
            self.play(Create(box), run_time=tracker.duration * 0.2)
            self.play(Write(columns), run_time=tracker.duration * 0.6)

        self.wait(1)
        self.play(FadeOut(takeaways_label), FadeOut(columns), FadeOut(box))

        # End card
        end_text = Text("Gated activation = Tanh magnitude × Sigmoid gate", font_size=34)

        with self.voiceover(text="Gated activation equals the tanh magnitude multiplied element-wise by the sigmoid gate.") as tracker:
            self.play(Write(end_text), run_time=tracker.duration)

        self.wait(0.5)
        self.play(FadeOut(end_text))
