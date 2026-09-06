from __future__ import annotations

from typing import Optional, List
from manim import Scene, FadeIn, FadeOut, Group, LEFT

from aos_manim_core import CueResolver, play_script, get_theme

from .layouts.base_slide import Slide
from .narration import hide_lecture_body, script_for_slide
from .transitions.transitions import fade_transition, wipe_transition, zoom_slide_transition

try:
    from manim_voiceover import VoiceoverScene as _VoiceoverScene
except Exception:  # pragma: no cover - optional dependency
    class _VoiceoverScene:  # type: ignore[no-redef]
        pass


class SlideScene(Scene):
    """Presentation scene controller with slide lifecycle management."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.slides: List[Slide] = []
        self.current_slide_idx: int = -1

    @property
    def current_slide(self) -> Optional[Slide]:
        if 0 <= self.current_slide_idx < len(self.slides):
            return self.slides[self.current_slide_idx]
        return None

    def show_slide(
        self,
        slide: Slide,
        transition: str = "fade",
        run_time: float = 0.8,
        lecture: bool = False,
    ) -> None:
        """Display a new slide using the specified transition."""
        if lecture:
            # Hide dynamic lecture body elements before the entrance transition
            # so they never flash at frame zero.
            hide_lecture_body(slide)

        old_slide = self.current_slide
        self.slides.append(slide)
        self.current_slide_idx = len(self.slides) - 1

        if old_slide is None:
            residual = [m for m in self.mobjects if m != slide]
            if residual:
                self.play(FadeOut(Group(*residual), run_time=run_time * 0.5))
                self.clear()
            self.play(FadeIn(slide, run_time=run_time))
        else:
            if transition == "wipe":
                wipe_transition(self, old_slide, slide, direction=LEFT, run_time=run_time)
            elif transition == "zoom":
                zoom_slide_transition(self, old_slide, slide, run_time=run_time)
            elif transition == "fade":
                fade_transition(self, old_slide, slide, run_time=run_time)
            else:
                self.clear()
                self.add(slide)

        if lecture:
            self._run_lecture(slide)

    def _run_lecture(self, slide: Slide) -> None:
        spec = slide.spec
        if spec is None:
            return
        script = script_for_slide(spec, getattr(slide, "cueables", {}))
        theme = getattr(slide, "theme", None) or get_theme()
        resolver = CueResolver(
            targets=getattr(slide, "cue_index", {}),
            cueables=getattr(slide, "cueables", {}),
            theme=theme,
        )
        play_script(self, script, resolver, gap=getattr(self, "lecture_gap", 0.35))

    def pause_slide(self, duration: float = 1.0) -> None:
        """Pause execution between slide points."""
        self.wait(duration)


class VoiceoverSlideScene(SlideScene, _VoiceoverScene):
    """Slide scene that reveals / highlights / steps content on voiceover bookmarks."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.aos_voiceover_enabled = False
        self.lecture_gap = 0.35

    def enable_voiceover(
        self, speech_service=None, voice: str = "alba", cache_dir: str = "voiceover_cache"
    ) -> bool:
        if not hasattr(self, "set_speech_service"):
            self.aos_voiceover_enabled = False
            return False

        if speech_service is None:
            import sys
            from pathlib import Path
            
            # Try loading AOSSpeechService, fallback to gTTS if unavailable
            try:
                try:
                    from tools.aos_speech_service import AOSSpeechService
                    speech_service = AOSSpeechService(voice=voice, cache_dir=cache_dir)
                except ImportError:
                    # Append apps/agents to path if not present (assuming monorepo layout)
                    agent_tools_path = Path(__file__).resolve().parents[4] / "agents"
                    if agent_tools_path.exists() and str(agent_tools_path) not in sys.path:
                        sys.path.insert(0, str(agent_tools_path))
                        from tools.aos_speech_service import AOSSpeechService
                        speech_service = AOSSpeechService(voice=voice, cache_dir=cache_dir)
                    else:
                        raise ImportError
            except ImportError:
                try:
                    from manim_voiceover.services.gtts import GTTSService
                    speech_service = GTTSService(lang="en")
                except ImportError:
                    pass

        if speech_service is not None:
            self.set_speech_service(speech_service)
            self.aos_voiceover_enabled = True
            return True

        self.aos_voiceover_enabled = False
        return False

    def beats(self, text: str, beats: list) -> None:
        """London-style bookmark loop; timed waits when voiceover is off."""
        gap = getattr(self, "lecture_gap", 0.55)
        marked = text
        for mark, _fn in beats:
            token = f"mark='{mark}'"
            if token not in marked and f'mark="{mark}"' not in marked:
                marked += f" <bookmark mark='{mark}'/>"
        if getattr(self, "aos_voiceover_enabled", False) and hasattr(self, "voiceover"):
            self.aos_voiceover_active = True
            try:
                with self.voiceover(text=marked):
                    for mark, fn in beats:
                        self.wait_until_bookmark(mark)
                        fn()
            finally:
                self.aos_voiceover_active = False
            return
        for _mark, fn in beats:
            fn()
            self.wait(gap)

    def show_slide(
        self,
        slide: Slide,
        transition: str = "fade",
        run_time: float = 0.8,
        lecture: bool = True,
    ) -> None:
        super().show_slide(slide, transition=transition, run_time=run_time, lecture=lecture)


class MarkdownVoiceoverDeck(VoiceoverSlideScene):
    """Robust, agent-friendly scene to render a full Markdown deck with voiceover."""

    markdown_file: str = "presentation.md"
    voice: str = "alba"
    voiceover_cache: str = "voiceover_cache"

    def construct(self):
        self.enable_voiceover(voice=self.voice, cache_dir=self.voiceover_cache)
        
        with open(self.markdown_file, "r", encoding="utf-8") as f:
            md_content = f.read()
            
        for slide in Slide.deck_from_markdown(md_content):
            self.show_slide(slide, transition="fade", lecture=True)
            self.pause_slide(self.lecture_gap)
