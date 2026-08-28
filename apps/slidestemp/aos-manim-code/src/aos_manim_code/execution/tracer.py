from __future__ import annotations

from typing import Optional, Dict, Any, List


def trace_factorial_execution(n: int) -> Dict[str, Any]:
    """Traces recursive execution of factorial."""
    events: List[Dict[str, Any]] = []

    def fact(val: int, depth: int) -> int:
        events.append({
            "type": "call",
            "func": "factorial",
            "args": {"n": val},
            "depth": depth,
        })
        if val <= 1:
            res = 1
        else:
            res = val * fact(val - 1, depth + 1)

        events.append({
            "type": "return",
            "func": "factorial",
            "args": {"n": val},
            "return_value": res,
            "depth": depth,
        })
        return res

    final_result = fact(n, depth=0)
    return {
        "n": n,
        "result": final_result,
        "events": events,
    }


def trace_fibonacci_execution(n: int) -> Dict[str, Any]:
    """Traces recursive execution of Fibonacci."""
    events: List[Dict[str, Any]] = []

    def fib(val: int, depth: int) -> int:
        events.append({
            "type": "call",
            "func": "fib",
            "args": {"n": val},
            "depth": depth,
        })
        if val <= 0:
            res = 0
        elif val == 1:
            res = 1
        else:
            res = fib(val - 1, depth + 1) + fib(val - 2, depth + 1)

        events.append({
            "type": "return",
            "func": "fib",
            "args": {"n": val},
            "return_value": res,
            "depth": depth,
        })
        return res

    final_result = fib(n, depth=0)
    return {
        "n": n,
        "result": final_result,
        "events": events,
    }
