from __future__ import annotations

from typing import Optional, List, Dict, Any
from aos_manim_core import get_theme, ThemeConfig
from ..structures.array import ArrayMobject


def compute_bubble_sort_steps(arr: List[int]) -> Dict[str, Any]:
    """Generates step trace for bubble sort."""
    a = list(arr)
    n = len(a)
    steps = []

    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            comp_info = {
                "type": "compare",
                "idx_a": j,
                "idx_b": j + 1,
                "val_a": a[j],
                "val_b": a[j + 1],
                "array_state": list(a),
            }
            steps.append(comp_info)
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                swapped = True
                swap_info = {
                    "type": "swap",
                    "idx_a": j,
                    "idx_b": j + 1,
                    "val_a": a[j],
                    "val_b": a[j + 1],
                    "array_state": list(a),
                }
                steps.append(swap_info)
        if not swapped:
            break

    return {
        "initial": arr,
        "sorted": a,
        "steps": steps,
    }


class BubbleSortVisualizer:
    """Visualizes Bubble Sort execution and comparisons."""

    def __init__(self, theme: Optional[ThemeConfig] = None) -> None:
        self.theme = theme or get_theme()

    def build_bubble_sort_mobjects(self, arr: List[int]) -> Dict[str, Any]:
        trace = compute_bubble_sort_steps(arr)
        t = self.theme
        array_mob = ArrayMobject(arr, theme=t)

        return {
            "array_mob": array_mob,
            "trace": trace,
        }
