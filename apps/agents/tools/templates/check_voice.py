from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService


class IntroScene(VoiceoverScene):
    def construct(self):
        self.set_speech_service(
            AOSSpeechService(voice="alba", cache_dir="voiceover_cache")
        )

        circle = Circle()
        with self.voiceover(text="This circle is drawn as I speak, Look this circle will be drawn until I speak.") as tracker:
            self.play(Create(circle), run_time=tracker.duration)

        with self.voiceover(text="Let's move the circle to the left as I speak, Look this circle will be moved until I speak.") as tracker:
            self.play(circle.animate.shift(LEFT), run_time=tracker.duration)

        with self.voiceover(text="Now let's change the color of the circle to blue as I speak, Look this circle will be changed to red until I speak.") as tracker:
            self.play(circle.animate.set_fill(BLUE), run_time=tracker.duration)

        self.wait(1)  
