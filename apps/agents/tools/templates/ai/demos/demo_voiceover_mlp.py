"""Demo: VoiceoverScene + bookmarks with MLP."""

from manim import *
from manim_voiceover import VoiceoverScene

from tools.aos_speech_service import AOSSpeechService
from manim_ai import get_concept, reveal_with_bookmarks


class DemoVoiceoverMLP(VoiceoverScene):
    def construct(self):
        self.camera.background_color = "#1a1a2e"
        self.set_speech_service(
            AOSSpeechService(voice="alba", cache_dir="voiceover_cache")
        )

        title = Text("Multilayer Perceptrons", font_size=36, color=WHITE)
        net = get_concept("mlp_network").build(layers=[3, 4, 2])
        act = get_concept("activations").build().scale(0.55)
        title.to_edge(UP)
        net.next_to(title, DOWN, buff=0.4)
        act.next_to(net, DOWN, buff=0.35)

        reveal_with_bookmarks(
            self,
            text="Today we study multilayer perceptrons. "
            "<bookmark mark='T'/>Here is the title. "
            "<bookmark mark='N'/>This network maps inputs through hidden layers. "
            "<bookmark mark='A'/>And these are common activation functions.",
            marks={"T": title, "N": net, "A": act},
            run_time=0.45,
        )
        self.wait(0.8)
