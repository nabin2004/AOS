from __future__ import annotations

from typing import Dict
from .palette import ThemeConfig, SemanticPalette, FontConfig


MODERN_DARK = ThemeConfig(
    name="modern_dark",
    is_dark=True,
    palette=SemanticPalette(
        primary="#3B82F6",           # Vibrant Blue
        secondary="#8B5CF6",         # Modern Purple
        accent="#F43F5E",            # Rose / Pink
        accent_secondary="#10B981",  # Emerald
        background="#090D16",        # Obsidian
        surface="#131B2E",           # Deep Slate
        surface_variant="#1E293B",   # Medium Slate
        border="#334155",
        text_main="#F8FAFC",
        text_muted="#94A3B8",
        success="#10B981",
        warning="#F59E0B",
        error="#EF4444",
        highlight_a="#FACC15",
        highlight_b="#06B6D4",
        node_color="#3B82F6",
        edge_color="#64748B",
    )
)

ACADEMIC_OXFORD = ThemeConfig(
    name="academic_oxford",
    is_dark=True,
    palette=SemanticPalette(
        primary="#38BDF8",           # Sky blue
        secondary="#E2B714",         # Oxford gold
        accent="#F87171",            # Soft crimson
        accent_secondary="#34D399",  # Sage green
        background="#0A1128",        # Deep oxford navy
        surface="#1C2541",           # Midnight navy
        surface_variant="#2D3A63",
        border="#3A506B",
        text_main="#FFFFFF",
        text_muted="#CBD5E1",
        success="#34D399",
        warning="#FBBF24",
        error="#F87171",
        highlight_a="#E2B714",
        highlight_b="#67E8F9",
        node_color="#38BDF8",
        edge_color="#475569",
    )
)

SOLARIZED_DARK = ThemeConfig(
    name="solarized_dark",
    is_dark=True,
    palette=SemanticPalette(
        primary="#268BD2",           # Blue
        secondary="#6C71C4",         # Violet
        accent="#D33682",            # Magenta
        accent_secondary="#2AA198",  # Cyan
        background="#002B36",        # Base03
        surface="#073642",           # Base02
        surface_variant="#586E75",   # Base01
        border="#657B83",            # Base00
        text_main="#93A1A1",         # Base1
        text_muted="#586E75",
        success="#859900",           # Green
        warning="#B58900",           # Yellow
        error="#DC322F",             # Red
        highlight_a="#CB4B16",       # Orange
        highlight_b="#2AA198",       # Cyan
        node_color="#268BD2",
        edge_color="#586E75",
    )
)

NORD = ThemeConfig(
    name="nord",
    is_dark=True,
    palette=SemanticPalette(
        primary="#88C0D0",           # Frost Cyan
        secondary="#81A1C1",         # Frost Blue
        accent="#B48EAD",            # Aurora Pink/Purple
        accent_secondary="#A3BE8C",  # Aurora Green
        background="#2E3440",        # Polar Night 0
        surface="#3B4252",           # Polar Night 1
        surface_variant="#434C5E",   # Polar Night 2
        border="#4C566A",            # Polar Night 3
        text_main="#ECEFF4",         # Snow Storm 3
        text_muted="#D8DEE9",        # Snow Storm 1
        success="#A3BE8C",           # Aurora Green
        warning="#EBCB8B",           # Aurora Yellow
        error="#BF616A",             # Aurora Red
        highlight_a="#D08770",       # Aurora Orange
        highlight_b="#5E81AC",       # Frost Deep Blue
        node_color="#88C0D0",
        edge_color="#4C566A",
    )
)

MINIMALIST_LIGHT = ThemeConfig(
    name="minimalist_light",
    is_dark=False,
    palette=SemanticPalette(
        primary="#2563EB",           # Royal Blue
        secondary="#7C3AED",         # Deep Violet
        accent="#DB2777",            # Vivid Pink
        accent_secondary="#059669",  # Deep Emerald
        background="#F8FAFC",        # Crisp Off-White
        surface="#FFFFFF",           # Pure White
        surface_variant="#F1F5F9",   # Light Slate
        border="#CBD5E1",            # Border Slate
        text_main="#0F172A",         # Deep Charcoal
        text_muted="#64748B",        # Muted Slate
        success="#16A34A",
        warning="#D97706",
        error="#DC2626",
        highlight_a="#CA8A04",
        highlight_b="#0891B2",
        node_color="#2563EB",
        edge_color="#94A3B8",
    )
)

CYBERPUNK = ThemeConfig(
    name="cyberpunk",
    is_dark=True,
    palette=SemanticPalette(
        primary="#00F0FF",           # Neon Cyan
        secondary="#7000FF",         # Neon Purple
        accent="#FF007F",            # Neon Pink
        accent_secondary="#00FF66",  # Neon Green
        background="#05050D",        # Pitch Black
        surface="#120D26",           # Dark Magenta
        surface_variant="#1F153D",
        border="#FF007F",
        text_main="#FFFFFF",
        text_muted="#9988AA",
        success="#00FF66",
        warning="#FFB800",
        error="#FF1F48",
        highlight_a="#FFE600",
        highlight_b="#00F0FF",
        node_color="#00F0FF",
        edge_color="#FF007F",
    )
)

THEME_PRESETS: Dict[str, ThemeConfig] = {
    "modern_dark": MODERN_DARK,
    "academic_oxford": ACADEMIC_OXFORD,
    "solarized_dark": SOLARIZED_DARK,
    "nord": NORD,
    "minimalist_light": MINIMALIST_LIGHT,
    "cyberpunk": CYBERPUNK,
}
