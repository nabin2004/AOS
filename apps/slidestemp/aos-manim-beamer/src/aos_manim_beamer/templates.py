from __future__ import annotations

from typing import Optional, Sequence

from aos_manim_core import ThemeConfig
from aos_manim_slides.lecture import BulletBoard, QuoteCard

from .components.frame import BeamerFrame


class BeamerBulletFrame(BeamerFrame):
    """Beamer chrome plus sequential bullet reveal."""

    def __init__(
        self,
        title: str,
        items: Sequence[str],
        subtitle: Optional[str] = None,
        section: Optional[str] = None,
        theme: Optional[ThemeConfig] = None,
        font_size: int = 32,
        **kwargs,
    ) -> None:
        super().__init__(title=title, subtitle=subtitle, section=section, theme=theme, **kwargs)
        self.board = BulletBoard(title, list(items), theme=self.theme, font_size=font_size, show_chrome=False)
        self.board.move_to(self.get_content_center())
        self.add_content(self.board)

    def play_on(self, scene) -> None:
        for i in range(len(self.board.bullet_mobs)):
            self.board.play_item(scene, i)


class BeamerQuoteFrame(BeamerFrame):
    """Beamer chrome plus a quote card in the content rect."""

    def __init__(
        self,
        title: str,
        quote: str,
        author: str = "",
        subtitle: Optional[str] = None,
        section: Optional[str] = None,
        theme: Optional[ThemeConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(title=title, subtitle=subtitle, section=section, theme=theme, **kwargs)
        self.card = QuoteCard(quote, author=author, theme=self.theme, font_size=34)
        self.card.scale(0.9)
        self.card.move_to(self.get_content_center())
        self.add_content(self.card)

    def play_on(self, scene) -> None:
        self.card.play_on(scene)
