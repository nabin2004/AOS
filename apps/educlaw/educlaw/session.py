"""Assemble a session: settings, memory, agent, turn handler."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from educlaw.agent.deps import AgentDeps
from educlaw.agent.factory import build_agent
from educlaw.agent.loop import AgentTurnHandler
from educlaw.agent.steering import SteeringQueue
from educlaw.lsp.ty import TyClient
from educlaw.memory.files import ensure_memory_md
from educlaw.memory.store import DagestanMemory, make_extraction_client
from educlaw.permissions.gate import PermissionAction, PermissionGate
from educlaw.sandbox.docker import DockerSandbox
from educlaw.settings import Settings, resolve_harness_home

EmitFn = Callable[[str, Any], None]
PermissionResolver = Callable[[PermissionAction], Awaitable[bool]]


async def auto_allow(_action: PermissionAction) -> bool:
    return True


async def headless_deny(action: PermissionAction) -> bool:
    del action
    return False


def create_session(
    cwd: Path | None = None,
    settings: Settings | None = None,
    emit: EmitFn | None = None,
    *,
    yes: bool = False,
    headless: bool = False,
    permission_resolver: PermissionResolver | None = None,
) -> AgentTurnHandler:
    settings = settings or Settings.from_env()
    cwd = (cwd or Path.cwd()).resolve()
    harness_home = resolve_harness_home(cwd, settings)
    harness_home.mkdir(parents=True, exist_ok=True)
    ensure_memory_md(cwd)

    llm_client = None
    stub_memory = settings.memory_stub or settings.test_model
    if not stub_memory:
        llm_client = make_extraction_client(settings.model)

    memory = DagestanMemory(
        harness_home / "memory" / "graph.json",
        llm_client=llm_client,
        stub=stub_memory,
    )
    mode = "auto" if yes or settings.test_model else settings.permission_mode
    resolver = permission_resolver
    if resolver is None and (mode == "auto" or yes):
        resolver = auto_allow
    elif resolver is None and headless:
        resolver = headless_deny

    deps = AgentDeps(
        cwd=cwd,
        harness_home=harness_home,
        memory=memory,
        steering=SteeringQueue(),
        gate=PermissionGate(mode=mode, resolver=resolver),
        sandbox=DockerSandbox(
            cwd,
            image=settings.manim_image,
            docker_user=settings.docker_user,
            quality=settings.manim_quality,
        ),
        lsp=TyClient(cwd),
        emit=emit,
    )
    agent = build_agent(settings, cwd=cwd)
    return AgentTurnHandler(
        agent=agent,
        deps=deps,
        settings=settings,
        compaction_model=None if settings.test_model else settings.model,
    )
