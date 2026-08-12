"""Chess move sound effects packed with manim-chess."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from manim import Scene

SOUNDS_DIR = Path(__file__).resolve().parent / "sounds"

SfxKind = Literal["move", "capture", "castle", "check", "promote", "notify", "end"]

_FILES: dict[SfxKind, str] = {
    "move": "move-self.mp3",
    "capture": "capture.mp3",
    "castle": "castle.mp3",
    "check": "move-check.mp3",
    "promote": "promote.mp3",
    "notify": "notify.mp3",
    # Prefer converted wav/mp3; fall back to notify if webm unsupported
    "end": "game-end.mp3",
}


def sound_path(kind: SfxKind) -> Path:
    name = _FILES[kind]
    path = SOUNDS_DIR / name
    if path.exists():
        return path
    if kind == "end":
        webm = SOUNDS_DIR / "game-end.webm"
        if webm.exists():
            return webm
        return SOUNDS_DIR / _FILES["notify"]
    raise FileNotFoundError(f"Missing chess SFX: {path}")


def play_chess_sfx(scene: Scene, kind: SfxKind, gain: float = 0.0) -> None:
    """Attach a packaged chess SFX to the current scene timeline."""
    path = sound_path(kind)
    if not path.exists():
        return
    try:
        scene.add_sound(str(path), time_offset=0, gain=gain)
    except Exception:
        # Manim/cairo may reject some containers; fail soft
        if kind != "notify":
            try:
                scene.add_sound(str(sound_path("notify")), time_offset=0, gain=gain)
            except Exception:
                pass


def sfx_for_move(
    *,
    is_capture: bool,
    is_castle: bool,
    is_check: bool,
    is_promotion: bool,
) -> SfxKind:
    """Pick the highest-priority SFX for a completed move."""
    if is_promotion:
        return "promote"
    if is_castle:
        return "castle"
    if is_check:
        return "check"
    if is_capture:
        return "capture"
    return "move"
