"""
AOS Manim Beamer: LaTeX Beamer presentation engine for Manim.
"""

from .components.block import Block, AlertBlock, ExampleBlock
from .components.frame import BeamerFrame
from .components.columns import BeamerColumns, BeamerColumn
from .engine.presentation import BeamerPresentation
from .validators.beamer_validators import BeamerFrameOverflowValidator
from .templates import BeamerBulletFrame, BeamerQuoteFrame

__version__ = "0.1.0"

__all__ = [
    "Block",
    "AlertBlock",
    "ExampleBlock",
    "BeamerFrame",
    "BeamerColumns",
    "BeamerColumn",
    "BeamerPresentation",
    "BeamerFrameOverflowValidator",
    "BeamerBulletFrame",
    "BeamerQuoteFrame",
]
