"""Base node class for animation pipeline graph steps."""

from __future__ import annotations

from typing import Any, Callable, Coroutine
from pydantic_graph import BaseNode

from animation_pipeline.state import AnimationState
from llm_retry import execute_with_llm_retry
from openai_compatible import format_custom_endpoint_error


class BaseAnimationNode:
    """Abstract mixin encapsulating retry execution, subject normalization, and error normalization."""

    @staticmethod
    def subject_str(subject: Any) -> str:
        """Normalize subject enum or string representation."""
        if hasattr(subject, "value"):
            return str(subject.value)
        return str(subject)

    async def execute_agent_call(
        self,
        call_fn: Callable[[], Coroutine[Any, Any, Any]],
        operation_name: str,
    ) -> Any:
        """Wrap an agent call with the standard exponential retry and jitter policy."""
        return await execute_with_llm_retry(call_fn, operation_name=operation_name)

    def format_error(self, exc: Exception | str) -> str:
        """Format an exception into a user-friendly diagnostic string."""
        return format_custom_endpoint_error(exc)
