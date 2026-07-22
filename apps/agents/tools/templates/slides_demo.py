"""
Slides.py Manim Demo — full deck + individual living slide scenes.

RENDER (from this directory):
    cd apps/agents/tools/templates

    # Full deck (all 7 slide types)
    uv run manim -pqh --media_dir . slides_demo.py SlidesShowcase

    # Any single slide
    uv run manim -pqh --media_dir . slides_demo.py TitleLivingSlide
"""

from manim import BLUE, DOWN, FadeOut, GREEN, LEFT, ORANGE, Scene

from slides import (
    build_slide_scene,
    configure_scene,
    generate_grid_points,
    generate_random_points,
    make_bullet_item,
    render_architecture_slide,
    render_bullet_slide,
    render_comparison_slide,
    render_dropout_slide,
    render_overview_slide,
    render_resnet_slide,
    render_title_slide,
)

# =============================================================================
# Shared demo data
# =============================================================================

TITLE_DATA = {
    "title": "Introduction to Data Science",
    "subtitle": "From Raw Data to Insights",
}

OVERVIEW_DATA = {
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
}

BULLETS_DATA = {
    "title": "Steps to Clean Data",
    "bullets": [
        make_bullet_item("Remove duplicates"),
        make_bullet_item("Handle missing values"),
        make_bullet_item("Normalize formats"),
        make_bullet_item("Validate with domain rules"),
    ],
}

ARCHITECTURE_DATA = {
    "title": "Pipeline Overview",
    "annotation": "Feedback Loop",
}

RESNET_DATA = {
    "title": "Residual Connections",
    "block_config": {
        "x_label": "x",
        "f_label": "F(x)",
        "output_label": "H(x) = F(x) + x",
        "identity_label": "Identity",
    },
}

DROPOUT_DATA = {
    "title": "Regularization: Dropout",
    "layers": [4, 5, 5, 3],
    "dropout_indices": [(1, 0), (1, 1)],
}

COMPARISON_DATA = {
    "title": "Hyperparameter Search Strategies",
    "left_plot_config": {
        "title": "Grid Search",
        "points": generate_grid_points([0.5, 1.5, 2.5], [0.5, 1.5, 2.5]),
    },
    "right_plot_config": {
        "title": "Random Search",
        "points": generate_random_points(9, seed=42),
    },
}


def _architecture_data():
    """Fresh copy — render_architecture_slide mutates filter_config via .pop()."""
    return {
        "title": ARCHITECTURE_DATA["title"],
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
        "annotation": ARCHITECTURE_DATA["annotation"],
    }


# =============================================================================
# Individual scene classes (via factory)
# =============================================================================

TitleLivingSlide = build_slide_scene("title", TITLE_DATA)
OverviewLivingSlide = build_slide_scene("overview", OVERVIEW_DATA)
BulletsLivingSlide = build_slide_scene("bullets", BULLETS_DATA)
ArchitectureLivingSlide = build_slide_scene("architecture", _architecture_data())
ResnetLivingSlide = build_slide_scene("resnet", RESNET_DATA)
DropoutLivingSlide = build_slide_scene("dropout", DROPOUT_DATA)
ComparisonLivingSlide = build_slide_scene("comparison", COMPARISON_DATA)


# =============================================================================
# Full deck orchestrator
# =============================================================================


def _clear_slide(scene: Scene) -> None:
    if scene.mobjects:
        scene.play(FadeOut(*scene.mobjects))


class SlidesShowcase(Scene):
    """Chains all seven slide renderers into one continuous presentation."""

    def construct(self):
        configure_scene()

        render_title_slide(self, **TITLE_DATA)
        self.wait(2)
        _clear_slide(self)

        render_overview_slide(self, **OVERVIEW_DATA)
        self.wait(2)
        _clear_slide(self)

        render_bullet_slide(self, **BULLETS_DATA)
        self.wait(2)
        _clear_slide(self)

        render_architecture_slide(self, **_architecture_data())
        self.wait(2)
        _clear_slide(self)

        render_resnet_slide(self, **RESNET_DATA)
        self.wait(2)
        _clear_slide(self)

        render_dropout_slide(self, **DROPOUT_DATA)
        self.wait(2)
        _clear_slide(self)

        render_comparison_slide(self, **COMPARISON_DATA)
        self.wait(2)
        _clear_slide(self)
