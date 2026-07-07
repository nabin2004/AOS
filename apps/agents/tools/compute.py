from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import chess
import numpy as np
import pandas as pd
import scipy.integrate
import sympy
from ir.manim_ir import Computation, ComputeLibrary
from pydantic_ai import RunContext

from tools.deps import ToolDeps
from tools.registry import aos_toolset

NUMPY_ROUTINES = {"linspace", "array", "meshgrid"}
SCIPY_ROUTINES = {"solve_ivp"}
SYMPY_ROUTINES = {"simplify", "expand", "latex"}
PANDAS_ROUTINES = {"read_csv"}
CHESS_ROUTINES = {"board_from_fen", "legal_moves"}


def _lorenz_system(_t: float, state: list[float], sigma: float, rho: float, beta: float) -> list[float]:
    x, y, z = state
    return [sigma * (y - x), x * (rho - z) - y, x * y - beta * z]


def _run_numpy(routine: str, params: dict[str, Any]) -> Any:
    if routine == "linspace":
        return np.linspace(**params).tolist()
    if routine == "array":
        return np.array(params.get("values", [])).tolist()
    if routine == "meshgrid":
        xs = np.linspace(params["x_min"], params["x_max"], params.get("n", 50))
        ys = np.linspace(params["y_min"], params["y_max"], params.get("n", 50))
        xg, yg = np.meshgrid(xs, ys)
        return {"x": xg.tolist(), "y": yg.tolist()}
    raise ValueError(f"unsupported numpy routine {routine!r}")


def _run_scipy(routine: str, params: dict[str, Any]) -> Any:
    if routine != "solve_ivp":
        raise ValueError(f"unsupported scipy routine {routine!r}")

    sigma = float(params["sigma"])
    rho = float(params["rho"])
    beta = float(params["beta"])
    y0 = params.get("y0", [1.0, 1.0, 1.0])
    t_end = float(params.get("t_end", 40.0))
    n = int(params.get("n", 6000))

    t_eval = np.linspace(0, t_end, n)
    sol = scipy.integrate.solve_ivp(
        _lorenz_system,
        (0, t_end),
        y0,
        args=(sigma, rho, beta),
        t_eval=t_eval,
        dense_output=False,
    )
    return sol.y.T.tolist()


def _run_sympy(routine: str, params: dict[str, Any]) -> Any:
    expr = sympy.sympify(params.get("expr", "0"))
    if routine == "simplify":
        return str(sympy.simplify(expr))
    if routine == "expand":
        return str(sympy.expand(expr))
    if routine == "latex":
        return sympy.latex(expr)
    raise ValueError(f"unsupported sympy routine {routine!r}")


def _run_pandas(routine: str, params: dict[str, Any], workspace_dir: Path) -> Any:
    if routine != "read_csv":
        raise ValueError(f"unsupported pandas routine {routine!r}")

    path = Path(params["path"])
    if not path.is_absolute():
        path = workspace_dir / path
    path = path.resolve()
    if workspace_dir.resolve() not in path.parents and path != workspace_dir.resolve():
        raise ValueError(f"CSV path must be under workspace: {path}")
    if not path.exists():
        raise ValueError(f"CSV file not found: {path}")

    df = pd.read_csv(path)
    return {"columns": df.columns.tolist(), "rows": df.values.tolist()}


def _run_chess(routine: str, params: dict[str, Any]) -> Any:
    if routine == "board_from_fen":
        board = chess.Board(params.get("fen", chess.STARTING_FEN))
        return {"fen": board.fen(), "turn": "white" if board.turn else "black"}
    if routine == "legal_moves":
        board = chess.Board(params.get("fen", chess.STARTING_FEN))
        return [move.uci() for move in board.legal_moves]
    raise ValueError(f"unsupported python_chess routine {routine!r}")


def execute_computation(computation: Computation, workspace_dir: Path | None = None) -> Any:
    """Run a whitelisted Computation and return a JSON-serializable result."""
    lib = computation.library
    routine = computation.routine
    params = computation.params

    if lib == ComputeLibrary.NUMPY:
        if routine not in NUMPY_ROUTINES:
            raise ValueError(f"unsupported numpy routine {routine!r}; allowed: {sorted(NUMPY_ROUTINES)}")
        return _run_numpy(routine, params)

    if lib == ComputeLibrary.SCIPY:
        if routine not in SCIPY_ROUTINES:
            raise ValueError(f"unsupported scipy routine {routine!r}; allowed: {sorted(SCIPY_ROUTINES)}")
        return _run_scipy(routine, params)

    if lib == ComputeLibrary.SYMPY:
        if routine not in SYMPY_ROUTINES:
            raise ValueError(f"unsupported sympy routine {routine!r}; allowed: {sorted(SYMPY_ROUTINES)}")
        return _run_sympy(routine, params)

    if lib == ComputeLibrary.PANDAS:
        if routine not in PANDAS_ROUTINES:
            raise ValueError(f"unsupported pandas routine {routine!r}; allowed: {sorted(PANDAS_ROUTINES)}")
        if workspace_dir is None:
            raise ValueError("pandas routines require workspace_dir")
        return _run_pandas(routine, params, workspace_dir)

    if lib == ComputeLibrary.PYTHON_CHESS:
        if routine not in CHESS_ROUTINES:
            raise ValueError(
                f"unsupported python_chess routine {routine!r}; allowed: {sorted(CHESS_ROUTINES)}"
            )
        return _run_chess(routine, params)

    raise ValueError(f"unsupported library {lib.value!r}")


@aos_toolset.tool
def run_computation(ctx: RunContext[ToolDeps], computation_json: str) -> str:
    """Execute a Computation IR record using whitelisted numpy/scipy/sympy/pandas/chess routines."""
    computation = Computation.model_validate_json(computation_json)
    result = execute_computation(computation, ctx.deps.workspace_dir)
    return json.dumps({"id": computation.id, "result": result})
