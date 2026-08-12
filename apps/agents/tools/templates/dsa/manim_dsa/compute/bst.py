"""BST insert snapshots."""

from __future__ import annotations

from collections.abc import Sequence


class _Node:
    __slots__ = ("val", "left", "right")

    def __init__(self, val: int) -> None:
        self.val = val
        self.left = None
        self.right = None


def _parents(root: _Node | None) -> dict[int, int | None]:
    parent: dict[int, int | None] = {}
    if root is None:
        return parent
    parent[root.val] = None
    stack = [root]
    while stack:
        n = stack.pop()
        if n.left:
            parent[n.left.val] = n.val
            stack.append(n.left)
        if n.right:
            parent[n.right.val] = n.val
            stack.append(n.right)
    return parent


def bst_insert_steps(values: Sequence[int]) -> list[dict]:
    root: _Node | None = None
    steps: list[dict] = []
    for v in values:
        if root is None:
            root = _Node(v)
        else:
            cur = root
            while True:
                if v < cur.val:
                    if cur.left is None:
                        cur.left = _Node(v)
                        break
                    cur = cur.left
                else:
                    if cur.right is None:
                        cur.right = _Node(v)
                        break
                    cur = cur.right
        steps.append({"inserted": v, "parent": _parents(root), "root": root.val if root else None})
    return steps
