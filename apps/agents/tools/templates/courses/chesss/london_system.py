"""London System — full VoiceoverScene lecture (slides + board + SFX + bookmarks).

Render from apps/agents:
  uv run manim -ql tools/templates/courses/chesss/london_system.py LondonSystemLecture
"""

from __future__ import annotations

import chess
from manim import *
from manim_voiceover import VoiceoverScene

from tools.aos_speech_service import AOSSpeechService
from manim_chess import BoardTheme, ChessBoard, play_chess_sfx


# ---------------------------------------------------------------------------
# Slide helpers (university-style, dark board)
# ---------------------------------------------------------------------------

BG = "#1a1a2e"
ACCENT = "#e94560"
SOFT = "#a0a0b0"


def _title(text: str, font_size: int = 48) -> Text:
    return Text(text, font_size=font_size, color=WHITE, weight=BOLD)


def _subtitle(text: str, font_size: int = 28) -> Text:
    return Text(text, font_size=font_size, color=SOFT)


def _bullet(text: str, font_size: int = 28) -> VGroup:
    dot = Dot(radius=0.07, color=ACCENT)
    label = Text(text, font_size=font_size, color=WHITE)
    return VGroup(dot, label).arrange(RIGHT, buff=0.22)


def _bullet_list(lines: list[str], font_size: int = 28) -> VGroup:
    items = [_bullet(t, font_size=font_size) for t in lines]
    return VGroup(*items).arrange(DOWN, aligned_edge=LEFT, buff=0.32)


class LondonSystemLecture(VoiceoverScene):
    """End-to-end London System teaching lecture."""

    def construct(self):
        self.camera.background_color = BG
        self.set_speech_service(
            AOSSpeechService(voice="alba", cache_dir="voiceover_cache")
        )

        self._title_hook()
        self._agenda()
        self._why_london()
        self._pros_cons()
        self._starting_position()
        self._mainline()
        self._indian_setup()
        self._jobava()
        self._anti_early_c5()
        self._anti_indian()
        self._history()
        self._famous_kamsky()
        self._famous_carlsen()
        self._conclusion()

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _clear(self, *mobs) -> None:
        present = [m for m in mobs if m is not None]
        if present:
            self.play(*[FadeOut(m) for m in present], run_time=0.5)

    def _section_title(self, title: str, subtitle: str | None = None) -> VGroup:
        t = _title(title, 42)
        group = VGroup(t)
        if subtitle:
            s = _subtitle(subtitle, 24)
            group = VGroup(t, s).arrange(DOWN, buff=0.25)
        group.to_edge(UP, buff=0.45)
        return group

    def _new_board(self, fen: str | None = None, square_size: float = 0.62) -> ChessBoard:
        board = ChessBoard(
            fen,
            square_size=square_size,
            theme=BoardTheme.classic(),
            show_labels=True,
        )
        board.move_to(ORIGIN + DOWN * 0.35)
        return board

    def _play_sans(
        self,
        board: ChessBoard,
        sans: list[str],
        *,
        run_time: float = 0.55,
        bookmark_prefix: str | None = None,
        narrate: str | None = None,
    ) -> None:
        """Play SAN moves; optional single voiceover with per-move bookmarks."""
        if narrate and bookmark_prefix:
            marks = "".join(
                f" <bookmark mark='{bookmark_prefix}{i}'/>{san}."
                for i, san in enumerate(sans)
            )
            with self.voiceover(text=narrate + marks):
                for i, san in enumerate(sans):
                    self.wait_until_bookmark(f"{bookmark_prefix}{i}")
                    board.clear_annotations()
                    move = board.board.parse_san(san)
                    board.arrow(move.from_square, move.to_square)
                    board.animate_move(move, scene=self, run_time=run_time)
        else:
            for san in sans:
                board.clear_annotations()
                move = board.board.parse_san(san)
                board.arrow(move.from_square, move.to_square)
                board.animate_move(move, scene=self, run_time=run_time)

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------
    def _title_hook(self) -> None:
        title = _title("London System", 56)
        sub = _subtitle("A solid 1.d4 opening system for White", 30)
        group = VGroup(title, sub).arrange(DOWN, buff=0.4).move_to(ORIGIN)
        with self.voiceover(
            text="Welcome. Today we study the London System. "
            "<bookmark mark='T1'/>A popular and very solid one d four opening for White."
        ):
            self.play(FadeIn(title), run_time=0.8)
            self.wait_until_bookmark("T1")
            self.play(FadeIn(sub), run_time=0.6)
        self.wait(0.3)
        self._clear(group)

    def _agenda(self) -> None:
        header = self._section_title("Today's Agenda", "What we will cover")
        left = _bullet_list(
            [
                "Why the London System",
                "Starting position",
                "Pros and cons",
                "Mainline setup",
                "Indian setup (...g6)",
            ],
            font_size=26,
        )
        right = _bullet_list(
            [
                "Jobava London",
                "How to play against it",
                "History",
                "Famous games",
                "Conclusion",
            ],
            font_size=26,
        )
        cols = VGroup(left, right).arrange(RIGHT, buff=1.4, aligned_edge=UP)
        cols.next_to(header, DOWN, buff=0.55)

        marks = [
            ("A0", left[0]),
            ("A1", left[1]),
            ("A2", left[2]),
            ("A3", left[3]),
            ("A4", left[4]),
            ("A5", right[0]),
            ("A6", right[1]),
            ("A7", right[2]),
            ("A8", right[3]),
            ("A9", right[4]),
        ]
        self.play(FadeIn(header), run_time=0.5)
        with self.voiceover(
            text="Here is our agenda. "
            "<bookmark mark='A0'/>Why London, "
            "<bookmark mark='A1'/>the starting position, "
            "<bookmark mark='A2'/>pros and cons, "
            "<bookmark mark='A3'/>the mainline, "
            "<bookmark mark='A4'/>the Indian setup, "
            "<bookmark mark='A5'/>the Jobava London, "
            "<bookmark mark='A6'/>how Black fights back, "
            "<bookmark mark='A7'/>a short history, "
            "<bookmark mark='A8'/>famous games, "
            "<bookmark mark='A9'/>and a conclusion."
        ):
            for mark, mob in marks:
                self.wait_until_bookmark(mark)
                self.play(FadeIn(mob), run_time=0.25)
        self.wait(0.25)
        self._clear(header, cols)

    def _why_london(self) -> None:
        header = self._section_title("Why the London System?", "A true system opening")
        bullets = _bullet_list(
            [
                "White can use the same basic setup vs most replies",
                "Theory is lighter than many 1.d4 mainlines",
                "Build a solid center with c3 and e3",
                "Develop the dark-squared bishop outside the chain first",
            ],
            font_size=26,
        )
        bullets.next_to(header, DOWN, buff=0.55).align_to(header, LEFT).shift(LEFT * 0.2)
        self.play(FadeIn(header))
        with self.voiceover(
            text="The London is called a system because White can play the same setup "
            "against almost all of Black's responses. "
            "<bookmark mark='W0'/>That means less memorization than sharp theory. "
            "<bookmark mark='W1'/>The main idea is a solid pawn chain on c three and e three, "
            "<bookmark mark='W2'/>but only after developing the dark-squared bishop outside the pawn chain. "
            "<bookmark mark='W3'/>Despite the solid reputation, the London also has aggressive lines."
        ):
            for i, mob in enumerate(bullets):
                self.wait_until_bookmark(f"W{i}")
                self.play(FadeIn(mob), run_time=0.3)
        self.wait(0.2)
        self._clear(header, bullets)

    def _pros_cons(self) -> None:
        header = self._section_title("Pros and Cons")
        pros_title = Text("Pros", font_size=32, color=GREEN)
        cons_title = Text("Cons", font_size=32, color=ACCENT)
        pros = _bullet_list(
            [
                "Hard for Black to get active play",
                "Difficult for Black to avoid",
                "Sound path to a playable middlegame",
            ],
            font_size=24,
        )
        cons = _bullet_list(
            [
                "Less chance of a direct attack",
                "Little immediate pressure",
                "The bishop on f4 can be exposed",
            ],
            font_size=24,
        )
        left = VGroup(pros_title, pros).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        right = VGroup(cons_title, cons).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        cols = VGroup(left, right).arrange(RIGHT, buff=1.2, aligned_edge=UP)
        cols.next_to(header, DOWN, buff=0.5)

        self.play(FadeIn(header), FadeIn(pros_title), FadeIn(cons_title))
        with self.voiceover(
            text="Let's weigh the trade-offs. "
            "<bookmark mark='P0'/>It is hard for Black to generate easy activity. "
            "<bookmark mark='P1'/>The London is also difficult to avoid entirely. "
            "<bookmark mark='P2'/>And it is a very sound way to reach a playable middlegame. "
            "<bookmark mark='C0'/>On the downside, White has less chance of an early attack. "
            "<bookmark mark='C1'/>It puts little immediate pressure on Black. "
            "<bookmark mark='C2'/>And the bishop on f four can become a target."
        ):
            for i, mob in enumerate(pros):
                self.wait_until_bookmark(f"P{i}")
                self.play(FadeIn(mob), run_time=0.25)
            for i, mob in enumerate(cons):
                self.wait_until_bookmark(f"C{i}")
                self.play(FadeIn(mob), run_time=0.25)
        self.wait(0.2)
        self._clear(header, cols)

    def _starting_position(self) -> None:
        header = self._section_title(
            "Starting Position",
            "Classic path: 1.d4 d5 2.Nf3 Nf6 3.Bf4",
        )
        board = self._new_board()
        self.play(FadeIn(header), FadeIn(board), run_time=0.6)
        with self.voiceover(
            text="White enters the London when the dark-squared bishop reaches f four "
            "before pushing e three. "
            "<bookmark mark='S0'/>We start with d four. "
            "<bookmark mark='S1'/>Black answers d five. "
            "<bookmark mark='S2'/>Knight to f three. "
            "<bookmark mark='S3'/>Knight to f six. "
            "<bookmark mark='S4'/>And bishop to f four — this is the classic London entry. "
            "Modern theory prefers two bishop f four even earlier, but the idea is the same: "
            "develop the bishop outside the future pawn chain."
        ):
            self.wait_until_bookmark("S0")
            board.animate_move("d4", scene=self, run_time=0.55)
            self.wait_until_bookmark("S1")
            board.animate_move("d5", scene=self, run_time=0.55)
            self.wait_until_bookmark("S2")
            board.animate_move("Nf3", scene=self, run_time=0.55)
            self.wait_until_bookmark("S3")
            board.animate_move("Nf6", scene=self, run_time=0.55)
            self.wait_until_bookmark("S4")
            board.clear_annotations()
            m = board.board.parse_san("Bf4")
            board.arrow(m.from_square, m.to_square)
            board.animate_move(m, scene=self, run_time=0.7)
            board.highlight_last_move()
        self.wait(0.35)
        self._clear(header, board)

    def _mainline(self) -> None:
        header = self._section_title(
            "Mainline",
            "Balanced London: White eyes the kingside",
        )
        note = _subtitle(
            "1.d4 d5 2.Bf4 Nf6 3.e3 c5 4.c3 Nc6 5.Nd2 e6 6.Ngf3 Bd6 7.Bg3 O-O 8.Bd3 b6 9.Qe2 Bb7",
            18,
        )
        note.next_to(header, DOWN, buff=0.2)
        self.play(FadeIn(header), FadeIn(note))
        board = self._new_board(square_size=0.58)
        board.next_to(note, DOWN, buff=0.25)
        sans = [
            "d4", "d5", "Bf4", "Nf6", "e3", "c5", "c3", "Nc6", "Nd2", "e6",
            "Ngf3", "Bd6", "Bg3", "O-O", "Bd3", "b6", "Qe2", "Bb7",
        ]
        with self.voiceover(
            text="In the modern mainline, White often plays bishop f four on move two. "
            "White builds c three and e three, then aims at a kingside attack, "
            "while Black seeks a central break or queenside counterplay. "
            "Follow the setup on the board."
            + "".join(f" <bookmark mark='M{i}'/>{san}." for i, san in enumerate(sans))
        ):
            self.play(FadeIn(board), run_time=0.5)
            for i, san in enumerate(sans):
                self.wait_until_bookmark(f"M{i}")
                board.clear_annotations()
                move = board.board.parse_san(san)
                board.arrow(move.from_square, move.to_square)
                board.animate_move(move, scene=self, run_time=0.45)
            board.highlight_last_move()
        self.wait(0.3)
        self._clear(header, note, board)

    def _indian_setup(self) -> None:
        header = self._section_title(
            "Indian Setup (...g6)",
            "Fianchetto vs the London",
        )
        tip = _bullet_list(
            [
                "Black plays ...g6 to discourage Bd3",
                "White often develops the light-squared bishop to e2 instead",
            ],
            font_size=24,
        )
        tip.next_to(header, DOWN, buff=0.35).to_edge(LEFT, buff=0.6)
        self.play(FadeIn(header))
        board = self._new_board(square_size=0.58)
        board.to_edge(RIGHT, buff=0.4).shift(DOWN * 0.2)
        sans = ["d4", "Nf6", "Bf4", "g6", "Nf3", "Bg7", "e3", "d6"]
        with self.voiceover(
            text="One of Black's most common replies is an Indian setup with g six, "
            "fianchettoing the dark-squared bishop. "
            "<bookmark mark='I0'/>This discourages White from placing the light-squared bishop on the active d three square. "
            "<bookmark mark='I1'/>White's plan is similar to the mainline, but the bishop usually goes to e two."
            + "".join(f" <bookmark mark='IV{i}'/>{san}." for i, san in enumerate(sans))
        ):
            self.wait_until_bookmark("I0")
            self.play(FadeIn(tip[0]), FadeIn(board), run_time=0.4)
            self.wait_until_bookmark("I1")
            self.play(FadeIn(tip[1]), run_time=0.3)
            for i, san in enumerate(sans):
                self.wait_until_bookmark(f"IV{i}")
                board.clear_annotations()
                move = board.board.parse_san(san)
                board.arrow(move.from_square, move.to_square)
                board.animate_move(move, scene=self, run_time=0.5)
        self.wait(0.25)
        self._clear(header, tip, board)

    def _jobava(self) -> None:
        header = self._section_title(
            "Jobava London",
            "Nc3 instead of c3 — sharper play",
        )
        tip = _bullet_list(
            [
                "Knight to c3 is more active than a c3 pawn",
                "Can become much sharper if Black errs",
            ],
            font_size=24,
        )
        tip.next_to(header, DOWN, buff=0.35).to_edge(LEFT, buff=0.6)
        self.play(FadeIn(header), FadeIn(tip))
        board = self._new_board()
        board.to_edge(RIGHT, buff=0.5).shift(DOWN * 0.15)
        sans = ["d4", "Nf6", "Nc3", "d5", "Bf4"]
        with self.voiceover(
            text="The Jobava London has gained popularity. "
            "White develops the queen's knight to c three, where the pawn usually sits, "
            "for a more active piece. "
            "<bookmark mark='J0'/>Watch knight c three and bishop f four."
            + "".join(f" <bookmark mark='JV{i}'/>{san}." for i, san in enumerate(sans))
        ):
            self.play(FadeIn(board), run_time=0.45)
            self.wait_until_bookmark("J0")
            for i, san in enumerate(sans):
                self.wait_until_bookmark(f"JV{i}")
                board.clear_annotations()
                move = board.board.parse_san(san)
                board.arrow(move.from_square, move.to_square)
                board.animate_move(move, scene=self, run_time=0.55)
            board.highlight_square(chess.C3, color=YELLOW, opacity=0.4)
        self.wait(0.25)
        self._clear(header, tip, board)

    def _anti_early_c5(self) -> None:
        header = self._section_title(
            "How to Play Against the London",
            "The Early ...c5",
        )
        tips = _bullet_list(
            [
                "Black scores well with an early ...c5",
                "Idea: ...Qb6 pressures b2 and the center",
                "Prepared White may leave the London with 3.d5",
            ],
            font_size=24,
        )
        tips.next_to(header, DOWN, buff=0.35).to_edge(LEFT, buff=0.55)
        self.play(FadeIn(header))
        board = self._new_board(square_size=0.58)
        board.to_edge(RIGHT, buff=0.4).shift(DOWN * 0.15)
        sans = ["d4", "Nf6", "Bf4", "c5"]
        with self.voiceover(
            text="If Black knows the London, White may not get a big opening edge. "
            "<bookmark mark='E0'/>An early c five is a testing try. "
            "<bookmark mark='E1'/>Black often follows with queen b six, hitting b two while the dark-squared bishop cannot help. "
            "<bookmark mark='E2'/>A well-prepared London player may deviate with three d five, leaving the usual London setup — so Black must be ready."
            + "".join(f" <bookmark mark='EV{i}'/>{san}." for i, san in enumerate(sans))
        ):
            self.wait_until_bookmark("E0")
            self.play(FadeIn(tips[0]), FadeIn(board))
            self.wait_until_bookmark("E1")
            self.play(FadeIn(tips[1]))
            self.wait_until_bookmark("E2")
            self.play(FadeIn(tips[2]))
            for i, san in enumerate(sans):
                self.wait_until_bookmark(f"EV{i}")
                board.clear_annotations()
                move = board.board.parse_san(san)
                board.arrow(move.from_square, move.to_square)
                board.animate_move(move, scene=self, run_time=0.55)
        self.wait(0.25)
        self._clear(header, tips, board)

    def _anti_indian(self) -> None:
        header = self._section_title(
            "Against the London: Indian again",
            "Slow equality — and White's 3.Nc3 try",
        )
        tips = _bullet_list(
            [
                "Double fianchetto plans are common for Black",
                "White expands kingside; Black on the queenside",
                "White's best chance may again be leaving London with Nc3",
            ],
            font_size=24,
        )
        tips.next_to(header, DOWN, buff=0.4)
        self.play(FadeIn(header))
        with self.voiceover(
            text="The Indian setup with g six is also a solid equalizer. "
            "<bookmark mark='AI0'/>Games often stay slow and balanced. "
            "<bookmark mark='AI1'/>Black develops both bishops by fianchetto. "
            "<bookmark mark='AI2'/>And once more, prepared White players may leave the London with knight c three to fight for an edge."
        ):
            self.wait_until_bookmark("AI0")
            self.play(FadeIn(tips[0]))
            self.wait_until_bookmark("AI1")
            self.play(FadeIn(tips[1]))
            self.wait_until_bookmark("AI2")
            self.play(FadeIn(tips[2]))
        self.wait(0.25)
        self._clear(header, tips)

    def _history(self) -> None:
        header = self._section_title("History of the London System")
        bullets = _bullet_list(
            [
                "Bf4 ideas are centuries old",
                "Top-level popularity after the 1922 London Congress",
                "Spotlight from Alekhine versus Euwe",
                "Modern revival with World Champion Magnus Carlsen",
            ],
            font_size=26,
        )
        bullets.next_to(header, DOWN, buff=0.5)
        self.play(FadeIn(header))
        with self.voiceover(
            text="Developing the dark-squared bishop to f four is a natural idea. "
            "<bookmark mark='H0'/>It has been played for centuries. "
            "<bookmark mark='H1'/>The opening's name and popularity surged after the nineteen twenty two London Congress. "
            "<bookmark mark='H2'/>Especially after games involving Alekhine and Euwe. "
            "<bookmark mark='H3'/>More recently, Magnus Carlsen helped bring it back into elite repertoires."
        ):
            for i, mob in enumerate(bullets):
                self.wait_until_bookmark(f"H{i}")
                self.play(FadeIn(mob), run_time=0.3)
        self.wait(0.25)
        self._clear(header, bullets)

    def _famous_kamsky(self) -> None:
        header = self._section_title(
            "Famous Game: Kamsky vs Shankland",
            "Eastern Class Championship 2014 — kingside attack idea (excerpt)",
        )
        # Teaching excerpt toward a London middlegame attack shape (D02 flavor)
        caption = _subtitle("Key idea: London pieces aim at Black's kingside", 22)
        caption.next_to(header, DOWN, buff=0.2)
        self.play(FadeIn(header), FadeIn(caption))
        board = self._new_board(square_size=0.58)
        board.next_to(caption, DOWN, buff=0.2)
        sans = [
            "d4", "Nf6", "Nf3", "d5", "Bf4", "c5", "e3", "Nc6",
            "c3", "e6", "Nbd2", "Bd6", "Bg3", "O-O", "Bd3",
        ]
        with self.voiceover(
            text="Gata Kamsky used the London to create a quick kingside attack "
            "against Samuel Shankland. "
            "Watch how White's bishops and knights point toward the black king."
            + "".join(f" <bookmark mark='K{i}'/>{san}." for i, san in enumerate(sans))
        ):
            self.play(FadeIn(board), run_time=0.45)
            for i, san in enumerate(sans):
                self.wait_until_bookmark(f"K{i}")
                board.clear_annotations()
                move = board.board.parse_san(san)
                board.arrow(move.from_square, move.to_square)
                board.animate_move(move, scene=self, run_time=0.4)
            board.highlight_square(chess.D3, color=RED, opacity=0.35)
            board.highlight_square(chess.G3, color=RED, opacity=0.35)
        self.wait(0.3)
        self._clear(header, caption, board)

    def _famous_carlsen(self) -> None:
        header = self._section_title(
            "Famous Game: Carlsen vs Ding Liren",
            "MCT Finals 2020 — Bxd6 novelty idea (excerpt)",
        )
        caption = _subtitle("Key moment idea: 7.Bxd6 — pawn for lasting pressure", 22)
        caption.next_to(header, DOWN, buff=0.2)
        self.play(FadeIn(header), FadeIn(caption))
        board = self._new_board(square_size=0.58)
        board.next_to(caption, DOWN, buff=0.2)
        # Approach a Bxd6 thematic position; include the capture as the teaching beat
        sans = [
            "d4", "Nf6", "Bf4", "d5", "e3", "e6", "Nd2", "c5",
            "c3", "Nc6", "Ngf3", "Bd6", "Bxd6",
        ]
        with self.voiceover(
            text="In twenty twenty, Carlsen faced Ding Liren in a rapid game. "
            "He introduced a strong idea with bishop takes d six, "
            "giving a pawn for lasting positional pressure. "
            "Follow the approach and the capture."
            + "".join(f" <bookmark mark='CD{i}'/>{san}." for i, san in enumerate(sans))
        ):
            self.play(FadeIn(board), run_time=0.45)
            for i, san in enumerate(sans):
                self.wait_until_bookmark(f"CD{i}")
                board.clear_annotations()
                move = board.board.parse_san(san)
                board.arrow(move.from_square, move.to_square)
                board.animate_move(move, scene=self, run_time=0.4)
            board.highlight_last_move()
        self.wait(0.3)
        self._clear(header, caption, board)

    def _conclusion(self) -> None:
        header = self._section_title("Conclusion")
        bullets = _bullet_list(
            [
                "You know how to reach the London and why it works",
                "You saw mainline, Indian, and Jobava paths",
                "You know early ...c5 and ...g6 ways to fight it",
                "Study master games to deepen the middlegame plans",
            ],
            font_size=26,
        )
        bullets.next_to(header, DOWN, buff=0.5)
        self.play(FadeIn(header))
        play_chess_sfx(self, "notify")
        with self.voiceover(
            text="You now know what the London System is, how to reach it, "
            "and several ways to counter it. "
            "<bookmark mark='Z0'/>Remember the bishop outside the chain. "
            "<bookmark mark='Z1'/>Practice the main setups we covered. "
            "<bookmark mark='Z2'/>And when facing the London, test White with early c five or an Indian setup. "
            "<bookmark mark='Z3'/>For more, study master games in the London and build your own repertoire. "
            "Thank you for learning with us."
        ):
            for i, mob in enumerate(bullets):
                self.wait_until_bookmark(f"Z{i}")
                self.play(FadeIn(mob), run_time=0.3)
        play_chess_sfx(self, "end")
        thanks = _title("Thank you", 44)
        thanks.move_to(ORIGIN)
        self.play(FadeOut(header), FadeOut(bullets), FadeIn(thanks), run_time=0.8)
        self.wait(1.2)
        self.play(FadeOut(thanks), run_time=0.5)
