"""Compile Typst math to cached SVG on disk (Typst stays out of the animation layer)."""

from __future__ import annotations

import contextlib
import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path


def _cache_root() -> Path:
    base = os.environ.get("MOTIONGRAM_CACHE_HOME", "")
    if base:
        return Path(base).expanduser() / "typst"
    return Path.home() / ".cache" / "motiongram" / "typst"


def _typst_stub(source: str) -> str:
    s = source.strip()
    if s.startswith("#set") or s.startswith("#page"):
        return s
    return f"""#set page(width: auto, height: auto, margin: 2pt)
#set text(14pt)
$
{s}
$
"""


def _normalize_hex_rgb(fill_rgb_hex: str) -> str:
    h = fill_rgb_hex.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        return "FFFFFF"
    return h


def _subtitle_typst_document(
    body: str,
    *,
    page_width_pt: float,
    font_size_pt: float,
    fill_rgb_hex: str,
) -> str:
    s = body.strip()
    if s.startswith("#set") or s.startswith("#page"):
        return s
    hh = _normalize_hex_rgb(fill_rgb_hex)
    w = max(page_width_pt, 32.0)
    fs = max(font_size_pt, 6.0)
    return f"""#set page(width: {w}pt, height: auto, margin: 4pt, fill: none)
#set text({fs}pt, fill: rgb("#{hh}"))
#set par(justify: false)
#align(center)[
{s}
]
"""


def typst_cache_key(source: str, *, engine_marker: str = "motiongram_typst_v1") -> str:
    h = hashlib.sha256()
    h.update(engine_marker.encode())
    h.update(b"\n")
    h.update(source.encode())
    return h.hexdigest()


def subtitle_document_for_cache(
    body: str,
    *,
    page_width_pt: float,
    font_size_pt: float,
    fill_rgb_hex: str,
) -> str:
    """Full Typst source used for subtitle SVG caching (includes layout)."""
    return _subtitle_typst_document(
        body,
        page_width_pt=page_width_pt,
        font_size_pt=font_size_pt,
        fill_rgb_hex=fill_rgb_hex,
    )


def typst_subtitle_cache_key(
    body: str,
    *,
    page_width_pt: float,
    font_size_pt: float,
    fill_rgb_hex: str,
    engine_marker: str = "motiongram_subtitle_v1",
) -> str:
    doc = subtitle_document_for_cache(
        body,
        page_width_pt=page_width_pt,
        font_size_pt=font_size_pt,
        fill_rgb_hex=fill_rgb_hex,
    )
    return typst_cache_key(doc, engine_marker=engine_marker)


def cached_typst_svg_path(source: str, *, engine_marker: str = "motiongram_typst_v1") -> Path | None:
    """Return path to ``.svg`` compiled from ``source``, or ``None`` if ``typst`` is unavailable.

    Cached by :func:`typst_cache_key`. Idempotent: same source returns the same file.
    """
    if shutil.which("typst") is None:
        return None

    key = typst_cache_key(source, engine_marker=engine_marker)
    root = _cache_root()
    root.mkdir(parents=True, exist_ok=True)
    typ_path = root / f"{key}.typ"
    svg_path = root / f"{key}.svg"

    if svg_path.is_file():
        return svg_path

    typ_path.write_text(_typst_stub(source), encoding="utf-8")
    try:
        subprocess.run(
            ["typst", "compile", str(typ_path), str(svg_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        for p in (svg_path, typ_path):
            with contextlib.suppress(OSError):
                p.unlink(missing_ok=True)
        return None

    return svg_path if svg_path.is_file() else None


def cached_typst_subtitle_svg_path(
    body: str,
    *,
    page_width_pt: float,
    font_size_pt: float,
    fill_rgb_hex: str,
    engine_marker: str = "motiongram_subtitle_v1",
) -> Path | None:
    """Compile subtitle Typst to a cached SVG, or None if Typst is missing or compile fails."""
    if shutil.which("typst") is None:
        return None

    document = subtitle_document_for_cache(
        body,
        page_width_pt=page_width_pt,
        font_size_pt=font_size_pt,
        fill_rgb_hex=fill_rgb_hex,
    )
    key = typst_cache_key(document, engine_marker=engine_marker)
    root = _cache_root()
    root.mkdir(parents=True, exist_ok=True)
    typ_path = root / f"{key}.typ"
    svg_path = root / f"{key}.svg"

    if svg_path.is_file():
        return svg_path

    typ_path.write_text(document, encoding="utf-8")
    try:
        subprocess.run(
            ["typst", "compile", str(typ_path), str(svg_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        for p in (svg_path, typ_path):
            with contextlib.suppress(OSError):
                p.unlink(missing_ok=True)
        return None

    return svg_path if svg_path.is_file() else None
