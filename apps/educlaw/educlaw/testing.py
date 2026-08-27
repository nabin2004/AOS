"""Test helpers (not part of the runtime harness API)."""

from __future__ import annotations

from pathlib import Path

from educlaw.agent.deps import AgentDeps
from educlaw.agent.steering import SteeringQueue
from educlaw.lsp.ty import TyClient
from educlaw.memory.store import DagestanMemory
from educlaw.permissions.gate import PermissionGate
from educlaw.sandbox.docker import DockerSandbox
from educlaw.settings import Settings


def make_settings(**overrides) -> Settings:
    data = dict(
        model="test",
        api_key=None,
        harness_home=None,
        context_window_tokens=16_000,
        compaction_threshold=0.7,
        compaction_tail=6,
        memory_digest_every=99,
        memory_stub=True,
        test_model=True,
        permission_mode="auto",
        manim_image="manimcommunity/manim:stable",
        docker_user=None,
        manim_quality="m",
        kitaru=False,
        logfire=False,
    )
    data.update(overrides)
    return Settings(**data)


def make_deps(tmp_path: Path, **gate_kwargs) -> AgentDeps:
    return AgentDeps(
        cwd=tmp_path,
        harness_home=tmp_path / ".aos",
        memory=DagestanMemory(tmp_path / "graph.json", stub=True),
        steering=SteeringQueue(),
        gate=PermissionGate(mode=gate_kwargs.get("mode", "auto"), resolver=gate_kwargs.get("resolver")),
        sandbox=DockerSandbox(tmp_path),
        lsp=TyClient(tmp_path),
    )
