"""
Manim Living Slide Toolkit
Generic, task-agnostic functions for creating educational video slides
that breathe with continuous micro‑animations.
"""

from manim import *
from typing import List, Dict, Tuple, Optional, Callable
import numpy as np
import sys

# =============================================================================
# CONFIGURATION
# =============================================================================


def configure_scene(
    pixel_height: int = 1080, pixel_width: int = 1920, background_color: str = "#1e1e1e"
) -> None:
    """Configure Manim rendering settings."""
    config.pixel_height = pixel_height
    config.pixel_width = pixel_width
    config.background_color = background_color


# =============================================================================
# LIVING ANIMATION UTILITIES – breathing, pulsing, sway
# =============================================================================


def breathe(
    mobject: Mobject,
    scale_factor: float = 1.02,
    run_time: float = 2,
    rate_func=there_and_back,
) -> Animation:
    """
    A subtle 'breathe' effect – repeatedly scale up and down.
    Returns an animation that can be played (usually in an always‑on loop).
    """
    return (
        mobject.animate.scale(scale_factor)
        .set_rate_func(rate_func)
        .set_run_time(run_time)
    )


def pulse(mobject: Mobject, factor: float = 0.08, run_time: float = 1.5) -> Animation:
    """Gentle color/size pulse. Brightens the object slightly and scales a little."""
    return AnimationGroup(
        mobject.animate.set_stroke(width=mobject.get_stroke_width() * 1.3)
        .set_rate_func(there_and_back)
        .set_run_time(run_time),
        mobject.animate.scale(1 + factor)
        .set_rate_func(there_and_back)
        .set_run_time(run_time),
        lag_ratio=0,
    )


def sway(
    mobject: Mobject, direction: np.ndarray = UP * 0.05, run_time: float = 2.0
) -> Animation:
    """Tiny rocking motion."""
    return (
        mobject.animate.shift(direction)
        .set_rate_func(there_and_back)
        .set_run_time(run_time)
    )


def living_loop(
    scene: Scene,
    mobject: Mobject,
    anim_func: Callable[[Mobject], Animation],
    pause: float = 0.0,
) -> None:
    """
    Attach an endless subtle animation to a mobject.
    The animation will keep running until the scene is torn down.
    """
    # Use Scene.add_forever_mobject if available (ManimCE v0.18+),
    # otherwise we schedule a continuous update.
    if hasattr(scene, "add_forever_mobject"):
        scene.add_forever_mobject(mobject)
        mobject.add_updater(lambda m, dt: anim_func(m).interpolate(0.5))
    else:
        # fallback: just play the animation once and let it be
        scene.play(anim_func(mobject))


# =============================================================================
# UI COMPONENTS (Low-level building blocks)
# =============================================================================


def create_bullet(
    text: str,
    color: str = WHITE,
    emphasize: bool = False,
    font_size: int = 32,
    bullet_color: str = YELLOW,
    bullet_radius: float = 0.08,
    buff: float = 0.2,
) -> VGroup:
    """Create a single bullet point with a dot and text (now with breathing option)."""
    dot = Dot(radius=bullet_radius, color=bullet_color)
    txt = Text(text, font_size=font_size, color=color).next_to(dot, RIGHT, buff=buff)

    if emphasize:
        txt.set_color(YELLOW)
        txt.set_weight(BOLD)

    return VGroup(dot, txt)


def create_bullet_list(
    items: List[Dict],
    direction: np.ndarray = DOWN,
    aligned_edge: np.ndarray = LEFT,
    buff: float = 0.4,
) -> VGroup:
    """Create a vertical/horizontal list of bullet points."""
    bullets = [
        create_bullet(
            text=item.get("text", ""),
            color=item.get("color", WHITE),
            emphasize=item.get("emphasize", False),
            font_size=item.get("font_size", 32),
        )
        for item in items
    ]
    return VGroup(*bullets).arrange(direction, aligned_edge=aligned_edge, buff=buff)


def create_neural_block(
    height: float,
    width: float,
    color: str = BLUE,
    label: str = "",
    font_size: int = 20,
    depth: int = 1,
    depth_shift: Tuple[float, float] = (0.1, 0.1),
    fill_opacity: float = 0.3,
) -> VGroup:
    """Create a pseudo‑3D neural network layer block."""
    group = VGroup()
    block = Rectangle(
        height=height, width=width, color=color, fill_opacity=fill_opacity
    )
    group.add(block)

    if label:
        lbl = Text(label, font_size=font_size).move_to(block.get_center())
        group.add(lbl)

    if depth > 1:
        dx, dy = depth_shift
        for i in range(1, depth):
            back = Rectangle(
                height=height,
                width=width,
                color=color,
                fill_opacity=max(0.05, fill_opacity - 0.1 * i),
            )
            back.shift(LEFT * dx * i + UP * dy * i)
            group.add(back)
    return group


def create_neural_network(
    layers: List[int],
    layer_spacing: float = 1.5,
    neuron_radius: float = 0.3,
    neuron_color: str = WHITE,
    edge_color: str = GRAY,
    edge_width: float = 2,
    vertical_buff: float = 0.5,
) -> Tuple[VGroup, VGroup]:
    """Create a multi‑layer neural network diagram."""
    neurons = VGroup()
    edges = VGroup()
    layer_groups = []

    for i, n in enumerate(layers):
        layer = VGroup(
            *[
                Circle(radius=neuron_radius, color=neuron_color, fill_opacity=1)
                for _ in range(n)
            ]
        )
        layer.arrange(DOWN, buff=vertical_buff)
        layer.move_to(
            LEFT * (len(layers) - 1) * layer_spacing / 2 + RIGHT * i * layer_spacing
        )
        layer_groups.append(layer)
        neurons.add(layer)

    for i in range(len(layers) - 1):
        for n1 in layer_groups[i]:
            for n2 in layer_groups[i + 1]:
                edge = Line(
                    n1.get_center(),
                    n2.get_center(),
                    color=edge_color,
                    stroke_width=edge_width,
                )
                edges.add(edge)

    return neurons, edges


def create_search_visualization(
    title: str,
    points: List[Tuple[float, float]],
    x_range: Tuple[float, float, float] = (0, 3, 1),
    y_range: Tuple[float, float, float] = (0, 3, 1),
    axis_length: float = 3,
    dot_color: str = RED,
    title_color: str = YELLOW,
) -> VGroup:
    """Create a 2D search space visualization."""
    plot = VGroup()
    axis = Axes(
        x_range=x_range, y_range=y_range, x_length=axis_length, y_length=axis_length
    )
    title_text = Text(title, font_size=24, color=title_color).next_to(axis, UP)
    plot.add(axis, title_text)
    dots = VGroup(*[Dot(axis.c2p(x, y), color=dot_color) for x, y in points])
    plot.add(dots)
    return plot


def create_residual_block(
    x_label: str = "x",
    f_label: str = "F(x)",
    output_label: str = "H(x) = F(x) + x",
    identity_label: str = "Identity",
    block_color: str = YELLOW,
    curve_color: str = BLUE,
) -> VGroup:
    """Create a ResNet‑style residual block diagram (generic)."""
    group = VGroup()
    x_circle = Circle(radius=0.2, color=WHITE, fill_opacity=1)
    x_text = MathTex(x_label).move_to(x_circle.get_center())
    x_group = VGroup(x_circle, x_text).shift(DOWN * 2)

    block = RoundedRectangle(height=2, width=3, color=block_color, corner_radius=0.2)
    block_text = MathTex(f_label).move_to(block.get_center())
    f_group = VGroup(block, block_text).next_to(x_group, UP, buff=1.5)

    identity_curve = ArcBetweenPoints(
        x_group.get_right(),
        f_group.get_right() + RIGHT * 3,
        angle=-PI / 2,
        color=curve_color,
    )
    ident_text = MathTex(identity_label).next_to(identity_curve, RIGHT, buff=0.5)

    plus = MathTex("+").next_to(f_group, UP, buff=0.5)
    output = MathTex(output_label).next_to(plus, UP, buff=0.5)

    group.add(x_group, f_group, identity_curve, ident_text, plus, output)
    return group


# =============================================================================
# LIVING SLIDE RENDERERS (breathing/pulsing built in)
# =============================================================================


def render_title_slide(
    scene: Scene,
    title: str,
    subtitle: str = "",
    title_color: str = BLUE,
    subtitle_color: str = WHITE,
    title_size: int = 64,
    subtitle_size: int = 40,
    animation_run_time: float = 1,
) -> None:
    """
    Title slide with a breathing subtitle.
    """
    title_obj = Text(title, font_size=title_size, color=title_color)
    title_obj.to_edge(UP)
    scene.play(Write(title_obj), run_time=animation_run_time)

    if subtitle:
        subtitle_obj = Text(subtitle, font_size=subtitle_size, color=subtitle_color)
        subtitle_obj.next_to(title_obj, DOWN)
        scene.play(FadeIn(subtitle_obj, shift=UP), run_time=animation_run_time)
        # Subtle breathing on subtitle
        living_loop(scene, subtitle_obj, lambda m: breathe(m, scale_factor=1.01))


def render_overview_slide(
    scene: Scene,
    title: str,
    left_items: List[Dict],
    right_items: List[Dict],
    title_color: str = WHITE,
    title_size: int = 48,
    left_shift: np.ndarray = LEFT * 4.5 + UP * 1,
    right_shift: np.ndarray = RIGHT * 4.5 + UP * 1,
    animation_run_time: float = 1,
) -> None:
    """Two‑column overview with gentle sway on each bullet list."""
    title_obj = Text(title, font_size=title_size, color=title_color).to_edge(UP)
    scene.play(Write(title_obj), run_time=animation_run_time)

    left_col = create_bullet_list(left_items).shift(left_shift)
    right_col = create_bullet_list(right_items).shift(right_shift)

    scene.play(FadeIn(left_col), FadeIn(right_col), run_time=animation_run_time)
    # Add tiny living sway to both lists
    living_loop(scene, left_col, lambda m: sway(m, direction=UP * 0.03))
    living_loop(scene, right_col, lambda m: sway(m, direction=DOWN * 0.03))


def render_bullet_slide(
    scene: Scene,
    title: str,
    bullets: List[Dict],
    title_color: str = WHITE,
    title_size: int = 48,
    bullet_delay: float = 0.2,
    animation_run_time: float = 0.5,
    position_shift: np.ndarray = UP * 1,
) -> None:
    """Sequential bullet slide – each bullet gets a tiny pulse after appearing."""
    title_obj = Text(title, font_size=title_size, color=title_color).to_edge(UP)
    scene.play(Write(title_obj), run_time=animation_run_time)

    bullet_group = create_bullet_list(bullets).shift(position_shift)

    for bullet in bullet_group:
        scene.play(Write(bullet), run_time=animation_run_time)
        # Pulse the newly added bullet (temporary)
        scene.play(pulse(bullet, factor=0.05), run_time=0.5)
        scene.wait(bullet_delay)


def render_architecture_slide(
    scene: Scene,
    title: str,
    input_config: Dict,
    output_config: Dict,
    filter_config: Optional[Dict] = None,
    arrow_config: Optional[Dict] = None,
    annotation: Optional[str] = None,
    title_color: str = WHITE,
    title_size: int = 48,
) -> None:
    """Architecture slide with breathing blocks."""
    title_obj = Text(title, font_size=title_size, color=title_color).to_edge(UP)
    scene.play(Write(title_obj))

    input_block = create_neural_block(**input_config).shift(LEFT * 3)
    output_block = create_neural_block(**output_config).shift(RIGHT * 3)

    elements = [input_block, output_block]

    if filter_config:
        num_filters = filter_config.pop("num", 6)
        filter_shift = filter_config.pop("shift", DOWN * 2 + LEFT * 1)
        filter_scale = filter_config.pop("scale", 0.6)
        filters = VGroup(
            *[create_neural_block(**filter_config) for _ in range(num_filters)]
        )
        filters.arrange(RIGHT, buff=0.05).scale(filter_scale).shift(filter_shift)
        elements.append(filters)
        arrow2 = Arrow(
            filters.get_top(), output_block.get_center() + DOWN * 3, buff=0.5
        )
        elements.append(arrow2)

    arrow1 = Arrow(input_block.get_right(), output_block.get_left(), buff=0.5)
    elements.append(arrow1)

    scene.play(
        *[FadeIn(e) for e in elements if isinstance(e, VGroup)],
        *[Create(e) for e in elements if isinstance(e, Arrow)],
    )

    # Make the main blocks breathe
    for block in [input_block, output_block]:
        if isinstance(block, VGroup):
            living_loop(scene, block, lambda m: breathe(m, scale_factor=1.01))

    if annotation:
        ann = Text(annotation, font_size=30, color=YELLOW).next_to(output_block, RIGHT)
        scene.play(Write(ann))


def render_resnet_slide(
    scene: Scene,
    title: str,
    block_config: Optional[Dict] = None,
    title_color: str = WHITE,
    title_size: int = 48,
) -> None:
    """Residual block slide with pulsing identity connection."""
    title_obj = Text(title, font_size=title_size, color=title_color).to_edge(UP)
    scene.play(Write(title_obj))

    config = block_config or {}
    diagram = create_residual_block(**config)

    # Animate sequentially
    scene.play(FadeIn(diagram[0]))  # x
    scene.wait(0.5)
    scene.play(Write(diagram[1]))  # F(x) block
    scene.play(Create(diagram[2]), Write(diagram[3]))  # identity
    scene.play(Write(diagram[4]))  # plus
    scene.play(Write(diagram[5]))  # output

    # Pulsing on the identity curve
    living_loop(scene, diagram[2], lambda m: pulse(m, factor=0.1))


def render_dropout_slide(
    scene: Scene,
    title: str,
    layers: List[int] = None,
    dropout_indices: List[Tuple[int, int]] = None,
    dropout_label: str = "Randomly drop neurons",
    title_color: str = WHITE,
    title_size: int = 48,
    layer_spacing: float = 1.5,
    vertical_buff: float = 0.5,
) -> None:
    """Dropout visualization – dropped neurons stay dim and pulse occasionally."""
    layers = layers or [4, 5, 5, 3]
    dropout_indices = dropout_indices or [(1, 0), (1, 1)]

    title_obj = Text(title, font_size=title_size, color=title_color).to_edge(UP)
    scene.play(Write(title_obj))

    neurons, edges = create_neural_network(
        layers=layers, layer_spacing=layer_spacing, vertical_buff=vertical_buff
    )
    scene.play(FadeIn(edges), FadeIn(neurons))
    scene.wait(1)

    label = Text(dropout_label, font_size=36, color=RED).shift(DOWN * 3)
    scene.play(Write(label))

    to_drop = []
    for layer_idx, neuron_idx in dropout_indices:
        if layer_idx < len(neurons) and neuron_idx < len(neurons[layer_idx]):
            to_drop.append(neurons[layer_idx][neuron_idx])

    if to_drop:
        scene.play(
            *[
                Transform(n, n.copy().set_fill(color=GRAY).set_opacity(0.3))
                for n in to_drop
            ],
            run_time=1,
        )
        # Dimmed neurons pulse weakly to remind they're "missing"
        for n in to_drop:
            living_loop(scene, n, lambda m, _n=n: pulse(_n, factor=0.02))


def render_comparison_slide(
    scene: Scene,
    title: str,
    left_plot_config: Dict,
    right_plot_config: Dict,
    title_color: str = WHITE,
    title_size: int = 48,
    left_shift: np.ndarray = LEFT * 4 + DOWN * 2,
    right_shift: np.ndarray = RIGHT * 4 + DOWN * 2,
) -> None:
    """Side‑by‑side plots, both breathing gently."""
    title_obj = Text(title, font_size=title_size, color=title_color).to_edge(UP)
    scene.play(Write(title_obj))

    left_plot = create_search_visualization(**left_plot_config).shift(left_shift)
    right_plot = create_search_visualization(**right_plot_config).shift(right_shift)

    scene.play(FadeIn(left_plot), FadeIn(right_plot))
    living_loop(scene, left_plot, lambda m: breathe(m, scale_factor=1.01))
    living_loop(scene, right_plot, lambda m: breathe(m, scale_factor=1.01))


# =============================================================================
# SCENE FACTORY (Orchestrator)
# =============================================================================


def build_slide_scene(
    slide_type: str, data: Dict, scene_class: Optional[type] = None
) -> type:
    """Factory that returns a LivingScene class configured for a specific slide."""
    scene_class = scene_class or Scene

    renderers = {
        "title": render_title_slide,
        "overview": render_overview_slide,
        "bullets": render_bullet_slide,
        "architecture": render_architecture_slide,
        "resnet": render_resnet_slide,
        "dropout": render_dropout_slide,
        "comparison": render_comparison_slide,
    }

    renderer = renderers.get(slide_type, render_title_slide)

    class GeneratedSlide(scene_class):
        def construct(self):
            renderer(self, **data)
            # Let the breathing animations play for a moment
            self.wait(3)
            self.play(FadeOut(*self.mobjects))

    GeneratedSlide.__name__ = f"{slide_type.capitalize()}LivingSlide"
    GeneratedSlide.__module__ = sys._getframe(1).f_globals.get("__name__", __name__)
    return GeneratedSlide


# =============================================================================
# UTILITY HELPERS
# =============================================================================


def generate_grid_points(
    x_vals: List[float], y_vals: List[float]
) -> List[Tuple[float, float]]:
    return [(x, y) for x in x_vals for y in y_vals]


def generate_random_points(
    count: int,
    x_range: Tuple[float, float] = (0.3, 2.7),
    y_range: Tuple[float, float] = (0.3, 2.7),
    seed: Optional[int] = None,
) -> List[Tuple[float, float]]:
    if seed is not None:
        np.random.seed(seed)
    return [
        (np.random.uniform(*x_range), np.random.uniform(*y_range)) for _ in range(count)
    ]


def make_bullet_item(
    text: str, emphasize: bool = False, color: str = WHITE, **kwargs
) -> Dict:
    return {"text": text, "emphasize": emphasize, "color": color, **kwargs}


# =============================================================================
# EXAMPLE USAGE (generic, living slides)
# =============================================================================

if __name__ == "__main__":
    # Example 1: Title Slide – breathing subtitle
    TitleLivingSlide = build_slide_scene(
        "title",
        {
            "title": "Introduction to Data Science",
            "subtitle": "From Raw Data to Insights",
        },
    )

    # Example 2: Overview Slide – swaying columns
    OverviewLivingSlide = build_slide_scene(
        "overview",
        {
            "title": "Today's Agenda",
            "left_items": [
                make_bullet_item("Data Collection & Cleaning"),
                make_bullet_item("Exploratory Analysis"),
                make_bullet_item("Feature Engineering"),
            ],
            "right_items": [
                make_bullet_item("Model Selection"),
                make_bullet_item("Training & Validation"),
                make_bullet_item("Deployment Strategies"),
            ],
        },
    )

    # Example 3: Architecture Slide (generic layered diagram)
    ArchLivingSlide = build_slide_scene(
        "architecture",
        {
            "title": "Pipeline Overview",
            "input_config": {
                "height": 2,
                "width": 1.5,
                "color": BLUE,
                "label": "Raw Data",
                "depth": 3,
            },
            "output_config": {
                "height": 2,
                "width": 1.5,
                "color": GREEN,
                "label": "Predictions",
                "depth": 3,
            },
            "filter_config": {
                "num": 4,
                "height": 1.5,
                "width": 1.5,
                "color": ORANGE,
                "label": "Transform",
                "shift": DOWN * 1.5 + LEFT * 0.5,
                "scale": 0.8,
            },
            "annotation": "Feedback Loop",
        },
    )

    # Example 4: Bullet Slide – each item pulses on entry
    BulletLivingSlide = build_slide_scene(
        "bullets",
        {
            "title": "Steps to Clean Data",
            "bullets": [
                make_bullet_item("Remove duplicates"),
                make_bullet_item("Handle missing values"),
                make_bullet_item("Normalize formats"),
                make_bullet_item("Validate with domain rules"),
            ],
        },
    )

    # Example 5: Dropout Slide (generic, now pulsing dim neurons)
    DropoutLivingSlide = build_slide_scene(
        "dropout",
        {
            "title": "Regularization: Dropout",
            "layers": [4, 5, 5, 3],
            "dropout_indices": [(1, 0), (1, 1)],
        },
    )

    # Example 6: Comparison Slide (Grid vs Random Search with breathing plots)
    ComparisonLivingSlide = build_slide_scene(
        "comparison",
        {
            "title": "Hyperparameter Search Strategies",
            "left_plot_config": {
                "title": "Grid Search",
                "points": generate_grid_points([0.5, 1.5, 2.5], [0.5, 1.5, 2.5]),
            },
            "right_plot_config": {
                "title": "Random Search",
                "points": generate_random_points(9, seed=42),
            },
        },
    )
