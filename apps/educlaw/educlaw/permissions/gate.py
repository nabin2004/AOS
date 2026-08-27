"""Claude Code-shaped permission modes for sandbox tools."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

PermissionMode = Literal["default", "edit", "auto"]
ActionKind = Literal["read", "write", "bash", "render", "destructive"]

PermissionResolver = Callable[["PermissionAction"], Awaitable[bool]]

_DESTRUCTIVE = re.compile(
    r"(?:\brm\b|\brm\s+-r|\bdel\s+/s|\bgit\s+reset\s+--hard|\bgit\s+clean\b"
    r"|\bmkfs\b|\bdd\s+if=|\bformat\b|\bshred\b)",
    re.IGNORECASE,
)


@dataclass(slots=True, frozen=True)
class PermissionAction:
    kind: ActionKind
    summary: str
    detail: str = ""


def classify_command(command: str) -> ActionKind:
    if _DESTRUCTIVE.search(command or ""):
        return "destructive"
    return "bash"


class PermissionGate:
    """Ask before risky (default), writes (edit), or allow everything (auto)."""

    def __init__(
        self,
        mode: PermissionMode = "default",
        resolver: PermissionResolver | None = None,
    ) -> None:
        if mode not in {"default", "edit", "auto"}:
            raise ValueError(f"unknown permission mode: {mode}")
        self.mode: PermissionMode = mode
        self.resolver = resolver
        self._future: asyncio.Future[bool] | None = None

    def needs_approval(self, action: PermissionAction) -> bool:
        if self.mode == "auto":
            return False
        if action.kind == "read":
            return False
        if self.mode == "default":
            return action.kind in {"bash", "render", "destructive"}
        return action.kind in {"write", "bash", "render", "destructive"}

    async def approve(
        self,
        action: PermissionAction,
        emit: Callable[[str, object], None] | None = None,
    ) -> bool:
        if not self.needs_approval(action):
            return True
        if self.resolver is not None:
            return await self.resolver(action)
        loop = asyncio.get_running_loop()
        self._future = loop.create_future()
        if emit:
            emit(
                "permission_required",
                {"kind": action.kind, "summary": action.summary, "detail": action.detail},
            )
        try:
            return await asyncio.wait_for(self._future, timeout=300)
        except TimeoutError:
            return False
        finally:
            self._future = None

    def answer(self, allowed: bool) -> bool:
        if self._future is None or self._future.done():
            return False
        self._future.set_result(allowed)
        return True

    @property
    def pending(self) -> bool:
        return self._future is not None and not self._future.done()
