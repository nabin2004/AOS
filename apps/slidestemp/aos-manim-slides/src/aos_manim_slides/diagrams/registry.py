from __future__ import annotations

from typing import Any, Callable, Dict

from manim import Axes, Dot, MathTex, Text, VGroup, UP, DOWN, LEFT, RIGHT

from aos_manim_core import ThemeConfig, get_theme

DiagramFactory = Callable[..., VGroup]


class DiagramNotFoundError(ValueError):
    """Raised when a Markdown/Python diagram name is not registered."""


def _sympy_expr(raw: Any) -> str:
    text = str(raw).strip()
    text = text.replace("^", "**")
    text = text.replace(" ", "")
    return text


def _placeholder(name: str, width: float, height: float, theme: ThemeConfig, message: str) -> VGroup:
    label = Text(message, font_size=theme.fonts.caption_font_size + 2, color=theme.text_muted, font=theme.fonts.text_font)
    group = VGroup(label)
    group.width = min(width, max(group.width, 0.5))
    if group.height > height:
        group.scale(height / max(group.height, 0.01))
    return group


def _gradient_descent(width: float, height: float, theme: ThemeConfig, **kwargs: Any) -> VGroup:
    expr = _sympy_expr(kwargs.get("f", kwargs.get("expr", "x**2")))
    x_val = float(kwargs.get("x", kwargs.get("x0", 1.5)))
    try:
        from aos_manim_maths import DerivativeVisualizer

        vis = DerivativeVisualizer(theme=theme)
        data = vis.build_derivative_mobjects(
            expr,
            x_val,
            axes_width=max(width * 0.95, 3.0),
            axes_height=max(height * 0.85, 2.2),
        )
        group = VGroup(data["axes"], data["curve"], data["tangent_line"], data["point"])
        if "labels" in data:
            group.add(data["labels"])
        return group
    except Exception:
        return _placeholder("gradient_descent", width, height, theme, "gradient_descent")


def _newton_method(width: float, height: float, theme: ThemeConfig, **kwargs: Any) -> VGroup:
    expr = _sympy_expr(kwargs.get("f", kwargs.get("expr", "x**2-2")))
    x0 = float(kwargs.get("x0", 1.5))
    try:
        from aos_manim_maths import RootFindingVisualizer

        vis = RootFindingVisualizer(theme=theme)
        return vis.build_cueable_root_finding(
            expr,
            x0,
            axes_width=max(width * 0.95, 3.0),
            axes_height=max(height * 0.85, 2.2),
            show_all_steps=True,
        )
    except Exception:
        return _placeholder("newton_method", width, height, theme, "newton_method")


def _binary_search(width: float, height: float, theme: ThemeConfig, **kwargs: Any) -> VGroup:
    raw_arr = kwargs.get("arr", kwargs.get("array", [1, 3, 4, 7, 9, 11, 15]))
    if isinstance(raw_arr, str):
        arr = [int(x.strip()) for x in raw_arr.strip("[]").split(",") if x.strip()]
    else:
        arr = list(raw_arr)
    target = int(kwargs.get("target", 7))
    try:
        from aos_manim_algorithms import BinarySearchVisualizer

        vis = BinarySearchVisualizer(theme=theme)
        group = vis.build_cueable_binary_search(arr, target)
        if group.height > height or group.width > width:
            s = min(width / max(group.width, 0.01), height / max(group.height, 0.01), 1.0)
            group.scale(s)
        return group
    except Exception:
        return _placeholder("binary_search", width, height, theme, "binary_search")


_REGISTRY: Dict[str, DiagramFactory] = {
    "gradient_descent": _gradient_descent,
    "newton_method": _newton_method,
    "binary_search": _binary_search,
}


def register_diagram(name: str, factory: DiagramFactory) -> None:
    _REGISTRY[name] = factory


def known_diagrams() -> list[str]:
    return sorted(_REGISTRY.keys())


def build_diagram(
    name: str,
    width: float,
    height: float,
    theme: ThemeConfig | None = None,
    **kwargs: Any,
) -> VGroup:
    theme = theme or get_theme()
    factory = _REGISTRY.get(name)
    if factory is None:
        raise DiagramNotFoundError(
            f"Unknown diagram '{name}'. Known diagrams: {', '.join(known_diagrams()) or '(none)'}."
        )
    return factory(width, height, theme, **kwargs)


AnimationFactory = Callable[..., VGroup]
_ANIMATIONS: Dict[str, AnimationFactory] = {}


def register_animation(name: str, factory: AnimationFactory) -> None:
    """Register a programmatic animation factory (width, height, theme, **kwargs) -> VGroup."""
    _ANIMATIONS[name] = factory


def known_animations() -> list[str]:
    return sorted(_ANIMATIONS.keys())


def _animation_placeholder(name: str, width: float, height: float, theme: ThemeConfig) -> VGroup:
    from manim import RoundedRectangle

    from aos_manim_slides.typography import slide_tex

    frame = RoundedRectangle(
        width=max(width, 1.0),
        height=max(height, 1.0),
        corner_radius=0.12,
        stroke_color=theme.border,
        fill_color=theme.surface,
        fill_opacity=0.35,
        stroke_width=2,
    )
    label = slide_tex(name.replace("_", " "), font_size=theme.fonts.caption_font_size + 4, color=theme.text_muted)
    group = VGroup(frame, label)
    label.move_to(frame.get_center())

    def play_on(scene: Any) -> None:
        return None

    def apply_cue(scene: Any, cue: Any) -> None:
        return None

    def cue_targets() -> Dict[str, Any]:
        return {"self": group}

    def step_count() -> int:
        return 0

    group.play_on = play_on  # type: ignore[attr-defined]
    group.apply_cue = apply_cue  # type: ignore[attr-defined]
    group.cue_targets = cue_targets  # type: ignore[attr-defined]
    group.step_count = step_count  # type: ignore[attr-defined]
    return group


def build_animation(
    name: str,
    width: float,
    height: float,
    theme: ThemeConfig | None = None,
    **kwargs: Any,
) -> VGroup:
    """Build a registered animation, or a labeled frame if the name is unknown."""
    theme = theme or get_theme()
    factory = _ANIMATIONS.get(name)
    if factory is None:
        return _animation_placeholder(name, width, height, theme)
    return factory(width, height, theme, **kwargs)
