"""Physics compute: kinematics, Newton, SHM, collisions."""

from __future__ import annotations

import numpy as np


def projectile_trajectory(
    v0: float = 12.0,
    angle_deg: float = 45.0,
    g: float = 9.8,
    n: int = 80,
) -> dict:
    theta = np.deg2rad(angle_deg)
    vx = v0 * np.cos(theta)
    vy = v0 * np.sin(theta)
    t_flight = 2 * vy / g if vy > 0 else 1.0
    t = np.linspace(0, t_flight, n)
    x = vx * t
    y = vy * t - 0.5 * g * t**2
    y = np.maximum(y, 0)
    return {"t": t, "x": x, "y": y, "vx": vx, "vy0": vy, "t_flight": float(t_flight)}


def newton_second(F: float = 10.0, m: float = 2.0) -> dict:
    a = F / m
    return {"F": F, "m": m, "a": a}


def shm_spring(
    A: float = 1.0,
    omega: float = 2.0,
    t_end: float = 6.0,
    n: int = 120,
    m: float = 1.0,
    k: float | None = None,
) -> dict:
    if k is None:
        k = m * omega**2
    else:
        omega = np.sqrt(k / m)
    t = np.linspace(0, t_end, n)
    x = A * np.cos(omega * t)
    v = -A * omega * np.sin(omega * t)
    ke = 0.5 * m * v**2
    pe = 0.5 * k * x**2
    return {"t": t, "x": x, "v": v, "ke": ke, "pe": pe, "E": ke + pe, "omega": float(omega), "k": float(k)}


def collision_1d(
    m1: float = 2.0,
    m2: float = 1.0,
    u1: float = 3.0,
    u2: float = -1.0,
    elastic: bool = True,
) -> dict:
    if elastic:
        v1 = ((m1 - m2) / (m1 + m2)) * u1 + (2 * m2 / (m1 + m2)) * u2
        v2 = (2 * m1 / (m1 + m2)) * u1 + ((m2 - m1) / (m1 + m2)) * u2
    else:
        # perfectly inelastic
        v = (m1 * u1 + m2 * u2) / (m1 + m2)
        v1 = v2 = v
    return {
        "m1": m1,
        "m2": m2,
        "u1": u1,
        "u2": u2,
        "v1": float(v1),
        "v2": float(v2),
        "elastic": elastic,
        "p_before": m1 * u1 + m2 * u2,
        "p_after": m1 * v1 + m2 * v2,
    }
