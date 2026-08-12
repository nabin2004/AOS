"""2D fork lesson — board deliberately shifted to prove no piece drift."""

from manim import *

from manim_chess import BoardTheme, ChessBoard
import chess


class Demo2DFork(Scene):
    def construct(self):
        # White knight on e5 forks king g8 and queen d7 via Nf7.
        fen = "6k1/3q4/8/4N3/8/8/8/4K3 w - - 0 1"
        board = ChessBoard(fen, square_size=0.75, theme=BoardTheme.classic())
        # Off-center on purpose: square_center must track this shift.
        board.move_to(LEFT * 1.5 + UP * 0.3)
        self.play(FadeIn(board), run_time=1.0)

        board.highlight_square(chess.E5, color=YELLOW, opacity=0.4)
        board.arrow(chess.E5, chess.F7, color=GREEN)
        board.show_legal_moves(chess.E5)
        self.wait(0.8)
        board.clear_annotations()

        board.highlight_square(chess.F7, color=RED, opacity=0.35)
        board.animate_move("Nf7", scene=self, run_time=1.2)
        board.highlight_last_move()
        self.wait(1.0)
