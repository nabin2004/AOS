from __future__ import annotations

from typing import Any, Iterable, Optional, Sequence

from manim import DOWN, LEFT, UP, Dot, FadeIn, RIGHT, Text, VGroup

from aos_manim_core import ThemeConfig, get_theme

from ..typography import slide_tex


def safe_play(scene: Any, *anims: Any, **kwargs: Any) -> None:
    play = getattr(scene, "play", None)
    if callable(play) and anims:
        play(*anims, **kwargs)
        return
    for anim in anims:
        mob = getattr(anim, "mobject", None)
        if mob is not None and hasattr(mob, "set_opacity"):
            mob.set_opacity(1)


def safe_wait(scene: Any, t: float = 0.3) -> None:
    wait = getattr(scene, "wait", None)
    if callable(wait):
        wait(t)


def pin_top_left(mob: Any, *, up: float = 0.55, left: float = 0.85) -> Any:
    mob.to_edge(UP, buff=up)
    mob.to_edge(LEFT, buff=left)
    return mob


def make_bullet_row(text: str, theme: ThemeConfig, font_size: int = 32) -> VGroup:
    dot = Dot(radius=0.07, color=theme.primary)
    label = slide_tex(text, font_size=font_size, color=theme.text_main)
    return VGroup(dot, label).arrange(RIGHT, buff=0.22)


def bullet_rows(
    items: Sequence[str],
    theme: Optional[ThemeConfig] = None,
    font_size: int = 32,
    buff: float = 0.5,
) -> VGroup:
    t = theme or get_theme()
    rows = VGroup(*[make_bullet_row(item, t, font_size=font_size) for item in items])
    return rows.arrange(DOWN, aligned_edge=LEFT, buff=buff)


def play_bullets(
    scene: Any,
    items: Iterable[Any],
    *,
    run_time: float = 0.45,
    shift=RIGHT,
) -> None:
    """Fade each bullet in from the left (need_to_implement Slide3)."""
    for item in items:
        safe_play(scene, FadeIn(item, shift=shift), run_time=run_time)


def play_column_rows(
    scene: Any,
    left: Sequence[Any],
    right: Sequence[Any],
    *,
    run_time: float = 0.5,
    shift=RIGHT,
) -> None:
    """Reveal row i of both columns together (need_to_implement TwoColumnSlide)."""
    n = max(len(left), len(right))
    for i in range(n):
        anims = []
        if i < len(left):
            anims.append(FadeIn(left[i], shift=shift))
        if i < len(right):
            anims.append(FadeIn(right[i], shift=shift))
        if anims:
            safe_play(scene, *anims, run_time=run_time)


def colored_text(
    text: str,
    *,
    font_size: int = 32,
    theme: Optional[ThemeConfig] = None,
    highlights: Optional[dict[str, Any]] = None,
):
    t = theme or get_theme()
    t2c = {k: v for k, v in (highlights or {}).items()}
    if t2c:
        return Text(
            text,
            font_size=font_size,
            color=t.text_main,
            t2c=t2c,
        )
    return slide_tex(text, font_size=font_size, color=t.text_main)


def voiceover_from_items(title: str, items: Sequence[str], ids: Sequence[str]) -> str:
    parts: list[str] = []
    if title:
        parts.append(f"{title}.")
    for cid, item in zip(ids, items):
        parts.append(f"<bookmark mark='{cid}'/>{item}.")
    return " ".join(parts)


voiceover_from_items = voiceover_from_items
