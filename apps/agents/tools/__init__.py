"""AOS agent tools registered as a PydanticAI FunctionToolset.

`ToolDeps` / `aos_toolset` are lazy so `from tools.compile import ...`
works in SFT infer without `ir` / `pydantic_ai`. Write/compile callables are
re-exported eagerly (they only need optional DBOS) so
`from tools import manim_write` binds the function, not the submodule.
"""

from __future__ import annotations

from typing import Any

from tools.compile import compile_manim_code
from tools.manim_write import manim_write

__all__ = ["aos_toolset", "ToolDeps", "compile_manim_code", "manim_write"]


def __getattr__(name: str) -> Any:
    if name == "ToolDeps":
        from tools.deps import ToolDeps

        return ToolDeps
    if name == "aos_toolset":
        from tools.registry import aos_toolset

        return aos_toolset
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
