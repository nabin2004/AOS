"""2D ChessBoard VGroup with python-chess SVG pieces (drift-free)."""

from __future__ import annotations

from typing import Any

import chess
import numpy as np
from manim import BLACK, Scene, Square, Text, VGroup

from manim_chess.annotations import AnnotationMixin
from manim_chess.game import board_from_fen
from manim_chess.moves import animate_board_move
from manim_chess.pieces2d import piece_to_svg
from manim_chess.theme import BoardTheme


class ChessBoard(AnnotationMixin, VGroup):
    """Flat 2D chessboard with SVG pieces for educational Manim scenes."""

    def __init__(
        self,
        board: chess.Board | str | None = None,
        *,
        square_size: float = 0.8,
        theme: BoardTheme | None = None,
        flipped: bool = False,
        show_labels: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.board = board if isinstance(board, chess.Board) else board_from_fen(board)
        self.square_size = square_size
        self.theme = theme or BoardTheme.classic()
        self.flipped = flipped
        self.show_labels = show_labels

        self.squares = VGroup()
        self.square_mobs: dict[int, Square] = {}
        self.labels = VGroup()
        self.piece_mobs: dict[int, Any] = {}
        self.annotations = VGroup()

        self._build_squares()
        if show_labels:
            self._build_labels()
        self._place_pieces()
        self.add(self.annotations)

    # ------------------------------------------------------------------
    # Geometry — always use live square mobject centers (no drift)
    # ------------------------------------------------------------------
    def _display_file_rank(self, square: int) -> tuple[int, int]:
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        if self.flipped:
            return 7 - file, 7 - rank
        return file, rank

    def _local_offset(self, square: int) -> np.ndarray:
        file, rank = self._display_file_rank(square)
        x = (file - 3.5) * self.square_size
        y = (rank - 3.5) * self.square_size
        return np.array([x, y, 0.0])

    def square_center(self, square: int) -> np.ndarray:
        """World-space center of a square (tracks board moves/shifts)."""
        return self.square_mobs[square].get_center()

    def _build_squares(self) -> None:
        for sq in chess.SQUARES:
            true_file = chess.square_file(sq)
            true_rank = chess.square_rank(sq)
            light = (true_file + true_rank) % 2 == 1
            color = self.theme.light_square if light else self.theme.dark_square
            cell = Square(
                side_length=self.square_size,
                stroke_width=self.theme.square_stroke_width,
                stroke_color=BLACK,
            )
            cell.set_fill(color, opacity=1)
            cell.move_to(self._local_offset(sq))
            self.square_mobs[sq] = cell
            self.squares.add(cell)
        self.add(self.squares)

    def _build_labels(self) -> None:
        files = "abcdefgh"
        for i in range(8):
            file_idx = 7 - i if self.flipped else i
            rank_idx = 7 - i if self.flipped else i

            fx = (i - 3.5) * self.square_size
            fy = (-3.5) * self.square_size - self.square_size * 0.55
            fl = Text(files[file_idx], font_size=18, color=self.theme.label)
            fl.move_to([fx, fy, 0])
            self.labels.add(fl)

            rx = (-3.5) * self.square_size - self.square_size * 0.55
            ry = (i - 3.5) * self.square_size
            rl = Text(str(rank_idx + 1), font_size=18, color=self.theme.label)
            rl.move_to([rx, ry, 0])
            self.labels.add(rl)
        self.add(self.labels)

    def _make_piece(self, piece: chess.Piece):
        mob = piece_to_svg(piece)
        target = self.square_size * self.theme.piece_fill
        # Fit inside the square without stretching aspect ratio
        if mob.height > 0 and mob.width > 0:
            scale = min(target / mob.height, target / mob.width)
            mob.scale(scale)
        return mob

    def _place_pieces(self) -> None:
        for sq in chess.SQUARES:
            piece = self.board.piece_at(sq)
            if piece is None:
                continue
            mob = self._make_piece(piece)
            mob.move_to(self.square_center(sq))
            self.piece_mobs[sq] = mob
            self.add(mob)

    def snap_pieces(self) -> None:
        """Force every piece onto its square center (anti-drift)."""
        for sq, mob in self.piece_mobs.items():
            mob.move_to(self.square_center(sq))

    # ------------------------------------------------------------------
    # Piece accessors
    # ------------------------------------------------------------------
    def get_piece_at(self, square: int):
        return self.piece_mobs.get(square)

    def remove_piece(self, square: int):
        mob = self.piece_mobs.pop(square, None)
        if mob is not None:
            self.remove(mob)
        return mob

    def set_fen(self, fen: str) -> None:
        """Replace logical position and rebuild piece mobjects."""
        for mob in list(self.piece_mobs.values()):
            self.remove(mob)
        self.piece_mobs.clear()
        self.clear_annotations()
        self.board = chess.Board(fen)
        self._place_pieces()

    def set_orientation(self, flipped: bool) -> None:
        """Flip board perspective and rebuild squares/pieces/labels."""
        if flipped == self.flipped:
            return
        self.remove(*self.submobjects)
        self.flipped = flipped
        self.squares = VGroup()
        self.square_mobs = {}
        self.labels = VGroup()
        self.piece_mobs = {}
        self.annotations = VGroup()
        self._build_squares()
        if self.show_labels:
            self._build_labels()
        self._place_pieces()
        self.add(self.annotations)

    # ------------------------------------------------------------------
    # Animation
    # ------------------------------------------------------------------
    def animate_move(
        self,
        move: chess.Move | str,
        scene: Scene,
        run_time: float = 1.0,
        play_sfx: bool = True,
    ) -> chess.Move:
        """Animate a SAN / UCI / Move, including castle, EP, and promotion."""
        result = animate_board_move(
            board=self.board,
            piece_mobs=self.piece_mobs,
            square_center=self.square_center,
            make_piece=self._make_piece,
            add_mob=self.add,
            remove_mob=self.remove,
            scene=scene,
            move=move,
            run_time=run_time,
            play_sfx=play_sfx,
        )
        self.snap_pieces()
        return result

    def play_moves(
        self,
        moves: list[chess.Move | str],
        scene: Scene,
        run_time: float = 0.8,
        wait: float = 0.15,
    ) -> None:
        for m in moves:
            self.animate_move(m, scene=scene, run_time=run_time)
            if wait > 0:
                scene.wait(wait)
