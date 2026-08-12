"""Neural-net ops via torch.nn.functional on CPU."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from manim_ai.compute import device as cpu


def softmax(logits: Sequence[float]) -> np.ndarray:
    t = cpu.as_tensor(list(logits), dtype=torch.float32)
    return F.softmax(t, dim=0).detach().cpu().numpy()


def mse_loss(y_hat, y) -> float:
    a = cpu.as_tensor(y_hat, dtype=torch.float32)
    b = cpu.as_tensor(y, dtype=torch.float32)
    return float(F.mse_loss(a, b))


def cross_entropy(logits: Sequence[float], target_index: int) -> float:
    t = cpu.as_tensor([list(logits)], dtype=torch.float32)
    target = cpu.tensor([int(target_index)], dtype=torch.long)
    return float(F.cross_entropy(t, target))


def activation_curves(
    kind: str = "all",
    x_min: float = -3.0,
    x_max: float = 3.0,
    n: int = 200,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    xs = cpu.linspace(x_min, x_max, n)
    out: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    x_np = xs.detach().cpu().numpy()
    if kind in ("all", "relu"):
        out["relu"] = (x_np, F.relu(xs).detach().cpu().numpy())
    if kind in ("all", "sigmoid"):
        out["sigmoid"] = (x_np, torch.sigmoid(xs).detach().cpu().numpy())
    if kind in ("all", "tanh"):
        out["tanh"] = (x_np, torch.tanh(xs).detach().cpu().numpy())
    return out


def synthetic_regression(
    n: int = 12,
    seed: int = 0,
    w: float = 1.5,
    b: float = 0.5,
    noise: float = 0.35,
) -> tuple[np.ndarray, np.ndarray]:
    g = cpu.generator(seed)
    xs = cpu.empty(n).uniform_(-2, 2, generator=g)
    ys = w * xs + b + cpu.empty(n).normal_(0, noise, generator=g)
    return xs.detach().cpu().numpy(), ys.detach().cpu().numpy()


def linear_forward(x: Sequence[float], weight, bias) -> np.ndarray:
    xt = cpu.as_tensor(list(x), dtype=torch.float32)
    w = cpu.as_tensor(weight, dtype=torch.float32)
    b = cpu.as_tensor(bias, dtype=torch.float32)
    return (xt @ w.T + b).detach().cpu().numpy()


def linear_module_forward(
    in_features: int,
    out_features: int,
    x: Sequence[float] | None = None,
    seed: int = 0,
) -> dict[str, np.ndarray]:
    """CPU nn.Linear forward; returns weights, bias, input, output."""
    g = cpu.generator(seed)
    layer = cpu.module_to_cpu(nn.Linear(in_features, out_features))
    with torch.no_grad():
        layer.weight.normal_(0, 0.5, generator=g)
        layer.bias.normal_(0, 0.1, generator=g)
    if x is None:
        x_t = cpu.randn(in_features, generator=g)
    else:
        x_t = cpu.as_tensor(list(x), dtype=torch.float32)
        if x_t.numel() != in_features:
            raise ValueError(f"x length {x_t.numel()} != in_features {in_features}")
    y = layer(x_t)
    return {
        "x": x_t.detach().cpu().numpy(),
        "weight": layer.weight.detach().cpu().numpy(),
        "bias": layer.bias.detach().cpu().numpy(),
        "y": y.detach().cpu().numpy(),
    }


def mlp_forward(
    sizes: Sequence[int],
    x: Sequence[float] | None = None,
    seed: int = 0,
) -> dict:
    """
    CPU MLP: Linear(+ReLU)* … Linear.
    Returns sizes, input, and per-layer activation vectors (after each Linear, with ReLU applied when present).
    """
    sizes = list(sizes)
    if len(sizes) < 2:
        raise ValueError("sizes need at least input and output")
    g = cpu.generator(seed)
    modules: list[nn.Module] = []
    for i in range(len(sizes) - 1):
        lin = nn.Linear(sizes[i], sizes[i + 1])
        with torch.no_grad():
            lin.weight.normal_(0, 0.5, generator=g)
            lin.bias.zero_()
        modules.append(cpu.module_to_cpu(lin))
        if i < len(sizes) - 2:
            modules.append(nn.ReLU())
    net = cpu.module_to_cpu(nn.Sequential(*modules))

    if x is None:
        x_t = cpu.randn(sizes[0], generator=g)
    else:
        x_t = cpu.as_tensor(list(x), dtype=torch.float32)

    layer_acts: list[list[float]] = [x_t.detach().cpu().tolist()]
    h = x_t
    idx = 0
    with torch.no_grad():
        while idx < len(net):
            h = net[idx](h)
            idx += 1
            if idx < len(net) and isinstance(net[idx], nn.ReLU):
                h = net[idx](h)
                idx += 1
            layer_acts.append(h.detach().cpu().tolist())

    return {
        "sizes": sizes,
        "x": layer_acts[0],
        "activations": layer_acts,
        "y": layer_acts[-1],
    }
