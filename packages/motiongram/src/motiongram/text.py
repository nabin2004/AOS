"""Text, math (Typst), and syntax-highlighted code blocks."""

from __future__ import annotations

from dataclasses import dataclass

try:
    from pygments.token import Token
except (ImportError, ModuleNotFoundError):
    class _TokenMeta(type):
        def __getattr__(cls, name: str) -> Any:
            return cls

    class Token(metaclass=_TokenMeta):
        pass

from motiongram.canvas import Canvas
from motiongram.core import Node

_TOKEN_COLORS: dict[type, str] = {
    Token.Keyword: "#C678DD",
    Token.Keyword.Namespace: "#C678DD",
    Token.Keyword.Type: "#E5C07B",
    Token.Name.Function: "#61AFEF",
    Token.Name.Class: "#E5C07B",
    Token.Name.Builtin: "#61AFEF",
    Token.Name.Decorator: "#61AFEF",
    Token.String: "#98C379",
    Token.Literal.String: "#98C379",
    Token.Number: "#D19A66",
    Token.Literal.Number: "#D19A66",
    Token.Operator: "#56B6C2",
    Token.Punctuation: "#ABB2BF",
    Token.Comment: "#5C6370",
    Token.Comment.Single: "#5C6370",
    Token.Comment.Multiline: "#5C6370",
}


def _token_color(tok_type: type) -> str:
    """Map a Pygments token type to a hex color (One Dark inspired palette)."""
    t: type | None = tok_type
    while t is not None:
        if t in _TOKEN_COLORS:
            return _TOKEN_COLORS[t]
        t = getattr(t, "parent", None)
    return "#ABB2BF"


@dataclass(slots=True)
class Text(Node):
    """Plain text label."""

    content: str = ""
    font_size: float = 24.0
    color: str = "#FFFFFF"

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        """Rasterize text via Skia."""
        draw_text = getattr(canvas, "draw_text", None)
        if draw_text is not None and self.content:
            draw_text(self.content, px, py, self.font_size, self.color)


@dataclass(slots=True)
class MathExpr(Node):
    """Mathematical expression rendered via Typst to cached SVG."""

    typst_source: str = ""
    font_size: float = 28.0
    color: str = "#FFFFFF"

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        """Typst → cached SVG; Skia canvases implement ``draw_svg_bytes``."""
        if not self.typst_source.strip():
            return
        from motiongram.typst_cache import cached_typst_svg_path

        svg_path = cached_typst_svg_path(self.typst_source)
        if svg_path is None:
            return
        data = svg_path.read_bytes()
        place = getattr(canvas, "draw_svg_bytes", None)
        if place is not None:
            scale = max(self.font_size, 1.0) / 28.0
            place(data, px, py, scale)


@dataclass(slots=True)
class CodeBlock(Node):
    """Source code with Pygments highlighting."""

    code: str = ""
    language: str = "python"
    font_size: float = 14.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        """Tokenize with Pygments and draw each token in its highlight color."""
        draw_text = getattr(canvas, "draw_text", None)
        if draw_text is None or not self.code:
            return

        from pygments import lex
        from pygments.lexers import get_lexer_by_name

        lexer = get_lexer_by_name(self.language, stripall=True)
        line_height = self.font_size * 1.4
        cursor_x = px
        cursor_y = py

        for tok_type, tok_value in lex(self.code, lexer):
            color = _token_color(tok_type)
            for ch in tok_value:
                if ch == "\n":
                    cursor_x = px
                    cursor_y += line_height
                else:
                    draw_text(
                        ch,
                        cursor_x,
                        cursor_y,
                        self.font_size,
                        color,
                        font_family="monospace",
                    )
                    cursor_x += self.font_size * 0.6
