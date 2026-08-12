"""AOS agent tools registered as a PydanticAI FunctionToolset.

All public re-exports are lazy so lightweight imports like
``from tools.aos_speech_service import AOSSpeechService`` (Manim scenes)
do not pull DBOS-backed compile/write tools or pydantic_ai.
``from tools import manim_write`` / ``compile_manim_code`` still bind the
callables via ``__getattr__``, not the submodules.
"""

from __future__ import annotations

from typing import Any

__all__ = ["aos_toolset", "ToolDeps", "compile_manim_code", "manim_write"]


def __getattr__(name: str) -> Any:
    if name == "ToolDeps":
        from tools.deps import ToolDeps

        return ToolDeps
    if name == "aos_toolset":
        from tools.registry import aos_toolset

        return aos_toolset
    if name == "compile_manim_code":
        from tools.compile import compile_manim_code as _compile_manim_code

        # Cache on the package so later lookups skip __getattr__.
        globals()["compile_manim_code"] = _compile_manim_code
        return _compile_manim_code
    if name == "manim_write":
        from tools.manim_write import manim_write as _manim_write

        # Importing tools.manim_write sets this attr to the submodule; overwrite
        # with the callable so `from tools import manim_write` stays correct.
        globals()["manim_write"] = _manim_write
        return _manim_write
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
