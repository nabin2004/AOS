"""manim-chess: educational 2D chess boards for Manim (python-chess SVG pieces)."""

from manim_chess.board import ChessBoard
from manim_chess.game import board_from_fen, iter_replay, load_pgn, moves_from_san, parse_move
from manim_chess.pieces2d import piece_to_svg
from manim_chess.sfx import play_chess_sfx, sfx_for_move
from manim_chess.theme import BoardTheme

__all__ = [
    "BoardTheme",
    "ChessBoard",
    "board_from_fen",
    "iter_replay",
    "load_pgn",
    "moves_from_san",
    "parse_move",
    "piece_to_svg",
    "play_chess_sfx",
    "sfx_for_move",
]
