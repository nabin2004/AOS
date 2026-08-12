"""Move animation helpers for 2D ChessBoard."""

from __future__ import annotations

from typing import Any, Callable

import chess
from manim import FadeIn, FadeOut, Scene

from manim_chess.game import parse_move
from manim_chess.sfx import play_chess_sfx, sfx_for_move


def resolve_move(board: chess.Board, move: chess.Move | str) -> chess.Move:
    return parse_move(board, move)


def animate_board_move(
    *,
    board: chess.Board,
    piece_mobs: dict[int, Any],
    square_center: Callable[[int], Any],
    make_piece: Callable[[chess.Piece], Any],
    add_mob: Callable[[Any], None],
    remove_mob: Callable[[Any], None],
    scene: Scene,
    move: chess.Move | str,
    run_time: float = 1.0,
    play_sfx: bool = True,
) -> chess.Move:
    """
    Animate a legal chess move including castling, en passant, and promotion.

    Mutates `board` and `piece_mobs` in place. Always snaps pieces to
    `square_center` after animation so shifted boards never drift.
    """
    resolved = resolve_move(board, move)
    if not board.is_legal(resolved):
        raise ValueError(f"Illegal move: {resolved.uci()}")

    is_castle = board.is_castling(resolved)
    is_en_passant = board.is_en_passant(resolved)
    is_capture = board.is_capture(resolved)
    promotion = resolved.promotion

    from_sq = resolved.from_square
    to_sq = resolved.to_square
    piece_mob = piece_mobs.get(from_sq)
    if piece_mob is None:
        raise ValueError(f"No piece mobject on {chess.square_name(from_sq)}")

    fade_targets: list[Any] = []
    if is_en_passant:
        capture_sq = to_sq + (-8 if board.turn == chess.WHITE else 8)
        captured_mob = piece_mobs.pop(capture_sq, None)
        if captured_mob is not None:
            fade_targets.append(captured_mob)
    elif is_capture:
        captured_mob = piece_mobs.pop(to_sq, None)
        if captured_mob is not None:
            fade_targets.append(captured_mob)

    rook_from: int | None = None
    rook_to: int | None = None
    rook_mob = None
    if is_castle:
        if chess.square_file(to_sq) > chess.square_file(from_sq):
            rook_from = from_sq + 3
            rook_to = from_sq + 1
        else:
            rook_from = from_sq - 4
            rook_to = from_sq - 1
        rook_mob = piece_mobs.get(rook_from)

    board.push(resolved)
    if play_sfx:
        play_chess_sfx(
            scene,
            sfx_for_move(
                is_capture=is_capture or is_en_passant,
                is_castle=is_castle,
                is_check=board.is_check(),
                is_promotion=promotion is not None,
            ),
        )

    anims = []
    if fade_targets:
        anims.extend(FadeOut(m) for m in fade_targets)

    target_pos = square_center(to_sq)
    anims.append(piece_mob.animate.move_to(target_pos))
    piece_mobs.pop(from_sq, None)
    piece_mobs[to_sq] = piece_mob

    if rook_mob is not None and rook_from is not None and rook_to is not None:
        anims.append(rook_mob.animate.move_to(square_center(rook_to)))
        piece_mobs.pop(rook_from, None)
        piece_mobs[rook_to] = rook_mob

    if anims:
        scene.play(*anims, run_time=run_time)
    for m in fade_targets:
        remove_mob(m)

    # Snap to live square centers (fixes floating-point / shift drift)
    piece_mob.move_to(square_center(to_sq))
    if rook_mob is not None and rook_to is not None:
        rook_mob.move_to(square_center(rook_to))

    if promotion is not None:
        color = board.piece_at(to_sq).color if board.piece_at(to_sq) else chess.WHITE
        new_piece = chess.Piece(promotion, color)
        old = piece_mobs.pop(to_sq, None)
        if old is not None:
            scene.play(FadeOut(old), run_time=run_time * 0.35)
            remove_mob(old)
        new_mob = make_piece(new_piece)
        new_mob.move_to(square_center(to_sq))
        add_mob(new_mob)
        piece_mobs[to_sq] = new_mob
        scene.play(FadeIn(new_mob), run_time=run_time * 0.35)
        new_mob.move_to(square_center(to_sq))

    return resolved
