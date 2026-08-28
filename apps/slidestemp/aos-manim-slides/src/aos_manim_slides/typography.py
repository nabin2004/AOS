from __future__ import annotations

from typing import Optional

from manim import Text, VGroup

_TEX_ESCAPES = (
    ("\\", r"\textbackslash{}"),
    ("{", r"\{"),
    ("}", r"\}"),
    ("$", r"\$"),
    ("%", r"\%"),
    ("&", r"\&"),
    ("#", r"\#"),
    ("_", r"\_"),
    ("~", r"\textasciitilde{}"),
    ("^", r"\textasciicircum{}"),
)


def escape_tex(text: str) -> str:
    """Escape a plain-language string for Computer Modern ``Tex``."""
    out = text or ""
    for src, dst in _TEX_ESCAPES:
        out = out.replace(src, dst)
    return out


def _text_fallback(text: str, *, font_size: int, color, weight: str = "NORMAL") -> Text:
    kwargs = {"font_size": font_size, "color": color}
    if weight and weight.upper() == "BOLD":
        kwargs["weight"] = "BOLD"
    return Text(text or " ", **kwargs)


def slide_tex(
    text: str,
    *,
    font_size: int = 24,
    color=None,
    weight: str = "NORMAL",
    slant: Optional[str] = None,
):
    """Body/title type in default LaTeX Computer Modern.

    Falls back to Manim ``Text`` *without* a custom ``font=`` when LaTeX is
    unavailable so we never force Sans.
    """
    from aos_manim_core import get_theme

    color = color if color is not None else get_theme().text_main
    source = text or " "
    try:
        from manim import Tex

        body = escape_tex(source)
        if weight and weight.upper() == "BOLD":
            body = rf"\textbf{{{body}}}"
        if slant and str(slant).upper() == "ITALIC":
            body = rf"\textit{{{body}}}"
        return Tex(body, font_size=font_size, color=color)
    except Exception:
        mob = _text_fallback(source, font_size=font_size, color=color, weight=weight)
        if slant and str(slant).upper() == "ITALIC" and hasattr(mob, "set_slant"):
            try:
                mob = _text_fallback(source, font_size=font_size, color=color, weight=weight)
            except Exception:
                pass
        return mob


def wrapped_slide_tex(
    text: str,
    font_size: int,
    max_width: float,
    *,
    color=None,
    weight: str = "NORMAL",
) -> VGroup:
    """Word-wrap ``text`` into Computer Modern lines that fit ``max_width``."""
    from aos_manim_core import get_theme

    color = color if color is not None else get_theme().text_main
    words = (text or "").split()
    if not words:
        return VGroup(slide_tex(" ", font_size=font_size, color=color, weight=weight))
    sample = slide_tex("M", font_size=font_size, color=color, weight=weight)
    char_w = max(float(getattr(sample, "width", 0.0) or 0.04), 0.04)
    max_chars = max(int(max_width / char_w), 8)
    lines: list[str] = []
    current = ""
    for word in words:
        trial = (current + " " + word).strip()
        if current and len(trial) > max_chars:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    from manim import DOWN, LEFT

    mobs = [slide_tex(line, font_size=font_size, color=color, weight=weight) for line in lines]
    group = VGroup(*mobs).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
    if group.width > max_width and group.width > 0:
        group.scale(max_width / group.width)
    return group
