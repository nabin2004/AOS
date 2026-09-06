"""
AOS Manim Slides: Presentation orchestration and slide templates for Manim.
"""

from .scene import SlideScene, VoiceoverSlideScene, MarkdownVoiceoverDeck
from .layouts.base_slide import Slide
from .layouts.templates import (
    TitleSlide,
    SectionSlide,
    ContentSlide,
    TwoColumnSlide,
    QuizSlide,
)
from .components.card import Card, Badge, CalloutBox, Rectangle
from .transitions.transitions import (
    fade_transition,
    wipe_transition,
    zoom_slide_transition,
)
from .validators.slide_validator import SlideOverflowValidator
from .document import (
    SlideSpec,
    Presentation,
    Paragraph,
    Heading,
    Equation,
    CodeBlock,
    Callout,
    DiagramRef,
    AnimationSlot,
    ListBlock,
    parse_markdown,
    parse_slide_markdown,
)
from .layout import (
    LayoutEngine,
    LayoutReport,
    VStack,
    HStack,
    Grid,
    Overlay,
    Center,
    Align,
    Padding,
    Box,
    Rect,
)
from .diagrams import (
    build_animation,
    build_diagram,
    register_animation,
    register_diagram,
    DiagramNotFoundError,
)
from .narration import assign_content_ids, auto_script_from_spec, script_for_slide
from .lecture import (
    BrandingIntro,
    BulletBoard,
    CodeReveal,
    CopyExplain,
    DisclaimerCard,
    QuoteCard,
    TwoColumnBullets,
    play_bullets,
    play_column_rows,
)

__version__ = "0.1.0"

__all__ = [
    "SlideScene",
    "VoiceoverSlideScene",
    "MarkdownVoiceoverDeck",
    "Slide",
    "TitleSlide",
    "SectionSlide",
    "ContentSlide",
    "TwoColumnSlide",
    "QuizSlide",
    "Card",
    "Badge",
    "CalloutBox",
    "Rectangle",
    "fade_transition",
    "wipe_transition",
    "zoom_slide_transition",
    "SlideOverflowValidator",
    "SlideSpec",
    "Presentation",
    "Paragraph",
    "Heading",
    "Equation",
    "CodeBlock",
    "Callout",
    "DiagramRef",
    "AnimationSlot",
    "ListBlock",
    "parse_markdown",
    "parse_slide_markdown",
    "LayoutEngine",
    "LayoutReport",
    "VStack",
    "HStack",
    "Grid",
    "Overlay",
    "Center",
    "Align",
    "Padding",
    "Box",
    "Rect",
    "build_diagram",
    "build_animation",
    "register_diagram",
    "register_animation",
    "DiagramNotFoundError",
    "assign_content_ids",
    "auto_script_from_spec",
    "script_for_slide",
    "BrandingIntro",
    "BulletBoard",
    "CodeReveal",
    "CopyExplain",
    "DisclaimerCard",
    "QuoteCard",
    "TwoColumnBullets",
    "play_bullets",
    "play_column_rows",
]
