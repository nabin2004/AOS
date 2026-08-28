"""
AOS Manim Code: Code execution, memory layout, and call stack visualization plugin.
"""

from .structures.code_window import CodeWindow
from .structures.stack_frame import StackFrameMobject, CallStackMobject
from .execution.tracer import trace_factorial_execution, trace_fibonacci_execution
from .validators.code_validators import AstSyntaxValidator, StackDepthValidator

__version__ = "0.1.0"

__all__ = [
    "CodeWindow",
    "StackFrameMobject",
    "CallStackMobject",
    "trace_factorial_execution",
    "trace_fibonacci_execution",
    "AstSyntaxValidator",
    "StackDepthValidator",
]
