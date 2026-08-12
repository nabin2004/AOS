"""Sorting step traces (pure Python)."""

from __future__ import annotations

from collections.abc import Iterator, Sequence


def bubble_sort_steps(arr: Sequence[int]) -> list[dict]:
    a = list(arr)
    steps = [{"array": a.copy(), "highlights": [], "swaps": [], "done": False}]
    n = len(a)
    for i in range(n):
        for j in range(0, n - i - 1):
            steps.append({"array": a.copy(), "highlights": [j, j + 1], "swaps": [], "done": False})
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                steps.append({"array": a.copy(), "highlights": [j, j + 1], "swaps": [j, j + 1], "done": False})
    steps.append({"array": a.copy(), "highlights": [], "swaps": [], "done": True})
    return steps


def merge_sort_steps(arr: Sequence[int]) -> list[dict]:
    a = list(arr)
    steps: list[dict] = [{"array": a.copy(), "highlights": [], "swaps": [], "done": False, "note": "start"}]

    def merge(lo: int, mid: int, hi: int) -> None:
        left = a[lo:mid]
        right = a[mid:hi]
        i = j = 0
        k = lo
        while i < len(left) and j < len(right):
            steps.append(
                {
                    "array": a.copy(),
                    "highlights": [lo + i if i < len(left) else mid + j, mid + j if j < len(right) else lo + i],
                    "swaps": [],
                    "done": False,
                    "note": f"merge [{lo},{hi})",
                }
            )
            if left[i] <= right[j]:
                a[k] = left[i]
                i += 1
            else:
                a[k] = right[j]
                j += 1
            k += 1
            steps.append({"array": a.copy(), "highlights": [k - 1], "swaps": [], "done": False, "note": "placed"})
        while i < len(left):
            a[k] = left[i]
            i += 1
            k += 1
            steps.append({"array": a.copy(), "highlights": [k - 1], "swaps": [], "done": False})
        while j < len(right):
            a[k] = right[j]
            j += 1
            k += 1
            steps.append({"array": a.copy(), "highlights": [k - 1], "swaps": [], "done": False})

    def sort(lo: int, hi: int) -> None:
        if hi - lo <= 1:
            return
        mid = (lo + hi) // 2
        sort(lo, mid)
        sort(mid, hi)
        merge(lo, mid, hi)

    sort(0, len(a))
    steps.append({"array": a.copy(), "highlights": [], "swaps": [], "done": True, "note": "done"})
    return steps
