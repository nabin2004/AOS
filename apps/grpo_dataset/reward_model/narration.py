from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class NarrationScore:
    score: float
    has_voiceover_scene: bool
    has_speech_service: bool
    voiceover_call_count: int
    has_bookmarks: bool
    bookmark_count: int
    has_bookmark_sync: bool
    details: Dict[str, Any]


def compute_narration_score(code: str) -> NarrationScore:
    """Analyze Manim Python code to evaluate adherence to ManimVoiceover patterns.

    Metrics scored:
    1. Inheriting from VoiceoverScene (weight: 0.25)
    2. Initializing speech service via self.set_speech_service(...) (weight: 0.20)
    3. Proper usage of `with self.voiceover(...)` blocks (weight: 0.25)
    4. SSML bookmark annotations `<bookmark mark="..."/>` in voiceover text (weight: 0.15)
    5. Synchronization with `self.wait_until_bookmark(...)` (weight: 0.15)
    """
    if not code or not isinstance(code, str):
        return NarrationScore(
            score=0.0,
            has_voiceover_scene=False,
            has_speech_service=False,
            voiceover_call_count=0,
            has_bookmarks=False,
            bookmark_count=0,
            has_bookmark_sync=False,
            details={"error": "Empty or invalid code string"},
        )

    # 1. Check VoiceoverScene inheritance
    has_voiceover_scene = bool(
        re.search(r"class\s+[A-Za-z0-9_]+\s*\([^)]*VoiceoverScene[^)]*\):", code)
    )

    # 2. Check self.set_speech_service
    has_speech_service = bool(
        re.search(r"self\.set_speech_service\s*\(", code)
    )

    # 3. Check voiceover call blocks: `self.voiceover(...)` or `with self.voiceover`
    voiceover_calls = len(re.findall(r"self\.voiceover\s*\(", code))

    # 4. Check bookmarks inside narration text: <bookmark mark='...'/> or <bookmark mark="..."/>
    bookmarks = re.findall(r"<bookmark\s+mark=[\'\"][^\'\"]+[\'\"]\s*/>", code)
    bookmark_count = len(bookmarks)
    has_bookmarks = bookmark_count > 0

    # 5. Check synchronization call: self.wait_until_bookmark(...)
    wait_bookmark_calls = len(re.findall(r"self\.wait_until_bookmark\s*\(", code))
    has_bookmark_sync = wait_bookmark_calls > 0

    # Calculate subscores
    score_scene = 0.25 if has_voiceover_scene else 0.0
    score_service = 0.20 if has_speech_service else 0.0
    
    # Scale voiceover calls up to a max of 0.25 (at least 2 calls gives full credit)
    if voiceover_calls >= 2:
        score_voiceover = 0.25
    elif voiceover_calls == 1:
        score_voiceover = 0.15
    else:
        score_voiceover = 0.0

    score_bm = 0.15 if has_bookmarks else 0.0
    score_sync = 0.15 if has_bookmark_sync else 0.0

    total_score = round(score_scene + score_service + score_voiceover + score_bm + score_sync, 4)

    return NarrationScore(
        score=total_score,
        has_voiceover_scene=has_voiceover_scene,
        has_speech_service=has_speech_service,
        voiceover_call_count=voiceover_calls,
        has_bookmarks=has_bookmarks,
        bookmark_count=bookmark_count,
        has_bookmark_sync=has_bookmark_sync,
        details={
            "score_scene": score_scene,
            "score_service": score_service,
            "score_voiceover": score_voiceover,
            "score_bookmarks": score_bm,
            "score_sync": score_sync,
            "wait_bookmark_calls": wait_bookmark_calls,
        },
    )
