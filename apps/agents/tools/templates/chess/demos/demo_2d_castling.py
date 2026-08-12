"""Castling demo on a shifted board (anti-drift + special move)."""

from manim import *

from manim_chess import ChessBoard
import chess


class Demo2DCastling(Scene):
    def construct(self):
        fen = "4k3/8/8/8/8/8/8/4K2R w K - 0 1"
        board = ChessBoard(fen, square_size=0.8, show_labels=True)
        board.shift(RIGHT * 1.2 + DOWN * 0.4)
        self.play(FadeIn(board), run_time=0.8)

        board.highlight_square(chess.E1, opacity=0.4)
        board.arrow(chess.E1, chess.G1)
        self.wait(0.3)
        board.clear_annotations()

        board.animate_move("O-O", scene=self, run_time=1.2)
        board.highlight_last_move()
        self.wait(1.0)
