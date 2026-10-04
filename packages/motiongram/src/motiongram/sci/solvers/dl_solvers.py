"""Deep Learning numerical solvers for activation curves, loss landscapes, and optimization trajectories."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

import numpy as np

from motiongram.sci.schema import DataSourceSpec
from motiongram.sci.solvers.base import DataResult, DataSource


class DeepLearningDataSolver(DataSource):
    """Unified solver for Deep Learning data sources."""

    # Built-in Activation Functions & analytical derivatives
    ACTIVATIONS: dict[str, tuple[Callable[[np.ndarray], np.ndarray], Callable[[np.ndarray], np.ndarray]]] = {
        "sigmoid": (
            lambda x: 1.0 / (1.0 + np.exp(-np.clip(x, -50.0, 50.0))),
            lambda x: (1.0 / (1.0 + np.exp(-np.clip(x, -50.0, 50.0)))) * (1.0 - (1.0 / (1.0 + np.exp(-np.clip(x, -50.0, 50.0))))),
        ),
        "tanh": (
            lambda x: np.tanh(x),
            lambda x: 1.0 - np.tanh(x) ** 2,
        ),
        "relu": (
            lambda x: np.maximum(0.0, x),
            lambda x: np.where(x > 0.0, 1.0, 0.0),
        ),
        "leaky_relu": (
            lambda x: np.where(x > 0.0, x, 0.01 * x),
            lambda x: np.where(x > 0.0, 1.0, 0.01),
        ),
        "gelu": (
            lambda x: 0.5 * x * (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (x + 0.044715 * x**3))),
            lambda x: 0.5 * (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (x + 0.044715 * x**3))) +
                      0.5 * x * (1.0 - np.tanh(np.sqrt(2.0 / np.pi) * (x + 0.044715 * x**3))**2) *
                      np.sqrt(2.0 / np.pi) * (1.0 + 3.0 * 0.044715 * x**2),
        ),
        "elu": (
            lambda x: np.where(x > 0.0, x, np.exp(np.clip(x, -50.0, 0.0)) - 1.0),
            lambda x: np.where(x > 0.0, 1.0, np.exp(np.clip(x, -50.0, 0.0))),
        ),
        "silu": (
            lambda x: x / (1.0 + np.exp(-np.clip(x, -50.0, 50.0))),
            lambda x: (1.0 / (1.0 + np.exp(-np.clip(x, -50.0, 50.0)))) * (1.0 + x * (1.0 - (1.0 / (1.0 + np.exp(-np.clip(x, -50.0, 50.0)))))),
        ),
    }

    # Built-in Standard Loss Benchmark Functions
    LOSS_BENCHMARKS: dict[str, Callable[[float, float], float]] = {
        "quadratic": lambda x, y: 0.5 * (x**2 + 2.0 * y**2),
        "saddle": lambda x, y: x**2 - y**2,
        "ravine": lambda x, y: 0.05 * x**2 + 2.5 * y**2,
        "rosenbrock": lambda x, y: (1.0 - x)**2 + 10.0 * (y - x**2)**2,
        "beale": lambda x, y: (1.5 - x + x*y)**2 + (2.25 - x + x*y**2)**2,
    }

    def solve(self, spec: DataSourceSpec, quality: str = "final") -> DataResult:
        """Solve and return numerical coordinates for the given DL data source."""
        source_type = spec.source.lower()

        if source_type == "function_sampler":
            return self._solve_function_sampler(spec)
        elif source_type in ("analytical_surface", "loss_surface"):
            return self._solve_loss_surface(spec)
        elif source_type in ("optimization_tracer", "optimizer_path"):
            return self._solve_optimization_tracer(spec)
        elif source_type == "softmax_normalizer":
            return self._solve_softmax_normalizer(spec)
        else:
            raise ValueError(f"Unsupported Deep Learning data source: {spec.source}")

    def cache_key(self, spec: DataSourceSpec, quality: str = "final") -> str:
        """Generate deterministic cache key."""
        payload = spec.model_dump_json() + f":{quality}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _solve_function_sampler(self, spec: DataSourceSpec) -> DataResult:
        """Sample analytical 1D activation curve or set of curves."""
        x_min, x_max = -5.0, 5.0
        if spec.x_range and len(spec.x_range) >= 2:
            x_min, x_max = float(spec.x_range[0]), float(spec.x_range[1])

        samples = spec.samples or 200
        x_vals = np.linspace(x_min, x_max, samples)

        func_name = (spec.function or "relu").lower()
        metadata: dict[str, Any] = {"function": func_name, "x_range": [x_min, x_max]}

        # Multiple functions requested
        if spec.functions:
            func_data: dict[str, list[list[float]]] = {}
            for fn in spec.functions:
                fn_clean = fn.lower()
                if fn_clean in self.ACTIVATIONS:
                    f_val, _ = self.ACTIVATIONS[fn_clean]
                    y_vals = f_val(x_vals)
                    func_data[fn_clean] = np.column_stack([x_vals, y_vals, np.zeros_like(x_vals)]).tolist()
            metadata["multiple_functions"] = func_data

        if func_name in self.ACTIVATIONS:
            f_val, f_grad = self.ACTIVATIONS[func_name]
            y_vals = f_val(x_vals) if not spec.derivative else f_grad(x_vals)
        else:
            # Safe analytical evaluation fallback
            y_vals = np.maximum(0.0, x_vals)

        points = np.column_stack([x_vals, y_vals, np.zeros_like(x_vals)])
        metadata["y_min"] = float(np.min(y_vals))
        metadata["y_max"] = float(np.max(y_vals))

        return DataResult(points=points, metadata=metadata)

    def _get_loss_evaluator(self, spec: DataSourceSpec) -> Callable[[float, float], float]:
        """Return a callable (x, y) -> float loss value."""
        loss_eq = spec.loss_function or spec.equation or "quadratic"
        clean_key = loss_eq.lower().strip()

        if clean_key in self.LOSS_BENCHMARKS:
            return self.LOSS_BENCHMARKS[clean_key]

        # Parse string equation with math/numpy safe primitives
        safe_dict = {
            "sin": np.sin,
            "cos": np.cos,
            "exp": np.exp,
            "log": np.log,
            "sqrt": np.sqrt,
            "pi": np.pi,
            "abs": np.abs,
        }

        def custom_loss(x: float, y: float) -> float:
            ctx = dict(safe_dict)
            ctx["x"] = float(x)
            ctx["y"] = float(y)
            ctx["w1"] = float(x)
            ctx["w2"] = float(y)
            try:
                res = eval(loss_eq, {"__builtins__": {}}, ctx)
                return float(res)
            except Exception:
                return float(0.5 * (x**2 + y**2))

        return custom_loss

    def _solve_loss_surface(self, spec: DataSourceSpec) -> DataResult:
        """Compute 3D heightfield grid and contour info for a loss function."""
        evaluator = self._get_loss_evaluator(spec)

        grid_cfg = spec.grid or {}
        x_range = grid_cfg.get("x", [-3.0, 3.0])
        y_range = grid_cfg.get("y", [-3.0, 3.0])
        res = grid_cfg.get("resolution", 30)

        x_vals = np.linspace(x_range[0], x_range[1], res)
        y_vals = np.linspace(y_range[0], y_range[1], res)

        surface_points: list[list[float]] = []
        loss_matrix = np.zeros((res, res), dtype=float)

        for i, xv in enumerate(x_vals):
            for j, yv in enumerate(y_vals):
                z = evaluator(xv, yv)
                loss_matrix[i, j] = z
                surface_points.append([float(xv), float(yv), float(z)])

        points = np.array(surface_points, dtype=float)
        metadata = {
            "x_range": x_range,
            "y_range": y_range,
            "resolution": res,
            "z_min": float(np.min(loss_matrix)),
            "z_max": float(np.max(loss_matrix)),
            "equation": spec.loss_function or spec.equation or "quadratic",
        }

        return DataResult(points=points, metadata=metadata)

    def _solve_optimization_tracer(self, spec: DataSourceSpec) -> DataResult:
        """Simulate numerical optimization trajectory (SGD, Momentum, RMSProp, Adam)."""
        evaluator = self._get_loss_evaluator(spec)
        algo = (spec.algorithm or "sgd").lower().strip()

        start = spec.start if spec.start and len(spec.start) >= 2 else [2.0, 2.0]
        lr = spec.learning_rate or 0.1
        steps = spec.steps or 40

        eps = 1e-5

        def compute_grad(w: np.ndarray) -> np.ndarray:
            """Central difference numerical gradient."""
            gx = (evaluator(w[0] + eps, w[1]) - evaluator(w[0] - eps, w[1])) / (2.0 * eps)
            gy = (evaluator(w[0], w[1] + eps) - evaluator(w[0], w[1] - eps)) / (2.0 * eps)
            # Clip gradient to prevent explosion
            norm = np.sqrt(gx**2 + gy**2)
            if norm > 50.0:
                gx = (gx / norm) * 50.0
                gy = (gy / norm) * 50.0
            return np.array([gx, gy], dtype=float)

        trajectory: list[list[float]] = []
        loss_history: list[float] = []

        curr_w = np.array([float(start[0]), float(start[1])], dtype=float)
        v = np.zeros(2, dtype=float)  # For Momentum
        s = np.zeros(2, dtype=float)  # For RMSProp / Adam (2nd moment)
        m = np.zeros(2, dtype=float)  # For Adam (1st moment)

        beta1 = spec.beta1 if spec.beta1 is not None else 0.9
        beta2 = spec.beta2 if spec.beta2 is not None else 0.999
        momentum_coeff = spec.momentum if spec.momentum is not None else 0.9

        for t in range(1, steps + 1):
            curr_loss = evaluator(curr_w[0], curr_w[1])
            trajectory.append([float(curr_w[0]), float(curr_w[1]), float(curr_loss)])
            loss_history.append(float(curr_loss))

            grad = compute_grad(curr_w)

            if algo == "sgd":
                curr_w -= lr * grad
            elif algo == "momentum":
                v = momentum_coeff * v + lr * grad
                curr_w -= v
            elif algo == "rmsprop":
                s = beta2 * s + (1.0 - beta2) * (grad**2)
                curr_w -= (lr / (np.sqrt(s) + 1e-8)) * grad
            elif algo == "adam":
                m = beta1 * m + (1.0 - beta1) * grad
                s = beta2 * s + (1.0 - beta2) * (grad**2)
                m_hat = m / (1.0 - beta1**t)
                s_hat = s / (1.0 - beta2**t)
                curr_w -= (lr / (np.sqrt(s_hat) + 1e-8)) * m_hat
            else:
                # Default SGD
                curr_w -= lr * grad

        # Add final point
        final_loss = evaluator(curr_w[0], curr_w[1])
        trajectory.append([float(curr_w[0]), float(curr_w[1]), float(final_loss)])
        loss_history.append(float(final_loss))

        points = np.array(trajectory, dtype=float)
        metadata = {
            "algorithm": algo,
            "steps": steps,
            "learning_rate": lr,
            "loss_history": loss_history,
            "initial_loss": loss_history[0],
            "final_loss": final_loss,
            "loss_decreased": final_loss < loss_history[0],
        }

        return DataResult(points=points, metadata=metadata)

    def _solve_softmax_normalizer(self, spec: DataSourceSpec) -> DataResult:
        """Normalize logits using temperature-scaled Softmax."""
        logits = spec.logits if spec.logits else [2.0, 1.0, 0.1]
        T = spec.temperature if spec.temperature > 0 else 1.0

        z = np.array(logits, dtype=float)
        exp_z = np.exp((z - np.max(z)) / T)  # Numerically stable
        probs = exp_z / np.sum(exp_z)

        # Represent as 2D bar coordinates: [index, probability, logit]
        bars = []
        for i, (logit_val, p_val) in enumerate(zip(z, probs)):
            bars.append([float(i), float(p_val), float(logit_val)])

        points = np.array(bars, dtype=float)
        metadata = {
            "logits": [float(v) for v in z],
            "probabilities": [float(p) for p in probs],
            "sum": float(np.sum(probs)),
            "temperature": T,
        }

        return DataResult(points=points, metadata=metadata)
