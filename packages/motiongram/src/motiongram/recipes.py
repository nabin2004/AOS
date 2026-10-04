"""Reusable timeline snippets — thin wrappers around ``Scene.add_animation``.

These helpers encode common motion recipes while keeping scheduling explicit:
they only append clips to ``scene.timeline`` via ``add_animation``.
"""

from __future__ import annotations

from collections.abc import Sequence as Seq

from motiongram.animate import MoveY, Parallel, ScaleY, SquashStretch
from motiongram.core import Node, Scene


def add_squash_stretch_drop(
    scene: Scene,
    target: Node,
    t0: float,
    t1: float,
    *,
    y0: float,
    y1: float,
    amount: float = 0.45,
    axis: str = "y",
) -> None:
    """Squash-and-stretch while translating vertically (cf. bouncing ball).

    Mirrors :mod:`examples.principles.13_squash_stretch`: parallel volume-preserving
    oscillation and vertical motion on ``target``.
    """
    scene.add_animation(
        t0,
        t1,
        target,
        Parallel(SquashStretch(amount=amount, axis=axis), MoveY(y0, y1)),
    )


def add_blink(
    scene: Scene,
    targets: Seq[Node],
    t_start: float,
    *,
    blink_duration: float = 0.14,
    closed_scale_y: float = 0.12,
    closing_fraction: float = 0.45,
) -> None:
    """Scale ``targets`` down along ``scale_y`` then back — lid-style blink.

    Apply to lightweight wrapper :class:`~motiongram.core.Node` parents around each
    drawable so eyelids or whites squash symmetrically.
    """
    if blink_duration <= 0.0:
        return
    split = min(max(closing_fraction, 1e-6), 1.0 - 1e-6)
    t_mid = t_start + blink_duration * split
    t_end = t_start + blink_duration
    for tgt in targets:
        scene.add_animation(t_start, t_mid, tgt, ScaleY(1.0, closed_scale_y))
        scene.add_animation(t_mid, t_end, tgt, ScaleY(closed_scale_y, 1.0))


__all__ = ["add_blink", "add_squash_stretch_drop"]
