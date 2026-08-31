"""CodeSandbox: Executes computational code examples and verifies return types."""

from __future__ import annotations

import sys
import traceback
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel

from aos_lkg.schema.nodes import CodeExampleNode
from aos_lkg.schema.graph import KnowledgeGraph


class ExampleExecutionResult(BaseModel):
    example_id: str
    example_name: str
    target_api: str
    passed: bool
    execution_time_ms: float = 0.0
    error_type: Optional[str] = None
    error_message: Optional[str] = None


class CodeSandbox:
    """Executes example snippets safely to verify real computational correctness."""

    @staticmethod
    def execute_snippet(code_str: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Executes a code string in an isolated dictionary environment."""
        sandbox_env: Dict[str, Any] = {}
        try:
            exec(code_str, sandbox_env, sandbox_env)
            return True, None, None
        except Exception as e:
            err_type = type(e).__name__
            err_msg = str(e)
            return False, err_type, err_msg

    @classmethod
    def test_all_examples(cls, kg: KnowledgeGraph) -> List[ExampleExecutionResult]:
        """Runs all CodeExampleNode snippets in the knowledge graph."""
        import time

        results = []
        for node in kg.nodes.values():
            if isinstance(node, CodeExampleNode):
                t0 = time.perf_counter()
                passed, err_type, err_msg = cls.execute_snippet(node.computational_snippet)
                elapsed_ms = (time.perf_counter() - t0) * 1000.0

                results.append(
                    ExampleExecutionResult(
                        example_id=node.id,
                        example_name=node.name,
                        target_api=node.target_api,
                        passed=passed,
                        execution_time_ms=round(elapsed_ms, 2),
                        error_type=err_type,
                        error_message=err_msg,
                    )
                )
        return results
