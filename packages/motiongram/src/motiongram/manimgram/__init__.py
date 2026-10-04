"""ManimGram: Declarative animation DSL and transpiler targeting ManimCE."""

from motiongram.manimgram.compiler import compile_dsl, compile_file
from motiongram.manimgram.llm import get_json_schema, get_system_prompt
from motiongram.manimgram.runner import RenderResult, render_scene
from motiongram.manimgram.schema import ManimGramScene
from motiongram.manimgram.selectors import SelectorRegistry

__all__ = [
    "ManimGramScene",
    "SelectorRegistry",
    "compile_dsl",
    "compile_file",
    "get_json_schema",
    "get_system_prompt",
    "render_scene",
    "RenderResult",
]
