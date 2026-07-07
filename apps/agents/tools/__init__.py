"""AOS agent tools registered as a PydanticAI FunctionToolset."""

from tools.deps import ToolDeps
from tools.registry import aos_toolset

# Imports submodules to register tools on aos_toolset.
from tools import compute, compile as compile_mod, lookup, qr, render, validate  # noqa: F401

__all__ = ["aos_toolset", "ToolDeps"]
