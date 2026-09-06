"""Truncate CodeMode ModelRetry payloads and auto-salvage bare Manim source."""

from __future__ import annotations

import logging
from typing import Any

from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.messages import ToolReturn

from error_feedback import summarize_diagnostic_output

logger = logging.getLogger(__name__)
_PATCHED = False


def install_codemode_retry_patch() -> None:
    """Summarize sandbox errors and auto-execute bare Manim in CodeMode."""
    global _PATCHED
    if _PATCHED:
        return

    from pydantic_ai_harness.code_mode import _toolset

    original = _toolset.CodeModeToolset.call_tool

    async def patched_call_tool(
        self: Any,
        name: str,
        tool_args: dict[str, Any],
        ctx: Any,
        tool: Any,
    ) -> Any:
        raw_code = ""
        if isinstance(tool_args, dict):
            raw_code = str(tool_args.get("code") or "")
        elif isinstance(tool_args, str):
            raw_code = tool_args

        # Fast path: If the model generated bare Manim code directly into run_code
        # without orchestrating tools (e.g. from manim import * / class Scene),
        # salvage and compile directly instead of failing in the Monty sandbox.
        if raw_code.strip() and ("from manim" in raw_code or "class " in raw_code) and "manim_write" not in raw_code:
            try:
                from tools.manim_source import extract_codemode_dump
                extracted = extract_codemode_dump(raw_code)
                if extracted and extracted.code and extracted.scene_name:
                    from tools.manim_write import manim_write
                    from tools.compile import compile_manim_code

                    w_res = manim_write(code=extracted.code, scene_name=extracted.scene_name)
                    c_res = compile_manim_code(code=extracted.code, scene_name=extracted.scene_name)
                    return ToolReturn(
                        return_value=c_res,
                        metadata={
                            "code_mode": True,
                            "direct_salvage": True,
                            "last_write": w_res,
                        },
                    )
            except Exception as salvage_err:
                logger.debug("Direct CodeMode salvage skipped: %s", salvage_err)

        try:
            return await original(self, name, tool_args, ctx, tool)
        except ModelRetry as exc:
            # Secondary salvage: If Monty rejected the snippet, check if it contains valid Manim source
            if raw_code.strip():
                try:
                    from tools.manim_source import extract_codemode_dump
                    extracted = extract_codemode_dump(raw_code)
                    if extracted and extracted.code and extracted.scene_name:
                        from tools.manim_write import manim_write
                        from tools.compile import compile_manim_code

                        w_res = manim_write(code=extracted.code, scene_name=extracted.scene_name)
                        c_res = compile_manim_code(code=extracted.code, scene_name=extracted.scene_name)
                        return ToolReturn(
                            return_value=c_res,
                            metadata={
                                "code_mode": True,
                                "direct_salvage": True,
                                "last_write": w_res,
                            },
                        )
                except Exception as secondary_err:
                    logger.debug("Secondary CodeMode salvage skipped: %s", secondary_err)

            diag = summarize_diagnostic_output(str(exc))
            hint = (
                "\n[CodeMode Format Guide]: Do NOT put `from manim import *` at the top level of run_code. "
                "Put your entire Manim scene inside a triple-quoted string variable `code = '''...'''` "
                "and call `await manim_write(code=code, scene_name='ClassName')` "
                "and `await compile_manim_code(code=code, scene_name='ClassName')`."
            )
            raise ModelRetry(f"{diag}\n{hint}") from exc

    _toolset.CodeModeToolset.call_tool = patched_call_tool  # type: ignore[method-assign]
    _PATCHED = True
