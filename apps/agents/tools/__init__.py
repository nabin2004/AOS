"""AOS agent tools registered as a PydanticAI FunctionToolset."""

from tools.deps import ToolDeps
from tools.registry import aos_toolset

# Imports submodules to register tools on aos_toolset.
# from tools import compile as manim_write
from tools.compile import compile_manim_code
from tools.manim_write import manim_write

__all__ = ["aos_toolset", "ToolDeps","compile_manim_code", "manim_write"]
