"""Truncate CodeMode ModelRetry payloads before they fill the context window."""

from __future__ import annotations

from typing import Any

from pydantic_ai.exceptions import ModelRetry

from error_feedback import summarize_diagnostic_output
from export_traces.codemode_contract import (
    extract_run_code_body,
    run_code_has_tool_redefinition,
)

_PATCHED = False

_TOOL_REDEF_RETRY = (
    "Do not define compile_manim_code / manim_write / manim_read / "
    "synthesize_narration. They already exist inside run_code. "
    "Call them directly with await."
)


def install_codemode_retry_patch() -> None:
    """Summarize sandbox errors raised as ModelRetry from pydantic-ai-harness CodeMode."""
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
        if name == "run_code":
            body = extract_run_code_body(tool_args)
            if body is not None and run_code_has_tool_redefinition(body):
                raise ModelRetry(_TOOL_REDEF_RETRY)
        try:
            return await original(self, name, tool_args, ctx, tool)
        except ModelRetry as exc:
            raise ModelRetry(summarize_diagnostic_output(str(exc))) from exc

    _toolset.CodeModeToolset.call_tool = patched_call_tool  # type: ignore[method-assign]
    _PATCHED = True
