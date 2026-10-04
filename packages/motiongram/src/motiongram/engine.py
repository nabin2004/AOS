"""Neutral frame stepping: timeline then scene-graph update (single entry point per frame)."""

from __future__ import annotations

from collections.abc import Callable

from motiongram.animate import TimelineOnApply, apply_timeline, smoothstep
from motiongram.core import Scene


def step_frame(
    scene: Scene,
    t: float,
    dt: float,
    *,
    ease: Callable[[float], float] | None = smoothstep,
    on_apply: TimelineOnApply | None = None,
) -> None:
    """Apply timeline at global time ``t``, then run ``scene.root.update(t, dt)``.

    Matches the order used by :class:`Renderer.play` — keep this as the only mutation sequence
    for animation time + non-spatial ``update`` hooks.
    """
    apply_timeline(scene, t, ease=ease, on_apply=on_apply)
    scene.root.update(t, dt)
