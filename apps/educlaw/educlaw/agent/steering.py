"""In-memory FIFO steering queue and priority gate."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import Literal


class GateDecision(str, Enum):
    STEER_NOW = "steer_now"
    ANSWER_LATER = "answer_later"
    ABORT = "abort"


@dataclass(slots=True)
class SteeringMessage:
    text: str
    kind: Literal["steer", "abort"] = "steer"


class SteeringQueue:
    """Thread-safe FIFO. Inject only at a safe boundary (before the next model call)."""

    def __init__(self) -> None:
        self._items: deque[SteeringMessage] = deque()
        self._lock = Lock()

    def push(self, text: str, kind: Literal["steer", "abort"] = "steer") -> None:
        with self._lock:
            self._items.append(SteeringMessage(text=text, kind=kind))

    def pop(self) -> SteeringMessage | None:
        with self._lock:
            if not self._items:
                return None
            return self._items.popleft()

    def drain(self) -> list[SteeringMessage]:
        with self._lock:
            items = list(self._items)
            self._items.clear()
            return items

    def requeue_front(self, messages: list[SteeringMessage]) -> None:
        with self._lock:
            self._items.extendleft(reversed(messages))

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)


def decide_gate(message: SteeringMessage, *, running: bool) -> GateDecision:
    """Choose steer_now, answer_later, or abort."""
    stripped = message.text.strip()
    lowered = stripped.lower()
    if message.kind == "abort" or lowered in {"/abort", "abort"}:
        return GateDecision.ABORT
    if not running:
        return GateDecision.STEER_NOW
    if len(stripped) < 200 and not stripped.endswith("?"):
        return GateDecision.STEER_NOW
    return GateDecision.ANSWER_LATER


def apply_gate(
    queue: SteeringQueue,
    *,
    running: bool,
) -> tuple[GateDecision, list[str], bool]:
    """Drain the queue and apply the gate.

    Returns (strongest decision, steer-now texts, aborted).
    Answer-later messages are re-queued in original order.
    """
    items = queue.drain()
    steer_texts: list[str] = []
    later: list[SteeringMessage] = []
    aborted = False
    leftover: list[SteeringMessage] = []

    for index, item in enumerate(items):
        decision = decide_gate(item, running=running)
        if decision is GateDecision.ABORT:
            aborted = True
            leftover = items[index + 1 :]
            break
        if decision is GateDecision.STEER_NOW:
            steer_texts.append(item.text)
        else:
            later.append(item)

    queue.requeue_front(later + leftover)
    if aborted:
        return GateDecision.ABORT, steer_texts, True
    if steer_texts:
        return GateDecision.STEER_NOW, steer_texts, False
    return GateDecision.ANSWER_LATER, [], False
