"""EduClaw ASCII logo."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TextIO


PROJECT_ROOT = Path(__file__).resolve().parent.parent

LOGO_CANDIDATES = [
    PROJECT_ROOT / "assests" / "ascii-logo.txt",
    PROJECT_ROOT / "assets" / "ascii-logo.txt",
    Path(__file__).resolve().parent / "assests" / "ascii-logo.txt",
    Path(__file__).resolve().parent / "assets" / "ascii-logo.txt",
    Path("C:/Users/nabin/Desktop/myall/AOS/apps/educlaw/assests/ascii-logo.txt"),
]


def load_logo() -> str:
    """Load the EduClaw ASCII logo."""
    for candidate in LOGO_CANDIDATES:
        if candidate.exists():
            try:
                return candidate.read_text(encoding="utf-8").rstrip()
            except OSError:
                continue
    return ""


def play_logo(stream: TextIO | None = None) -> bool:
    """
    Play the EduClaw ASCII logo.

    Returns:
        True if the logo was displayed.
        False if the logo could not be loaded.
    """

    output = stream or sys.stdout

    logo = load_logo()

    if not logo:
        return False

    try:
        from terminaltexteffects.effects.effect_print import Print
    except ImportError:
        # terminaltexteffects isn't installed.
        # Still show the logo normally.
        print(logo, file=output)
        return True

    try:
        effect = Print(logo)

        with effect.terminal_output() as terminal:
            for frame in effect:
                terminal.print(frame)

        return True

    except Exception:
        # If animation fails, fall back to normal printing.
        print(logo, file=output)
        return True


if __name__ == "__main__":
    # Allows:
    #
    #   python -m educlaw.logo
    #
    # for testing.
    if not play_logo():
        print(f"Logo not found: {LOGO_PATH}")
        raise SystemExit(1)