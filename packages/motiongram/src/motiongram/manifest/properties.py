"""Normalize YAML property conveniences into Node constructor kwargs."""

from __future__ import annotations

from typing import Any

from motiongram.manifest.errors import ManifestValidationError


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert ``#RRGGBB`` or ``#RGB`` to an RGB tuple."""
    s = hex_color.strip()
    if not s.startswith("#"):
        raise ManifestValidationError(
            f"background must be hex color like #21252b, got {hex_color!r}"
        )
    body = s[1:]
    if len(body) == 3:
        body = "".join(ch * 2 for ch in body)
    if len(body) != 6:
        raise ManifestValidationError(f"invalid hex color: {hex_color!r}")
    try:
        r = int(body[0:2], 16)
        g = int(body[2:4], 16)
        b = int(body[4:6], 16)
    except ValueError as exc:
        raise ManifestValidationError(f"invalid hex color: {hex_color!r}") from exc
    return r, g, b


def normalize_element_properties(raw: dict[str, Any]) -> dict[str, Any]:
    """Apply aliases: ``position`` → ``x``/``y``, ``typst`` → ``typst_source``."""
    props = dict(raw)
    if "position" in props:
        pos = props.pop("position")
        if not isinstance(pos, list | tuple) or len(pos) != 2:
            raise ManifestValidationError(f"position must be [x, y], got {pos!r}")
        props.setdefault("x", float(pos[0]))
        props.setdefault("y", float(pos[1]))
    if "typst" in props and "typst_source" not in props:
        props["typst_source"] = props.pop("typst")
    if "latex" in props and "typst_source" not in props:
        raise ManifestValidationError(
            "MathExpr uses Typst, not LaTeX — use properties.typst or typst_source"
        )
    return props
