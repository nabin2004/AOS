from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from educlaw.agent.steering import SteeringQueue
from educlaw.lsp.ty import TyClient
from educlaw.memory.store import DagestanMemory
from educlaw.permissions.gate import PermissionGate
from educlaw.sandbox.docker import DockerSandbox

EmitFn = Callable[[str, Any], None]


@dataclass(slots=True)
class AgentDeps:
    cwd: Path
    harness_home: Path
    memory: DagestanMemory
    steering: SteeringQueue
    gate: PermissionGate
    sandbox: DockerSandbox
    lsp: TyClient
    emit: EmitFn | None = None
