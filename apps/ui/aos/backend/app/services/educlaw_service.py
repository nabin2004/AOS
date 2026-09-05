"""EduClaw harness runner and WebSocket streaming service for AOS UI & Backend."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Coroutine

from fastapi import WebSocket

def _find_educlaw_path() -> Path | None:
    container_candidates = [
        Path("/app/apps/educlaw"),
        Path("/app/educlaw"),
        Path("/educlaw"),
    ]
    for candidate in container_candidates:
        if candidate.is_dir():
            return candidate
    curr = Path(__file__).resolve()
    for parent in [curr, *curr.parents]:
        candidate = parent / "apps" / "educlaw"
        if candidate.is_dir():
            return candidate
        candidate_direct = parent / "educlaw"
        if candidate_direct.is_dir():
            return candidate_direct
    return None

educlaw_path = _find_educlaw_path()
if educlaw_path and str(educlaw_path) not in sys.path:
    sys.path.insert(0, str(educlaw_path))


try:
    from educlaw.agent.loop import AgentTurnHandler
    from educlaw.permissions.gate import PermissionAction
    from educlaw.session import create_session
    from educlaw.settings import Settings
    HAS_EDUCLAW = True
except Exception as _err:
    logging.getLogger(__name__).warning("EduClaw import failed: %s", _err)
    HAS_EDUCLAW = False
    AgentTurnHandler = None
    PermissionAction = None
    create_session = None
    Settings = None


logger = logging.getLogger(__name__)


class EduClawService:
    """Manages EduClaw harness instances and streams execution to the frontend."""

    def __init__(
        self,
        websocket: WebSocket | None = None,
        workspace_dir: Path | None = None,
        headless: bool = True,
        auto_approve: bool = True,
        model_name: str | None = None,
        permission_callback: Callable[[PermissionAction], Coroutine[Any, Any, bool]] | None = None,
    ) -> None:
        self.websocket = websocket
        self.workspace_dir = workspace_dir or Path.cwd()
        self.headless = headless
        self.auto_approve = auto_approve
        self.model_name = model_name
        self.permission_callback = permission_callback
        self._handler: AgentTurnHandler | None = None
        self._permission_futures: dict[str, asyncio.Future[bool]] = {}

    def _emit_event(self, event: str, payload: Any) -> None:
        """Callback passed to EduClaw to forward harness events over WebSocket."""
        if self.websocket is None:
            return

        async def _send() -> None:
            try:
                from app.services.agent import send_event
                await send_event(
                    self.websocket,
                    "educlaw_event",
                    {"event": event, "payload": payload},
                )
                # Map specific tool events for standard UI components
                if event == "tool":
                    await send_event(
                        self.websocket,
                        "tool_call",
                        {
                            "name": payload.get("name", "educlaw_tool"),
                            "arguments": payload,
                        },
                    )
            except Exception as e:
                logger.debug("Failed to emit educlaw event: %s", e)

        asyncio.create_task(_send())

    async def _resolve_permission(self, action: PermissionAction) -> bool:
        """Resolve permissions interactively or automatically."""
        if self.auto_approve:
            return True
        if self.permission_callback:
            return await self.permission_callback(action)
        if self.websocket:
            action_id = f"{action.kind}-{id(action)}"
            loop = asyncio.get_running_loop()
            fut: asyncio.Future[bool] = loop.create_future()
            self._permission_futures[action_id] = fut
            try:
                from app.services.agent import send_event
                await send_event(
                    self.websocket,
                    "permission_request",
                    {
                        "action_id": action_id,
                        "kind": action.kind,
                        "summary": action.summary,
                        "detail": action.detail,
                    },
                )
                return await asyncio.wait_for(fut, timeout=120.0)
            except Exception as exc:
                logger.warning("Permission prompt timed out or failed: %s", exc)
                return False
            finally:
                self._permission_futures.pop(action_id, None)
        return not self.headless

    def handle_permission_response(self, action_id: str, approved: bool) -> None:
        fut = self._permission_futures.get(action_id)
        if fut and not fut.done():
            fut.set_result(approved)

    def get_handler(self) -> AgentTurnHandler:
        if not HAS_EDUCLAW or Settings is None or create_session is None:
            raise RuntimeError(
                "EduClaw harness is not available in the backend environment. "
                "Ensure apps/educlaw is mounted to /app/apps/educlaw."
            )
        if self._handler is None:
            settings = Settings.from_env()
            if self.model_name:
                settings.model = self.model_name
            self._handler = create_session(
                cwd=self.workspace_dir,
                settings=settings,
                emit=self._emit_event,
                yes=self.auto_approve,
                headless=self.headless,
                permission_resolver=self._resolve_permission,
            )
        return self._handler

    async def run_turn(self, user_prompt: str) -> str:
        """Run one EduClaw turn and return output."""
        handler = self.get_handler()
        return await handler.run_turn(user_prompt)

    async def get_memory_graph(self) -> dict[str, Any]:
        """Fetch the Dagestan temporal memory graph."""
        handler = self.get_handler()
        try:
            return await handler.deps.memory.read_graph()
        except Exception as e:
            logger.error("Failed to read Dagestan memory graph: %s", e)
            return {"nodes": [], "edges": [], "error": str(e)}

    async def curate_memory(self) -> dict[str, Any]:
        """Trigger Dagestan memory curation."""
        handler = self.get_handler()
        try:
            result = await handler.deps.memory.curate()
            return {"ok": True, "result": result}
        except Exception as e:
            logger.error("Failed to curate Dagestan memory: %s", e)
            return {"ok": False, "error": str(e)}
