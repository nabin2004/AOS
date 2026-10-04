"""Easing curves for animations — cubic bezier, elastic, bounce, back, polynomial."""

from __future__ import annotations

import math


def _clamp01(t: float) -> float:
    return max(0.0, min(1.0, t))


def linear(t: float) -> float:
    """Identity easing."""
    return _clamp01(t)


def ease_in_quad(t: float) -> float:
    """Quadratic ease-in."""
    t = _clamp01(t)
    return t * t


def ease_out_quad(t: float) -> float:
    """Quadratic ease-out."""
    t = _clamp01(t)
    return 1.0 - (1.0 - t) * (1.0 - t)


def ease_in_out_quad(t: float) -> float:
    """Quadratic ease-in-out on [0, 1]."""
    t = _clamp01(t)
    if t < 0.5:
        return 2.0 * t * t
    return 1.0 - ((-2.0 * t + 2.0) ** 2) / 2.0


def ease_in_cubic(t: float) -> float:
    t = _clamp01(t)
    return t * t * t


def ease_out_cubic(t: float) -> float:
    t = _clamp01(t)
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    t = _clamp01(t)
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0


def overshoot(t: float, amount: float = 1.70158) -> float:
    """Scaled overshoot curve helper on [0, 1] (used by ease_*_back)."""
    t = _clamp01(t)
    return t * t * ((amount + 1.0) * t - amount)


def ease_in_back(t: float, amount: float = 1.70158) -> float:
    """Ease-in with anticipation/pull-back past start."""
    return overshoot(t, amount)


def ease_out_back(t: float, amount: float = 1.70158) -> float:
    """Ease-out that overshoots past end then settles."""
    u = _clamp01(t)
    return 1.0 + ((amount + 1.0) * (u - 1.0) + amount) * (u - 1.0) ** 2


def ease_in_out_back(t: float, amount: float = 1.70158) -> float:
    u = _clamp01(t)
    c = amount * 1.525
    if u < 0.5:
        return (u * u * ((c + 1.0) * 2.0 * u - c)) / 2.0
    return ((2.0 * u - 2.0) ** 2 * ((c + 1.0) * (u * 2.0 - 2.0) + c) + 2.0) / 2.0


def ease_in_elastic(t: float, amplitude: float = 1.0, period: float = 0.3) -> float:
    """Ease-in with elastic decay toward start (Robert Penner-style).

    ``period`` scales oscillation; ``amplitude`` scales overshoot magnitude.
    """
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    p = period / (2.0 * math.pi)
    s = p / 4.0
    return -(
        amplitude
        * math.pow(2.0, 10.0 * (t - 1.0))
        * math.sin(((t - 1.0 - s) * (2.0 * math.pi)) / period)
    )


def ease_out_elastic(t: float, amplitude: float = 1.0, period: float = 0.3) -> float:
    """Ease-out with elastic oscillation past target."""
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    p = period / (2.0 * math.pi)
    s = p / 4.0
    return (
        amplitude * math.pow(2.0, -10.0 * t) * math.sin((t - s) * (2.0 * math.pi) / period)
        + 1.0
    )


def ease_out_bounce(t: float) -> float:
    """Ease-out with bounce near end (Robert Penner style)."""
    u = _clamp01(t)
    if u < 1.0 / 2.75:
        return 7.5625 * u * u
    if u < 2.0 / 2.75:
        u -= 1.5 / 2.75
        return 7.5625 * u * u + 0.75
    if u < 2.5 / 2.75:
        u -= 2.25 / 2.75
        return 7.5625 * u * u + 0.9375
    u -= 2.625 / 2.75
    return 7.5625 * u * u + 0.984375


def ease_in_bounce(t: float) -> float:
    """Ease-in mirror of bounce."""
    return 1.0 - ease_out_bounce(1.0 - _clamp01(t))


def ease_in_out_bounce(t: float) -> float:
    u = _clamp01(t)
    if u < 0.5:
        return (1.0 - ease_out_bounce(1.0 - 2.0 * u)) / 2.0
    return (1.0 + ease_out_bounce(2.0 * u - 1.0)) / 2.0


def _cubic_component(t: float, p0: float, p1: float, p2: float, p3: float) -> float:
    """Evaluate cubic Bézier component at parameter ``t``."""
    u = 1.0 - t
    return u * u * u * p0 + 3.0 * u * u * t * p1 + 3.0 * u * t * t * p2 + t * t * t * p3


def cubic_bezier(
    t: float,
    p1x: float,
    p1y: float,
    p2x: float,
    p2y: float,
    *,
    epsilon: float = 1e-7,
    max_iter: int = 40,
) -> float:
    """Map eased progress: ``t ∈ [0, 1]`` → ``y`` on cubic Bézier from (0,0) to (1,1).

    Finds Bézier parameter ``τ`` such that ``x(τ) ≈ t``, returns ``y(τ)``.
    Control points match CSS ``cubic-bezier()`` semantics.
    """
    u = _clamp01(t)
    if u <= 0.0:
        return 0.0
    if u >= 1.0:
        return 1.0

    lo, hi = 0.0, 1.0
    tau = u
    for _ in range(max_iter):
        tau = (lo + hi) / 2.0
        x = _cubic_component(tau, 0.0, p1x, p2x, 1.0)
        if abs(x - u) < epsilon:
            break
        if x < u:
            lo = tau
        else:
            hi = tau
    return _clamp01(_cubic_component(tau, 0.0, p1y, p2y, 1.0))


__all__ = [
    "cubic_bezier",
    "ease_in_back",
    "ease_in_bounce",
    "ease_in_cubic",
    "ease_in_elastic",
    "ease_in_out_back",
    "ease_in_out_bounce",
    "ease_in_out_cubic",
    "ease_in_out_quad",
    "ease_in_quad",
    "ease_out_back",
    "ease_out_bounce",
    "ease_out_cubic",
    "ease_out_elastic",
    "ease_out_quad",
    "linear",
    "overshoot",
]
