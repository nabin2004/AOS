"""Continuous and discrete dynamical systems solver plugin using scipy.integrate.solve_ivp."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp

from motiongram.sci.schema import DataSourceSpec
from motiongram.sci.solvers.base import DataResult, DataSource
from motiongram.sci.solvers.cache import load_cached_result, save_cached_result


# ── Canonical Continuous Attractor Systems ────────────────────────────────────

def lorenz_system(t: float, state: np.ndarray, params: dict[str, float]) -> list[float]:
    """Lorenz attractor system equations."""
    x, y, z = state[:3]
    sigma = params.get("sigma", 10.0)
    rho = params.get("rho", 28.0)
    beta = params.get("beta", 8.0 / 3.0)
    return [
        sigma * (y - x),
        x * (rho - z) - y,
        x * y - beta * z,
    ]


def rossler_system(t: float, state: np.ndarray, params: dict[str, float]) -> list[float]:
    """Rössler attractor system equations."""
    x, y, z = state[:3]
    a = params.get("a", 0.2)
    b = params.get("b", 0.2)
    c = params.get("c", 5.7)
    return [
        -y - z,
        x + a * y,
        b + z * (x - c),
    ]


def fixed_point_system(t: float, state: np.ndarray, params: dict[str, float]) -> list[float]:
    """Fixed-point (point) attractor: damped spiral focus."""
    x, y, z = state[:3]
    a = params.get("a", 0.4)
    omega = params.get("omega", 2.0)
    b = params.get("b", 0.6)
    return [
        -a * x - omega * y,
        omega * x - a * y,
        -b * z,
    ]


def limit_cycle_system(t: float, state: np.ndarray, params: dict[str, float]) -> list[float]:
    """Supercritical Hopf limit cycle attractor."""
    x, y, z = state[:3]
    mu = params.get("mu", 4.0)
    omega = params.get("omega", 2.0)
    c = params.get("c", 1.0)
    r2 = x**2 + y**2
    return [
        (mu - r2) * x - omega * y,
        omega * x + (mu - r2) * y,
        -c * (z - 0.5 * np.sin(np.sqrt(max(r2, 1e-6)))),
    ]


def torus_system(t: float, state: np.ndarray, params: dict[str, float]) -> list[float]:
    """Langford 3D quasiperiodic torus attractor flow."""
    x, y, z = state[:3]
    lam = params.get("lambda", 0.6)
    omega = params.get("omega", 3.5)
    c = params.get("c", 0.2)
    d = params.get("d", 0.5)
    return [
        (lam - z) * x - omega * y,
        omega * x + (lam - z) * y,
        c * z + d * (x**2 + y**2) - z**3,
    ]


def chua_system(t: float, state: np.ndarray, params: dict[str, float]) -> list[float]:
    """Chua circuit double-scroll chaotic attractor."""
    x, y, z = state[:3]
    alpha = params.get("alpha", 10.0)
    beta = params.get("beta", 14.87)
    m0 = params.get("m0", -1.27)
    m1 = params.get("m1", -0.68)
    h = m1 * x + 0.5 * (m0 - m1) * (abs(x + 1.0) - abs(x - 1.0))
    return [
        alpha * (y - x - h),
        x - y + z,
        -beta * y,
    ]


def multiscroll_system(t: float, state: np.ndarray, params: dict[str, float]) -> list[float]:
    """Suykens generalized multiscroll chaotic attractor."""
    x, y, z = state[:3]
    alpha = params.get("alpha", 9.0)
    beta = params.get("beta", 14.28)
    a = params.get("a", 1.0)
    b = params.get("b", 1.1)
    fx = b * (np.pi / (2.0 * a)) * np.sin((np.pi * x) / (2.0 * a))
    return [
        alpha * (y - fx),
        x - y + z,
        -beta * y,
    ]


def chen_system(t: float, state: np.ndarray, params: dict[str, float]) -> list[float]:
    """Chen strange attractor system."""
    x, y, z = state[:3]
    a = params.get("a", 35.0)
    b = params.get("b", 3.0)
    c = params.get("c", 28.0)
    return [
        a * (y - x),
        (c - a) * x - x * z + c * y,
        x * y - b * z,
    ]


def sprott_system(t: float, state: np.ndarray, params: dict[str, float]) -> list[float]:
    """Sprott minimal chaotic attractor (Case B)."""
    x, y, z = state[:3]
    a = params.get("a", 1.0)
    return [
        y * z,
        x - y,
        a - x * y,
    ]


def rabinovich_fabrikant_system(
    t: float, state: np.ndarray, params: dict[str, float]
) -> list[float]:
    """Rabinovich–Fabrikant complex attractor."""
    x, y, z = state[:3]
    alpha = params.get("alpha", 0.14)
    gamma = params.get("gamma", 0.10)
    return [
        y * (z - 1.0 + x**2) + gamma * x,
        x * (3.0 * z + 1.0 - x**2) + gamma * y,
        -2.0 * z * (alpha + x * y),
    ]


def shilnikov_system(t: float, state: np.ndarray, params: dict[str, float]) -> list[float]:
    """Shilnikov saddle-focus homoclinic chaos attractor."""
    x, y, z = state[:3]
    a = params.get("a", 5.5)
    b = params.get("b", 3.5)
    c = params.get("c", 1.0)
    d = params.get("d", 1.0)
    return [
        y,
        z,
        -a * x - b * y - c * z + d * (x**2),
    ]


def hyperchaotic_system(t: float, state: np.ndarray, params: dict[str, float]) -> list[float]:
    """4D Rössler Hyperchaotic system with two positive Lyapunov exponents."""
    x = state[0]
    y = state[1]
    z = state[2]
    w = state[3] if len(state) > 3 else 0.0
    a = params.get("a", 0.25)
    b = params.get("b", 3.0)
    c = params.get("c", 0.5)
    d = params.get("d", 0.05)
    return [
        -y - z,
        x + a * y + w,
        b + x * z,
        -c * z + d * w,
    ]


def hidden_attractor_system(t: float, state: np.ndarray, params: dict[str, float]) -> list[float]:
    """Wei hidden attractor system with zero equilibria."""
    x, y, z = state[:3]
    a = params.get("a", 10.0)
    b = params.get("b", 2.0)
    c = params.get("c", 10.0)
    return [
        a * (y - x),
        -x * z + c,
        x * y - b,
    ]


def aizerman_system(t: float, state: np.ndarray, params: dict[str, float]) -> list[float]:
    """Aizerman nonlinear control system demonstrating hidden oscillations."""
    x, y, z = state[:3]
    a = params.get("a", 2.0)
    b = params.get("b", 1.0)
    c = params.get("c", 0.1)
    k = params.get("k", 1.5)
    return [
        y,
        z,
        -a * z - b * y - c * x - k * np.tanh(x),
    ]


def chaotic_saddle_system(t: float, state: np.ndarray, params: dict[str, float]) -> list[float]:
    """Transient chaos near a chaotic saddle in subcritical Lorenz."""
    x, y, z = state[:3]
    sigma = params.get("sigma", 10.0)
    rho = params.get("rho", 21.5)
    beta = params.get("beta", 8.0 / 3.0)
    return [
        sigma * (y - x),
        x * (rho - z) - y,
        x * y - beta * z,
    ]


def solenoid_system(t: float, state: np.ndarray, params: dict[str, float]) -> list[float]:
    """Continuous Smale–Williams solenoid flow in 3D."""
    x, y, z = state[:3]
    r = np.sqrt(x**2 + y**2)
    theta = np.arctan2(y, x)
    R0 = params.get("R0", 3.0)
    omega = params.get("omega", 1.5)
    lam = params.get("lambda", 0.8)
    dx = -lam * (r - R0) * np.cos(theta) - omega * y + 0.3 * np.cos(2 * theta)
    dy = -lam * (r - R0) * np.sin(theta) + omega * x + 0.3 * np.sin(2 * theta)
    dz = -0.5 * z + 0.4 * np.sin(2 * theta)
    return [dx, dy, dz]


def milnor_system(t: float, state: np.ndarray, params: dict[str, float]) -> list[float]:
    """Milnor attractor system with riddled basin behavior."""
    x, y, z = state[:3]
    a = params.get("a", 1.4)
    b = params.get("b", 0.3)
    return [
        y - a * x**3,
        -x + b * y - z,
        -0.5 * z + x**2,
    ]


def coexisting_attractors_system(
    t: float, state: np.ndarray, params: dict[str, float]
) -> list[float]:
    """Multistable system with coexisting attractors."""
    x, y, z = state[:3]
    a = params.get("a", 1.0)
    b = params.get("b", 0.8)
    return [
        y,
        -x + y * (1.0 - x**2 - y**2) + z,
        -b * z + a * x**2,
    ]


def double_pendulum_system(
    t: float, state: np.ndarray, params: dict[str, float]
) -> list[float]:
    """Double pendulum equations in angular coordinates [th1, th2, w1, w2]."""
    th1, th2, w1, w2 = state[:4]
    g = params.get("g", 9.81)
    m1 = params.get("m1", 1.0)
    m2 = params.get("m2", 1.0)
    l1 = params.get("l1", 1.0)
    l2 = params.get("l2", 1.0)

    delta = th1 - th2
    den1 = l1 * (2 * m1 + m2 - m2 * np.cos(2 * th1 - 2 * th2))
    den2 = l2 * (2 * m1 + m2 - m2 * np.cos(2 * th1 - 2 * th2))

    num1 = (
        -g * (2 * m1 + m2) * np.sin(th1)
        - m2 * g * np.sin(th1 - 2 * th2)
        - 2 * np.sin(delta) * m2 * (w2**2 * l2 + w1**2 * l1 * np.cos(delta))
    )
    d_w1 = num1 / den1

    num2 = 2 * np.sin(delta) * (
        w1**2 * l1 * (m1 + m2)
        + g * (m1 + m2) * np.cos(th1)
        + w2**2 * l2 * m2 * np.cos(delta)
    )
    d_w2 = num2 / den2

    return [w1, w2, d_w1, d_w2]


def lotka_volterra_system(
    t: float, state: np.ndarray, params: dict[str, float]
) -> list[float]:
    """Lotka-Volterra predator-prey system."""
    x, y = state[:2]
    alpha = params.get("alpha", 1.5)
    beta = params.get("beta", 1.0)
    delta = params.get("delta", 0.75)
    gamma = params.get("gamma", 1.0)
    dx = alpha * x - beta * x * y
    dy = delta * x * y - gamma * y
    dz = 0.0 if len(state) > 2 else 0.0
    return [dx, dy, dz] if len(state) > 2 else [dx, dy]


def van_der_pol_system(
    t: float, state: np.ndarray, params: dict[str, float]
) -> list[float]:
    """Van der Pol oscillator."""
    x, y = state[:2]
    mu = params.get("mu", 1.0)
    dx = y
    dy = mu * (1.0 - x**2) * y - x
    dz = 0.0 if len(state) > 2 else 0.0
    return [dx, dy, dz] if len(state) > 2 else [dx, dy]


MODEL_REGISTRY: dict[
    str, Callable[[float, np.ndarray, dict[str, float]], list[float]]
] = {
    # Canonical attractors
    "fixed_point": fixed_point_system,
    "limit_cycle": limit_cycle_system,
    "torus": torus_system,
    "quasiperiodic": torus_system,
    "lorenz": lorenz_system,
    "rossler": rossler_system,
    "chua": chua_system,
    "double_scroll": chua_system,
    "multiscroll": multiscroll_system,
    "chen": chen_system,
    "sprott": sprott_system,
    "sprott_b": sprott_system,
    "rabinovich_fabrikant": rabinovich_fabrikant_system,
    "shilnikov": shilnikov_system,
    "hyperchaotic": hyperchaotic_system,
    "hidden_attractor": hidden_attractor_system,
    "leonov": hidden_attractor_system,
    "aizerman": aizerman_system,
    "chaotic_saddle": chaotic_saddle_system,
    "transient": chaotic_saddle_system,
    "solenoid": solenoid_system,
    "milnor": milnor_system,
    "coexisting_attractors": coexisting_attractors_system,
    # Oscillators & classic systems
    "double_pendulum": double_pendulum_system,
    "lotka_volterra": lotka_volterra_system,
    "van_der_pol": van_der_pol_system,
}

# Pre-calibrated default initial conditions & parameters for robust simulation
DEFAULT_CONFIGS: dict[str, dict[str, Any]] = {
    "fixed_point": {"initial_conditions": [3.0, 3.0, 3.0], "params": {"a": 0.4, "omega": 2.0, "b": 0.6}},
    "limit_cycle": {"initial_conditions": [0.1, 0.1, 2.0], "params": {"mu": 4.0, "omega": 2.0, "c": 1.0}},
    "torus": {"initial_conditions": [0.1, 0.1, 0.5], "params": {"lambda": 0.6, "omega": 3.5, "c": 0.2, "d": 0.5}},
    "quasiperiodic": {"initial_conditions": [0.1, 0.1, 0.5], "params": {"lambda": 0.6, "omega": 3.5, "c": 0.2, "d": 0.5}},
    "lorenz": {"initial_conditions": [0.1, 0.0, 0.0], "params": {"sigma": 10.0, "rho": 28.0, "beta": 8.0 / 3.0}},
    "rossler": {"initial_conditions": [0.1, 0.0, 0.0], "params": {"a": 0.2, "b": 0.2, "c": 5.7}},
    "chua": {"initial_conditions": [0.1, 0.1, 0.0], "params": {"alpha": 10.0, "beta": 14.87, "m0": -1.27, "m1": -0.68}},
    "double_scroll": {"initial_conditions": [0.1, 0.1, 0.0], "params": {"alpha": 10.0, "beta": 14.87, "m0": -1.27, "m1": -0.68}},
    "multiscroll": {"initial_conditions": [0.1, 0.1, 0.0], "params": {"alpha": 9.0, "beta": 14.28, "a": 1.0, "b": 1.1}},
    "chen": {"initial_conditions": [-0.1, 0.5, -0.6], "params": {"a": 35.0, "b": 3.0, "c": 28.0}},
    "sprott": {"initial_conditions": [0.1, 0.1, 0.1], "params": {"a": 1.0}},
    "sprott_b": {"initial_conditions": [0.1, 0.1, 0.1], "params": {"a": 1.0}},
    "rabinovich_fabrikant": {"initial_conditions": [-1.0, 0.0, 0.5], "params": {"alpha": 0.14, "gamma": 0.10}},
    "shilnikov": {"initial_conditions": [0.1, 0.1, 0.1], "params": {"a": 5.5, "b": 3.5, "c": 1.0, "d": 1.0}},
    "hyperchaotic": {"initial_conditions": [-10.0, -6.0, 0.0, 10.0], "params": {"a": 0.25, "b": 3.0, "c": 0.5, "d": 0.05}},
    "hidden_attractor": {"initial_conditions": [1.0, 1.0, 1.0], "params": {"a": 10.0, "b": 2.0, "c": 10.0}},
    "leonov": {"initial_conditions": [1.0, 1.0, 1.0], "params": {"a": 10.0, "b": 2.0, "c": 10.0}},
    "aizerman": {"initial_conditions": [2.0, 0.0, 0.0], "params": {"a": 2.0, "b": 1.0, "c": 0.1, "k": 1.5}},
    "chaotic_saddle": {"initial_conditions": [1.0, 1.0, 1.0], "params": {"sigma": 10.0, "rho": 21.5, "beta": 8.0 / 3.0}},
    "transient": {"initial_conditions": [1.0, 1.0, 1.0], "params": {"sigma": 10.0, "rho": 21.5, "beta": 8.0 / 3.0}},
    "solenoid": {"initial_conditions": [3.1, 0.0, 0.1], "params": {"R0": 3.0, "omega": 1.5, "lambda": 0.8}},
    "milnor": {"initial_conditions": [0.1, 0.1, 0.1], "params": {"a": 1.4, "b": 0.3}},
    "coexisting_attractors": {"initial_conditions": [0.5, 0.5, 0.5], "params": {"a": 1.0, "b": 0.8}},
    "henon": {"initial_conditions": [0.0, 0.0], "params": {"a": 1.4, "b": 0.3}},
    "lotka_volterra": {"initial_conditions": [2.0, 1.0], "params": {"alpha": 1.5, "beta": 1.0, "delta": 0.75, "gamma": 1.0}},
    "van_der_pol": {"initial_conditions": [1.0, 0.0], "params": {"mu": 1.0}},
    "double_pendulum": {"initial_conditions": [np.pi / 2, np.pi / 2, 0.0, 0.0], "params": {"g": 9.81, "m1": 1.0, "m2": 1.0, "l1": 1.0, "l2": 1.0}},
}


class ODESolver(DataSource):
    """Solves differential equation initial value problems and discrete maps."""

    def __init__(self, registry: dict[str, Any] | None = None):
        self.registry = registry or MODEL_REGISTRY

    def cache_key(self, spec: DataSourceSpec, quality: str = "final") -> str:
        """Calculate deterministic SHA256 cache key for ODE run."""
        payload = {
            "source": spec.source,
            "model": spec.model,
            "params": {k: float(v) for k, v in sorted(spec.params.items())},
            "initial_conditions": [float(x) for x in spec.initial_conditions],
            "solver": {
                "method": spec.solver.method,
                "t_span": [float(x) for x in spec.solver.t_span],
                "dt": float(spec.solver.dt),
                "rtol": float(spec.solver.rtol),
                "atol": float(spec.solver.atol),
                "downsample": int(spec.solver.downsample),
            },
            "quality": quality,
        }
        raw_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw_bytes).hexdigest()

    def solve(self, spec: DataSourceSpec, quality: str = "final") -> DataResult:
        """Solve differential system or discrete map with disk caching."""
        key = self.cache_key(spec, quality)
        if spec.solver.cache:
            cached = load_cached_result(key)
            if cached is not None:
                return cached

        model_name = (spec.model or "").lower().strip()

        # Handle discrete maps (e.g. Hénon map)
        if model_name == "henon" or spec.source in ("discrete_map", "map_solver"):
            return self._solve_henon(spec, quality, key)

        if not model_name or model_name not in self.registry:
            available = ", ".join(sorted(self.registry.keys())) + ", henon"
            raise ValueError(
                f"Unknown ODE model: '{spec.model}'. Available models: {available}"
            )

        model_fn = self.registry[model_name]

        # Use defaults if initial_conditions or params not fully provided
        cfg = DEFAULT_CONFIGS.get(model_name, {})
        init_conds = spec.initial_conditions if spec.initial_conditions else cfg.get("initial_conditions", [0.1, 0.1, 0.1])
        params = dict(cfg.get("params", {}))
        params.update(spec.params)

        y0 = np.array(init_conds, dtype=np.float64)
        if len(y0) == 0:
            raise ValueError(f"Initial conditions for model '{spec.model}' cannot be empty.")

        t0, t1 = spec.solver.t_span[0], spec.solver.t_span[1]
        dt = spec.solver.dt
        if quality == "preview":
            dt = max(dt, 0.05)

        num_steps = max(int(np.ceil((t1 - t0) / dt)) + 1, 2)
        t_eval = np.linspace(t0, t1, num_steps)

        def rhs(t: float, y: np.ndarray) -> list[float]:
            return model_fn(t, y, params)

        sol = solve_ivp(
            rhs,
            (t0, t1),
            y0,
            method=spec.solver.method,
            t_eval=t_eval,
            rtol=spec.solver.rtol,
            atol=spec.solver.atol,
        )

        if not sol.success:
            return DataResult(
                points=np.empty((0, 3)),
                status="failed",
                error=sol.message,
            )

        # Transpose to shape (N, D)
        pts = sol.y.T

        # If double pendulum, convert angles [th1, th2, w1, w2] to Cartesian tip (x2, y2, 0)
        if model_name == "double_pendulum" and pts.shape[1] >= 2:
            l1 = params.get("l1", 1.0)
            l2 = params.get("l2", 1.0)
            th1 = pts[:, 0]
            th2 = pts[:, 1]
            x1 = l1 * np.sin(th1)
            y1 = -l1 * np.cos(th1)
            x2 = x1 + l2 * np.sin(th2)
            y2 = y1 - l2 * np.cos(th2)
            pts = np.column_stack([x2, y2, np.zeros_like(x2)])
        elif pts.shape[1] == 2:
            pts = np.column_stack([pts[:, 0], pts[:, 1], np.zeros(len(pts))])
        elif pts.shape[1] > 3:
            # 4D systems (e.g. Hyperchaotic) projected to 3D phase space (x, y, z)
            pts = pts[:, :3]

        downsample = spec.solver.downsample
        if quality == "preview":
            downsample = max(downsample, 3)

        if downsample > 1:
            pts = pts[::downsample]
            t_eval = t_eval[::downsample]

        result = DataResult(
            points=pts,
            time=t_eval,
            metadata={
                "model": model_name,
                "points_count": len(pts),
                "duration": float(t1 - t0),
            },
            status="success",
        )
        result.validate()

        if spec.solver.cache:
            save_cached_result(key, result)

        return result

    def _solve_henon(self, spec: DataSourceSpec, quality: str, key: str) -> DataResult:
        """Solve discrete Hénon map."""
        cfg = DEFAULT_CONFIGS.get("henon", {})
        init_conds = spec.initial_conditions if spec.initial_conditions else cfg.get("initial_conditions", [0.0, 0.0])
        params = dict(cfg.get("params", {}))
        params.update(spec.params)

        a = params.get("a", 1.4)
        b = params.get("b", 0.3)
        x = float(init_conds[0]) if len(init_conds) > 0 else 0.0
        y = float(init_conds[1]) if len(init_conds) > 1 else 0.0

        t0, t1 = spec.solver.t_span[0], spec.solver.t_span[1]
        dt = spec.solver.dt
        num_steps = max(int(np.ceil((t1 - t0) / dt)) + 1, 100)
        if quality == "preview":
            num_steps = min(num_steps, 2000)

        points = np.zeros((num_steps, 3), dtype=np.float64)
        time_arr = np.linspace(t0, t1, num_steps)

        for i in range(num_steps):
            points[i] = [x, y, 0.0]
            nx = 1.0 - a * x**2 + y
            ny = b * x
            x, y = nx, ny

        result = DataResult(
            points=points,
            time=time_arr,
            metadata={"model": "henon", "points_count": num_steps, "type": "discrete_map"},
            status="success",
        )
        result.validate()
        if spec.solver.cache:
            save_cached_result(key, result)
        return result
