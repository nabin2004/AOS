"""Binary search steps."""

from __future__ import annotations

from collections.abc import Sequence


def binary_search_steps(arr: Sequence[int], target: int) -> list[dict]:
    a = list(arr)
    lo, hi = 0, len(a) - 1
    steps = [{"array": a, "lo": lo, "hi": hi, "mid": None, "found": False}]
    while lo <= hi:
        mid = (lo + hi) // 2
        steps.append({"array": a, "lo": lo, "hi": hi, "mid": mid, "found": a[mid] == target})
        if a[mid] == target:
            return steps
        if a[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    steps.append({"array": a, "lo": lo, "hi": hi, "mid": None, "found": False})
    return steps
