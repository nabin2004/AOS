from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Union, Generator, Optional
from .palette import ThemeConfig, SemanticPalette, FontConfig
from .presets import THEME_PRESETS, MODERN_DARK


class ThemeManager:
    """Manages active theme state across all AOS Manim plugins."""
    _instance: Optional[ThemeManager] = None

    def __init__(self) -> None:
        self._themes: Dict[str, ThemeConfig] = dict(THEME_PRESETS)
        self._active_theme: ThemeConfig = MODERN_DARK

    @classmethod
    def get_instance(cls) -> ThemeManager:
        if cls._instance is None:
            cls._instance = ThemeManager()
        return cls._instance

    @property
    def active_theme(self) -> ThemeConfig:
        return self._active_theme

    def set_theme(self, theme: Union[str, ThemeConfig]) -> ThemeConfig:
        if isinstance(theme, str):
            if theme not in self._themes:
                raise ValueError(
                    f"Unknown theme '{theme}'. Available themes: {list(self._themes.keys())}"
                )
            self._active_theme = self._themes[theme]
        elif isinstance(theme, ThemeConfig):
            self._themes[theme.name] = theme
            self._active_theme = theme
        else:
            raise TypeError(f"Expected str or ThemeConfig, got {type(theme)}")
        return self._active_theme

    def register_theme(self, name: str, theme: ThemeConfig) -> None:
        self._themes[name] = theme

    def get_theme(self, name: Optional[str] = None) -> ThemeConfig:
        if name is None:
            return self._active_theme
        if name not in self._themes:
            raise ValueError(f"Theme '{name}' not found.")
        return self._themes[name]

    def list_themes(self) -> list[str]:
        return list(self._themes.keys())

    def load_theme_from_json(self, filepath: Union[str, Path]) -> ThemeConfig:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Theme file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        theme = ThemeConfig.from_dict(data)
        self.register_theme(theme.name, theme)
        return theme


# Global convenience API
def get_theme(name: Optional[str] = None) -> ThemeConfig:
    """Retrieve current active theme or a specific registered theme."""
    return ThemeManager.get_instance().get_theme(name)


def set_theme(theme: Union[str, ThemeConfig]) -> ThemeConfig:
    """Set the active global theme."""
    return ThemeManager.get_instance().set_theme(theme)


@contextmanager
def use_theme(theme: Union[str, ThemeConfig]) -> Generator[ThemeConfig, None, None]:
    """Context manager to temporarily execute within a specific theme scope."""
    manager = ThemeManager.get_instance()
    previous = manager.active_theme
    try:
        yield manager.set_theme(theme)
    finally:
        manager.set_theme(previous)
