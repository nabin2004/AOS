"""Optimizer trajectories via torch.optim on a toy 1D loss (CPU)."""

from __future__ import annotations

import torch

from manim_ai.compute import device as cpu


def _trace(
    name: str,
    start: float,
    steps: int,
    lr: float,
    make_opt,
) -> list[float]:
    w = cpu.tensor(float(start), requires_grad=True, dtype=torch.float32)
    assert w.device.type == "cpu"
    opt = make_opt([w])
    xs = [float(w.detach())]
    for _ in range(steps):
        opt.zero_grad()
        loss = (w - 0.5) ** 2
        loss.backward()
        opt.step()
        xs.append(float(w.detach()))
    return xs


def sgd_path(start: float = 2.5, steps: int = 8, lr: float = 0.25) -> list[float]:
    return _trace("sgd", start, steps, lr, lambda params: torch.optim.SGD(params, lr=lr))


def momentum_path(
    start: float = 2.5,
    steps: int = 8,
    lr: float = 0.15,
    momentum: float = 0.9,
) -> list[float]:
    return _trace(
        "momentum",
        start,
        steps,
        lr,
        lambda params: torch.optim.SGD(params, lr=lr, momentum=momentum),
    )


def adam_path(start: float = 2.5, steps: int = 8, lr: float = 0.3) -> list[float]:
    return _trace("adam", start, steps, lr, lambda params: torch.optim.Adam(params, lr=lr))


def rmsprop_path(start: float = 2.5, steps: int = 8, lr: float = 0.2) -> list[float]:
    return _trace(
        "rmsprop",
        start,
        steps,
        lr,
        lambda params: torch.optim.RMSprop(params, lr=lr),
    )
