"""
AOS Manim Core: Foundational Protocol, Theme Engine, Manifest System, and Invariant Validators.
"""

from .theme import (
    SemanticPalette,
    FontConfig,
    ThemeConfig,
    MODERN_DARK,
    ACADEMIC_OXFORD,
    SOLARIZED_DARK,
    NORD,
    MINIMALIST_LIGHT,
    CYBERPUNK,
    THEME_PRESETS,
    ThemeManager,
    get_theme,
    set_theme,
    use_theme,
)

from .manifest import (
    PluginManifest,
    Capability,
    BackendSpec,
    ValidationRule,
    ManifestBuilder,
)

from .validators import (
    BaseValidator,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    CanvasBoundsValidator,
    CollisionValidator,
    NumericalToleranceValidator,
    SymbolicEquivalenceValidator,
)

from .registry import (
    PluginRegistry,
    register_plugin,
    get_plugin_registry,
)

from .narration import (
    Cue,
    CueAction,
    CueResolver,
    Cueable,
    NarrationScript,
    apply_standard_cue,
    bind_authored_script,
    inject_bookmarks,
    is_cueable,
    parse_bookmark_marks,
    play_script,
    wait_for_mark,
)

__version__ = "0.1.0"

__all__ = [
    # Theming
    "SemanticPalette",
    "FontConfig",
    "ThemeConfig",
    "MODERN_DARK",
    "ACADEMIC_OXFORD",
    "SOLARIZED_DARK",
    "NORD",
    "MINIMALIST_LIGHT",
    "CYBERPUNK",
    "THEME_PRESETS",
    "ThemeManager",
    "get_theme",
    "set_theme",
    "use_theme",
    # Manifest
    "PluginManifest",
    "Capability",
    "BackendSpec",
    "ValidationRule",
    "ManifestBuilder",
    # Validators
    "BaseValidator",
    "ValidationResult",
    "ValidationIssue",
    "ValidationSeverity",
    "CanvasBoundsValidator",
    "CollisionValidator",
    "NumericalToleranceValidator",
    "SymbolicEquivalenceValidator",
    # Registry
    "PluginRegistry",
    "register_plugin",
    "get_plugin_registry",
    # Narration / cues
    "Cue",
    "CueAction",
    "CueResolver",
    "Cueable",
    "NarrationScript",
    "apply_standard_cue",
    "bind_authored_script",
    "inject_bookmarks",
    "is_cueable",
    "parse_bookmark_marks",
    "play_script",
    "wait_for_mark",
]
