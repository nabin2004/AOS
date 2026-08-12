"""2D SVG chess pieces via python-chess chess.svg.piece."""

from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile

import chess
import chess.svg
from manim import SVGMobject

_SVG_CACHE_DIR = Path(tempfile.gettempdir()) / "manim_chess_svg_cache"
_SVG_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_PATH_CACHE: dict[tuple[str, int], Path] = {}


def _svg_path_for(piece: chess.Piece, size: int = 90) -> Path:
    key = (piece.symbol(), size)
    cached = _PATH_CACHE.get(key)
    if cached is not None and cached.exists():
        return cached

    digest = hashlib.sha1(f"{piece.symbol()}-{size}".encode()).hexdigest()[:12]
    path = _SVG_CACHE_DIR / f"piece_{digest}.svg"
    if not path.exists():
        path.write_text(chess.svg.piece(piece, size=size), encoding="utf-8")
    _PATH_CACHE[key] = path
    return path


def piece_to_svg(piece: chess.Piece, *, size: int = 90) -> SVGMobject:
    """
    Return an unscaled SVGMobject for a chess piece (cached on disk).

    Callers should size with scale_to_fit_height / scale_to_fit_width against
    the board square so glyphs stay centered and do not drift.
    """
    return SVGMobject(str(_svg_path_for(piece, size=size)))


def clear_svg_cache() -> None:
    """Clear in-memory SVG path cache (files on disk remain)."""
    _PATH_CACHE.clear()
