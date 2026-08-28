from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence, runtime_checkable

BOOKMARK_RE = re.compile(r"<bookmark\s+mark=['\"]([^'\"]+)['\"]\s*/>", re.IGNORECASE)
DEFAULT_CUE_GAP = 0.35


class CueAction(str, Enum):
    REVEAL = "reveal"
    HIGHLIGHT = "highlight"
    INDICATE = "indicate"
    DIM = "dim"
    STEP = "step"
    PLAY = "play"
    SFX = "sfx"


@dataclass
class Cue:
    """One timed beat: a bookmark mark mapped to a visual action on a target."""

    mark: str
    target_id: str
    action: CueAction = CueAction.REVEAL
    payload: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.action, str):
            self.action = CueAction(self.action)


@dataclass
class NarrationScript:
    text: str = ""
    cues: List[Cue] = field(default_factory=list)

    def with_bookmarks(self) -> str:
        return inject_bookmarks(self.text, self.cues)

    def as_voiceover_text(self) -> str:
        """Bookmarked narration string for manim-voiceover ``voiceover(text=...)``."""
        return self.with_bookmarks()


@runtime_checkable
class Cueable(Protocol):
    def cue_targets(self) -> Mapping[str, Any]:
        ...

    def apply_cue(self, scene: Any, cue: Cue) -> None:
        ...

    def step_count(self) -> int:
        ...


def parse_bookmark_marks(text: str) -> List[str]:
    return BOOKMARK_RE.findall(text or "")


def inject_bookmarks(text: str, cues: Sequence[Cue]) -> str:
    """Ensure each cue has a bookmark tag. Existing tags are left in place."""
    body = text or ""
    present = set(parse_bookmark_marks(body))
    missing = [c for c in cues if c.mark not in present]
    if not missing:
        return body
    suffix = "".join(f" <bookmark mark='{c.mark}'/>" for c in missing)
    return (body.rstrip() + suffix).strip()


def bind_authored_script(
    text: str,
    auto_cues: Sequence[Cue],
    explicit: Optional[Sequence[Cue]] = None,
) -> NarrationScript:
    """Map an authored voiceover string onto auto or explicit cues."""
    if explicit:
        return NarrationScript(text=text, cues=list(explicit))
    auto = list(auto_cues)
    marks = parse_bookmark_marks(text)
    if not marks:
        return NarrationScript(text=inject_bookmarks(text, auto), cues=auto)

    by_mark = {c.mark: c for c in auto}
    by_target = {c.target_id: c for c in auto}
    used: set[int] = set()
    bound: List[Cue] = []
    for mark in marks:
        if mark in by_mark:
            src = by_mark[mark]
            bound.append(src)
            used.add(id(src))
            continue
        if mark in by_target:
            src = by_target[mark]
            bound.append(
                Cue(mark=mark, target_id=src.target_id, action=src.action, payload=dict(src.payload))
            )
            used.add(id(src))
            continue
        nxt = next((c for c in auto if id(c) not in used), None)
        if nxt is not None:
            used.add(id(nxt))
            bound.append(
                Cue(mark=mark, target_id=nxt.target_id, action=nxt.action, payload=dict(nxt.payload))
            )
        else:
            bound.append(Cue(mark=mark, target_id=mark, action=CueAction.REVEAL))
    return NarrationScript(text=text, cues=bound)


def wait_for_mark(scene: Any, mark: str, gap: float = DEFAULT_CUE_GAP) -> None:
    use_vo = bool(getattr(scene, "aos_voiceover_active", False))
    waiter = getattr(scene, "wait_until_bookmark", None)
    if use_vo and callable(waiter):
        waiter(mark)
        return
    wait = getattr(scene, "wait", None)
    if callable(wait):
        wait(gap)


def _play(scene: Any, *anims: Any, run_time: float = 0.3) -> None:
    play = getattr(scene, "play", None)
    if callable(play) and anims:
        try:
            play(*anims, run_time=run_time)
            return
        except Exception:
            pass
    for anim in anims:
        mob = getattr(anim, "mobject", None)
        if mob is not None and hasattr(mob, "set_opacity"):
            mob.set_opacity(1)


def apply_standard_cue(
    scene: Any,
    cue: Cue,
    mob: Any,
    *,
    theme: Any = None,
    highlight_boxes: Optional[Dict[str, Any]] = None,
) -> None:
    if mob is None:
        if cue.action == CueAction.SFX:
            player = getattr(scene, "add_sound", None)
            name = (cue.payload or {}).get("name")
            if callable(player) and name:
                player(str(name))
        return

    color_a = getattr(theme, "highlight_a", None) if theme is not None else None
    color_b = getattr(theme, "highlight_b", None) if theme is not None else None

    if cue.action == CueAction.REVEAL:
        try:
            from manim import FadeIn, Create, Write
            use_draw = (cue.payload or {}).get("draw", False) or getattr(mob, "draw", False)
            if use_draw:
                from manim import Text, MathTex
                has_text = False
                try:
                    family = mob.get_family()
                    has_text = any(isinstance(sub, (Text, MathTex)) for sub in family)
                except Exception:
                    pass
                if has_text:
                    anim = Write(mob)
                else:
                    anim = Create(mob)
            else:
                anim = FadeIn(mob)

            _play(scene, anim, run_time=float(cue.payload.get("run_time", 0.3)))
        except Exception:
            if hasattr(mob, "set_opacity"):
                mob.set_opacity(1)
        return

    if cue.action == CueAction.DIM:
        if hasattr(mob, "set_opacity"):
            mob.set_opacity(float(cue.payload.get("opacity", 0.35)))
        return

    if cue.action == CueAction.HIGHLIGHT:
        try:
            from manim import SurroundingRectangle

            box = SurroundingRectangle(
                mob,
                color=color_a or "#FACC15",
                buff=0.08,
                stroke_width=2.5,
            )
            if highlight_boxes is not None:
                old = highlight_boxes.pop(cue.target_id, None)
                if old is not None and hasattr(scene, "remove"):
                    scene.remove(old)
                highlight_boxes[cue.target_id] = box
            if hasattr(scene, "add"):
                scene.add(box)
            else:
                _play(scene, box)
        except Exception:
            if hasattr(mob, "set_stroke"):
                mob.set_stroke(color=color_a or "#FACC15", width=3)
        return

    if cue.action == CueAction.INDICATE:
        try:
            from manim import Indicate

            _play(
                scene,
                Indicate(mob, color=color_b or color_a or "#06B6D4"),
                run_time=float(cue.payload.get("run_time", 0.5)),
            )
        except Exception:
            if hasattr(mob, "set_opacity"):
                mob.set_opacity(1)
        return

    if cue.action == CueAction.STEP:
        apply_fn = getattr(mob, "apply_cue", None)
        if callable(apply_fn):
            apply_fn(scene, cue)
        elif hasattr(mob, "set_opacity"):
            mob.set_opacity(1)
        return

    if cue.action == CueAction.PLAY:
        apply_fn = getattr(mob, "apply_cue", None)
        play_fn = getattr(mob, "play_on", None)
        if callable(apply_fn):
            apply_fn(scene, cue)
            return
        if callable(play_fn):
            play_fn(scene)
            return
        if hasattr(mob, "set_opacity"):
            mob.set_opacity(1)
        return

    if cue.action == CueAction.SFX:
        player = getattr(scene, "add_sound", None)
        name = (cue.payload or {}).get("name")
        if callable(player) and name:
            player(str(name))


class CueResolver:
    """Looks up mobjects and Cueable visualizers by target_id."""

    def __init__(
        self,
        targets: Optional[Dict[str, Any]] = None,
        cueables: Optional[Dict[str, Any]] = None,
        theme: Any = None,
    ) -> None:
        self.targets: Dict[str, Any] = dict(targets or {})
        self.cueables: Dict[str, Any] = dict(cueables or {})
        self.theme = theme
        self._highlight_boxes: Dict[str, Any] = {}

    def apply_cue(self, scene: Any, cue: Cue) -> None:
        cueable = self.cueables.get(cue.target_id)
        if cueable is None and "." in cue.target_id:
            cueable = self.cueables.get(cue.target_id.split(".", 1)[0])
        if cueable is not None and hasattr(cueable, "apply_cue"):
            if cue.action in (
                CueAction.STEP,
                CueAction.PLAY,
                CueAction.HIGHLIGHT,
                CueAction.INDICATE,
                CueAction.REVEAL,
                CueAction.DIM,
            ):
                cueable.apply_cue(scene, cue)
                return
        mob = self.targets.get(cue.target_id)
        apply_standard_cue(
            scene,
            cue,
            mob,
            theme=self.theme,
            highlight_boxes=self._highlight_boxes,
        )


def play_script(
    scene: Any,
    script: NarrationScript,
    resolver: CueResolver,
    *,
    gap: float = DEFAULT_CUE_GAP,
) -> None:
    """Wait on each bookmark (or a timed gap) and apply the matching cue."""
    cues = list(script.cues)
    text = script.with_bookmarks()

    def run() -> None:
        for cue in cues:
            wait_for_mark(scene, cue.mark, gap)
            resolver.apply_cue(scene, cue)

    voiceover_cm = getattr(scene, "voiceover", None)
    enabled = bool(getattr(scene, "aos_voiceover_enabled", False))
    if enabled and callable(voiceover_cm):
        scene.aos_voiceover_active = True
        try:
            with voiceover_cm(text=text):
                run()
        finally:
            scene.aos_voiceover_active = False
        return
    run()


def is_cueable(obj: Any) -> bool:
    return hasattr(obj, "apply_cue") and hasattr(obj, "cue_targets")
