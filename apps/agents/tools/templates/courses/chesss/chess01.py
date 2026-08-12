"""Course demo: fork lesson using manim_chess + AOS voiceover."""

from manim import *
from manim_voiceover import VoiceoverScene
import chess
from tools.aos_speech_service import AOSSpeechService
from manim_chess import ChessBoard, BoardTheme


class IntroScene(VoiceoverScene):
    def construct(self):
        self.set_speech_service(
            AOSSpeechService(
                voice="alba",
                cache_dir="voiceover_cache",
            )
        )

        fen = "6k1/3q4/8/4N3/8/8/8/4K3 w - - 0 1"
        chess_board = ChessBoard(fen, square_size=0.8, theme=BoardTheme.classic())
        chess_board.move_to(ORIGIN)

        self.play(FadeIn(chess_board, run_time=1.5))
        self.wait(0.5)

        with self.voiceover(
            text="Watch the knight on e five. It can jump to f seven with a powerful fork."
        ):
            chess_board.highlight_square(chess.E5, color=YELLOW, opacity=0.4)
            chess_board.arrow(chess.E5, chess.F7, color=RED)
            self.wait(0.5)

        with self.voiceover(
            text="White plays knight to f seven, attacking the king and the queen at the same time."
        ):
            chess_board.clear_annotations()
            chess_board.animate_move("Nf7", scene=self, run_time=1.5)
            chess_board.highlight_last_move()

        with self.voiceover(
            text="This is a classic fork — black cannot defend both pieces."
        ):
            self.wait(0.5)

        self.wait(1.5)
