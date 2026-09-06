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
    """Smooth, clean transition between slides: fades out existing elements, clears canvas, then fades in new slide."""
    from manim import Group
    to_fade = [m for m in scene.mobjects if m != new_mob]
    fade_mob = Group(*to_fade) if to_fade else old_mob
    half = max(run_time * 0.5, 0.2)
    scene.play(FadeOut(fade_mob, run_time=half))
    if hasattr(scene, "clear"):
        scene.clear()
    else:
        scene.remove(fade_mob)
    scene.play(FadeIn(new_mob, run_time=half))


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
