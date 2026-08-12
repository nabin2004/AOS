"""FEN / SAN / UCI / PGN helpers for educational chess animations."""

from __future__ import annotations

import io
from collections.abc import Iterator, Sequence
from pathlib import Path

import chess
import chess.pgn


def board_from_fen(fen: str | None = None) -> chess.Board:
    """Create a board from FEN, or a starting position if fen is None."""
    if fen is None:
        return chess.Board()
    return chess.Board(fen)


def parse_move(board: chess.Board, move: chess.Move | str) -> chess.Move:
    """Parse a Move, SAN, or UCI string against the current board."""
    if isinstance(move, chess.Move):
        return move
    text = move.strip()
    try:
        return board.parse_san(text)
    except ValueError:
        pass
    try:
        parsed = chess.Move.from_uci(text)
    except ValueError as exc:
        raise ValueError(f"Cannot parse move {text!r}") from exc
    if parsed not in board.legal_moves:
        raise ValueError(f"Illegal move {text!r} in position {board.fen()}")
    return parsed


def load_pgn(source: str | Path) -> list[chess.Move]:
    """
    Load the main line of the first game from a PGN string or file path.

    Returns the list of moves (does not push onto a board).
    """
    path = Path(source)
    if path.exists() and path.is_file():
        text = path.read_text(encoding="utf-8")
    else:
        text = str(source)

    game = chess.pgn.read_game(io.StringIO(text))
    if game is None:
        return []
    return list(game.mainline_moves())


def iter_replay(
    start: chess.Board | str | None,
    moves: Sequence[chess.Move | str],
) -> Iterator[tuple[chess.Board, chess.Move]]:
    """
    Yield (board_before_move, move) for each move, pushing as we go.

    The caller sees the board *before* each move is applied; after the
    generator finishes, the working board has all moves pushed.
    """
    board = start if isinstance(start, chess.Board) else board_from_fen(start)
    for raw in moves:
        move = parse_move(board, raw)
        yield board.copy(stack=False), move
        board.push(move)


def moves_from_san(board: chess.Board, sans: Sequence[str]) -> list[chess.Move]:
    """Parse a sequence of SAN moves from a starting board (does not mutate)."""
    work = board.copy(stack=False)
    out: list[chess.Move] = []
    for san in sans:
        move = parse_move(work, san)
        out.append(move)
        work.push(move)
    return out
