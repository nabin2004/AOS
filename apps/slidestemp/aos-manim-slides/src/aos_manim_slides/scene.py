from __future__ import annotations

from typing import Optional, List
from manim import Scene, FadeIn, FadeOut, LEFT

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
        old_slide = self.current_slide
        self.slides.append(slide)
        self.current_slide_idx = len(self.slides) - 1

        if old_slide is None:
            self.play(FadeIn(slide, run_time=run_time))
        else:
            if transition == "wipe":
                wipe_transition(self, old_slide, slide, direction=LEFT, run_time=run_time)
            elif transition == "zoom":
                zoom_slide_transition(self, old_slide, slide, run_time=run_time)
            elif transition == "fade":
                fade_transition(self, old_slide, slide, run_time=run_time)
            else:
                self.remove(old_slide)
                self.add(slide)

        if lecture:
            self._run_lecture(slide)

    def _run_lecture(self, slide: Slide) -> None:
        hide_lecture_body(slide)
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

    def enable_voiceover(self, speech_service=None) -> bool:
        if speech_service is not None and hasattr(self, "set_speech_service"):
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
