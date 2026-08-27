"""Unit tests for VoiceoverScene AST gate and MP4 selection helpers."""

from __future__ import annotations

from pathlib import Path

from tools.compile import (
    _find_scene_mp4,
    validate_voiceover_scene,
)
from tools.voiceover_quality import FILLER_VOICEOVER
from video_entry import find_mp4


VOICEOVER_OK = '''
from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService

class IntroScene(VoiceoverScene):
    def construct(self):
        self.set_speech_service(AOSSpeechService(voice="alba", cache_dir="voiceover_cache"))
        circle = Circle()
        with self.voiceover(text="Euler's formula shows a complex exponential can be written using cosine and sine.") as tracker:
            self.play(Create(circle), run_time=tracker.duration)
'''

PLAIN_SCENE = '''
from manim import *

class IntroScene(Scene):
    def construct(self):
        self.play(Create(Circle()))
'''

VOICEOVER_NO_CALLS = '''
from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService

class IntroScene(VoiceoverScene):
    def construct(self):
        self.set_speech_service(AOSSpeechService(voice="alba", cache_dir="voiceover_cache"))
        self.play(Create(Circle()))
'''


VOICEOVER_NO_SERVICE = '''
from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService

class IntroScene(VoiceoverScene):
    def construct(self):
        with self.voiceover(text="Let's explore this identity further.") as tracker:
            self.wait(tracker.duration)
'''


def test_validate_voiceover_scene_ok() -> None:
    assert validate_voiceover_scene(VOICEOVER_OK) is None


def test_validate_voiceover_scene_missing_base() -> None:
    assert validate_voiceover_scene(PLAIN_SCENE) == "missing_voiceover_scene"


def test_validate_voiceover_scene_missing_calls() -> None:
    assert validate_voiceover_scene(VOICEOVER_NO_CALLS) == "missing_voiceover_calls"


def test_validate_voiceover_scene_missing_speech_service() -> None:
    assert validate_voiceover_scene(VOICEOVER_NO_SERVICE) == "missing_speech_service"


def test_validate_voiceover_scene_filler() -> None:
    src = '''
from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService

class IntroScene(VoiceoverScene):
    def construct(self):
        self.set_speech_service(AOSSpeechService(voice="alba", cache_dir="voiceover_cache"))
        with self.voiceover(text="Let's look at this on the board.") as tracker:
            self.play(Create(Circle()), run_time=tracker.duration)
'''
    assert validate_voiceover_scene(src) == FILLER_VOICEOVER


def test_validate_voiceover_scene_here_we_have() -> None:
    src = '''
from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService

class IntroScene(VoiceoverScene):
    def construct(self):
        self.set_speech_service(AOSSpeechService(voice="alba", cache_dir="voiceover_cache"))
        with self.voiceover(text="Here we have Let's explore the magic of complex numbers.") as tracker:
            self.play(Write(Tex("Let's explore")), run_time=tracker.duration)
'''
    assert validate_voiceover_scene(src) == FILLER_VOICEOVER


def test_find_mp4_skips_partial_and_prefers_scene_name(tmp_path: Path) -> None:
    media = tmp_path / "media" / "videos" / "scene" / "480p15"
    partial = media / "partial_movie_files" / "IntroScene"
    media.mkdir(parents=True)
    partial.mkdir(parents=True)

    big_partial = partial / "chunk.mp4"
    big_partial.write_bytes(b"x" * 5000)
    final = media / "IntroScene.mp4"
    final.write_bytes(b"y" * 1000)
    other = media / "OtherScene.mp4"
    other.write_bytes(b"z" * 2000)

    assert find_mp4(tmp_path, scene_name="IntroScene") == final
    assert _find_scene_mp4(tmp_path, "IntroScene") == final
    # Without scene name, largest non-partial wins.
    assert find_mp4(tmp_path) == other
