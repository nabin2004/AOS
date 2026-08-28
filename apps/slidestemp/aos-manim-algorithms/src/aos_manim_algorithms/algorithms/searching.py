from __future__ import annotations

from typing import Optional, List, Dict, Any
from manim import (
    VGroup,
    Text,
    Arrow,
    UP,
    DOWN,
    LEFT,
    RIGHT,
)
from aos_manim_core import get_theme, ThemeConfig, Cue, CueAction, apply_standard_cue
from ..structures.array import ArrayMobject


def compute_binary_search_steps(arr: List[int], target: int) -> Dict[str, Any]:
    """Generates execution trace for binary search."""
    steps = []
    left = 0
    right = len(arr) - 1
    found_idx = -1

    while left <= right:
        mid = (left + right) // 2
        mid_val = arr[mid]
        step_info = {
            "left": left,
            "right": right,
            "mid": mid,
            "mid_val": mid_val,
            "target": target,
        }

        if mid_val == target:
            step_info["action"] = f"Found target {target} at index {mid}!"
            step_info["status"] = "found"
            found_idx = mid
            steps.append(step_info)
            break
        elif mid_val < target:
            step_info["action"] = f"{mid_val} < {target} -> Search right half (left = {mid + 1})"
            step_info["status"] = "search_right"
            steps.append(step_info)
            left = mid + 1
        else:
            step_info["action"] = f"{mid_val} > {target} -> Search left half (right = {mid - 1})"
            step_info["status"] = "search_left"
            steps.append(step_info)
            right = mid - 1

    return {
        "array": arr,
        "target": target,
        "found_index": found_idx,
        "steps": steps,
    }


class BinarySearchVisualizer:
    """Visualizes binary search steps with pointer annotations."""

    def __init__(self, theme: Optional[ThemeConfig] = None) -> None:
        self.theme = theme or get_theme()

    def build_binary_search_mobjects(
        self,
        arr: List[int],
        target: int,
    ) -> Dict[str, Any]:
        trace = compute_binary_search_steps(arr, target)
        t = self.theme

        array_mob = ArrayMobject(arr, theme=t)

        header = Text(
            f"Binary Search: Target = {target}",
            font_size=t.fonts.title_font_size - 8,
            color=t.text_main,
            font=t.fonts.text_font,
            weight="BOLD",
        ).next_to(array_mob, UP, buff=0.8)

        status_text = Text(
            trace["steps"][0]["action"] if trace["steps"] else "Starting search...",
            font_size=t.fonts.body_font_size - 4,
            color=t.accent,
            font=t.fonts.text_font,
        ).next_to(array_mob, DOWN, buff=0.8)

        return {
            "array_mob": array_mob,
            "header": header,
            "status_text": status_text,
            "trace": trace,
        }

    def build_cueable_binary_search(self, arr: List[int], target: int, show_all_steps: bool = True) -> "BinarySearchCueable":
        packed = self.build_binary_search_mobjects(arr, target)
        return BinarySearchCueable(packed, theme=self.theme)


class BinarySearchCueable(VGroup):
    """Binary search visualizer driven by STEP cues (lo / mid / hi highlights)."""

    def __init__(self, packed: Dict[str, Any], theme: Optional[ThemeConfig] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()
        self.array_mob = packed["array_mob"]
        self.header = packed["header"]
        self.status_text = packed["status_text"]
        self.trace = packed["trace"]
        self.base = VGroup(self.array_mob, self.header, self.status_text)
        self.add(self.base)
        self.applied_step = -1

    def cue_targets(self) -> Dict[str, Any]:
        return {"base": self.base, "array": self.array_mob}

    def step_count(self) -> int:
        return len(self.trace.get("steps") or [])

    def apply_cue(self, scene: Any, cue: Cue) -> None:
        if cue.action == CueAction.REVEAL:
            apply_standard_cue(scene, cue, self.base, theme=self.theme)
            return
        if cue.action == CueAction.STEP:
            i = int((cue.payload or {}).get("i", 0))
            steps = self.trace.get("steps") or []
            if not steps:
                return
            i = max(0, min(i, len(steps) - 1))
            step = steps[i]
            self.applied_step = i
            self.array_mob.reset_all()
            t = self.theme
            self.array_mob.highlight_index(step["left"], t.highlight_b)
            self.array_mob.highlight_index(step["right"], t.highlight_b)
            self.array_mob.highlight_index(step["mid"], t.highlight_a)
            if step.get("status") == "found":
                self.array_mob.highlight_index(step["mid"], t.success)
            new_status = Text(
                step.get("action", ""),
                font_size=t.fonts.body_font_size - 4,
                color=t.accent,
                font=t.fonts.text_font,
            )
            new_status.move_to(self.status_text.get_center())
            self.base.remove(self.status_text)
            self.remove(self.status_text)
            self.status_text = new_status
            self.base.add(self.status_text)
            self.add(self.status_text)
            return
        apply_standard_cue(scene, cue, self.base, theme=self.theme)
