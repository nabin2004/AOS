"""2D annotation helpers for ChessBoard (highlights, arrows, attacks)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import chess
import numpy as np
from manim import BLUE_E, Arrow, Circle, Dot, Square, VGroup

if TYPE_CHECKING:
    from manim_chess.theme import BoardTheme


class AnnotationMixin:
    """Highlights, arrows, attacks, and legal-move dots."""

    board: chess.Board
    theme: BoardTheme
    square_size: float
    annotations: VGroup
    square_mobs: dict[int, Square]
    flipped: bool

    def square_center(self, square: int) -> np.ndarray:  # pragma: no cover
        raise NotImplementedError

    def highlight_square(
        self,
        square: int,
        color: str | None = None,
        opacity: float = 0.45,
    ) -> Square:
        """Add a filled overlay on a square (same size as the cell)."""
        color = color or self.theme.highlight
        cell = self.square_mobs[square]
        hl = Square(side_length=self.square_size * 0.98)
        hl.set_fill(color, opacity=opacity)
        hl.set_stroke(width=0)
        hl.move_to(cell.get_center())
        self.annotations.add(hl)
        self.add(hl)
        return hl

    def highlight_squares(
        self,
        squares: list[int] | chess.SquareSet,
        color: str | None = None,
        opacity: float = 0.45,
    ) -> VGroup:
        group = VGroup()
        for sq in squares:
            group.add(self.highlight_square(int(sq), color=color, opacity=opacity))
        return group

    def highlight_last_move(self, move: chess.Move | None = None) -> VGroup:
        """Highlight from/to of the last move (or a provided move)."""
        if move is None:
            if not self.board.move_stack:
                return VGroup()
            move = self.board.peek()
        group = VGroup()
        for sq in (move.from_square, move.to_square):
            true_file = chess.square_file(sq)
            true_rank = chess.square_rank(sq)
            light = (true_file + true_rank) % 2 == 1
            color = self.theme.lastmove_light if light else self.theme.lastmove_dark
            group.add(self.highlight_square(sq, color=color, opacity=0.55))
        return group

    def arrow(
        self,
        from_square: int,
        to_square: int,
        color: str | None = None,
        buff: float = 0.12,
        stroke_width: float = 6,
    ) -> Arrow:
        """Draw an arrow between two squares (scene-accurate centers)."""
        color = color or self.theme.arrow
        start = self.square_center(from_square)
        end = self.square_center(to_square)
        arr = Arrow(
            start,
            end,
            buff=buff,
            color=color,
            stroke_width=stroke_width,
            max_tip_length_to_length_ratio=0.18,
        )
        self.annotations.add(arr)
        self.add(arr)
        return arr

    def show_attacks(self, square: int, opacity: float = 0.35) -> VGroup:
        """Highlight squares attacked by the piece on `square` (board.attacks)."""
        if self.board.piece_at(square) is None:
            return VGroup()
        attacked = self.board.attacks(square)
        return self.highlight_squares(
            attacked, color=self.theme.attack_fill, opacity=opacity
        )

    def show_legal_moves(self, square: int, opacity: float = 0.55) -> VGroup:
        """Show dots (quiet) / rings (captures) for legal moves from square."""
        group = VGroup()
        if self.board.piece_at(square) is None:
            return group
        for move in self.board.legal_moves:
            if move.from_square != square:
                continue
            target = move.to_square
            is_capture = self.board.is_capture(move)
            center = self.square_center(target)
            if is_capture:
                ring = Circle(
                    radius=self.square_size * 0.38,
                    color=self.theme.capture_hint,
                    stroke_width=4,
                    fill_opacity=0,
                )
                ring.move_to(center)
                group.add(ring)
            else:
                dot = Dot(
                    point=center,
                    radius=self.square_size * 0.12,
                    color=self.theme.legal_move or BLUE_E,
                    fill_opacity=opacity,
                )
                group.add(dot)
        self.annotations.add(group)
        self.add(group)
        return group

    def clear_annotations(self) -> None:
        """Remove all highlight/arrow/legal-move overlays."""
        for mob in list(self.annotations):
            self.remove(mob)
        self.annotations = VGroup()
        self.add(self.annotations)
