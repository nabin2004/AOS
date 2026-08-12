"""VoiceoverScene-friendly bookmark helpers for AI lectures."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from manim import FadeIn, Mobject, Scene


def reveal_with_bookmarks(
    scene: Scene,
    text: str,
    marks: Mapping[str, Mobject | Sequence[Mobject]],
    *,
    run_time: float = 0.35,
) -> None:
    """
    Play a voiceover ``text`` containing ``<bookmark mark='ID'/>`` tags and
    FadeIn the mapped mobjects when each bookmark fires.

    Requires ``scene`` to be a VoiceoverScene with speech service configured.
    """
    if not hasattr(scene, "voiceover") or not hasattr(scene, "wait_until_bookmark"):
        raise TypeError("reveal_with_bookmarks requires a VoiceoverScene")

    with scene.voiceover(text=text):
        for mark, mob in marks.items():
            scene.wait_until_bookmark(mark)
            items = mob if isinstance(mob, (list, tuple)) else [mob]
            scene.play(*[FadeIn(m) for m in items], run_time=run_time)


def narrate_steps(
    scene: Scene,
    intro: str,
    steps: Sequence[tuple[str, str, Mobject]],
    *,
    run_time: float = 0.4,
) -> None:
    """
    ``steps`` is a list of (bookmark_id, spoken_clause, mobject).
    Builds one voiceover string with bookmarks and reveals each step.
    """
    parts = [intro]
    marks: dict[str, Mobject] = {}
    for bid, clause, mob in steps:
        parts.append(f" <bookmark mark='{bid}'/>{clause}")
        marks[bid] = mob
    reveal_with_bookmarks(scene, "".join(parts), marks, run_time=run_time)
