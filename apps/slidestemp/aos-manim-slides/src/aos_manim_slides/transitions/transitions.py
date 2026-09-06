from __future__ import annotations

from typing import Optional
from manim import (
    Scene,
    Mobject,
    FadeOut,
    FadeIn,
    ReplacementTransform,
    TransformMatchingShapes,
    AnimationGroup,
    LEFT,
    RIGHT,
    UP,
    DOWN,
)


def fade_transition(scene: Scene, old_mob: Mobject, new_mob: Mobject, run_time: float = 0.8) -> None:
    """Smooth cross-fade between two slides or layouts."""
    scene.play(
        FadeOut(old_mob, run_time=run_time),
        FadeIn(new_mob, run_time=run_time),
    )
    scene.remove(old_mob)


def wipe_transition(
    scene: Scene,
    old_mob: Mobject,
    new_mob: Mobject,
    direction: list[float] = LEFT,
    run_time: float = 0.8,
) -> None:
    """Wipe old slide off screen while bringing new slide in from the opposite direction."""
    new_mob.shift(-direction * 14)
    scene.play(
        old_mob.animate.shift(direction * 14),
        new_mob.animate.shift(direction * 14),
        run_time=run_time,
    )
    scene.remove(old_mob)


def zoom_slide_transition(scene: Scene, old_mob: Mobject, new_mob: Mobject, run_time: float = 0.9) -> None:
    """Scale-zoom transition between slides."""
    new_mob.scale(0.2)
    new_mob.set_opacity(0)
    scene.play(
        old_mob.animate.scale(2.0).set_opacity(0),
        new_mob.animate.scale(5.0).set_opacity(1.0),
        run_time=run_time,
    )
    scene.remove(old_mob)
