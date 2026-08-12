"""Short PGN replay demo with arrows and highlights."""

from manim import *

from manim_chess import ChessBoard, load_pgn


SHORT_PGN = """
[Event "Demo"]
[Result "*"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 *
"""


class Demo2DPGN(Scene):
    def construct(self):
        chess_board = ChessBoard(square_size=0.7, show_labels=True)
        chess_board.move_to(ORIGIN)
        self.play(FadeIn(chess_board), run_time=0.8)

        moves = load_pgn(SHORT_PGN)
        for move in moves:
            from_sq, to_sq = move.from_square, move.to_square
            chess_board.clear_annotations()
            chess_board.highlight_square(from_sq, color=YELLOW, opacity=0.35)
            chess_board.arrow(from_sq, to_sq)
            self.wait(0.15)
            chess_board.animate_move(move, scene=self, run_time=0.7)
            chess_board.highlight_last_move()
            self.wait(0.2)

        self.wait(0.8)
