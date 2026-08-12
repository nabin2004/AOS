"""Tiny autodiff graphs via torch on CPU."""

from __future__ import annotations

from collections.abc import Sequence

import torch
import torch.nn as nn
import torch.nn.functional as F

from manim_ai.compute import device as cpu


def graph_abc(
    a: float = 2.0,
    b: float = 3.0,
    c: float = 4.0,
) -> dict[str, float]:
    """
    Forward + backward for y=(a+b)*c on CPU.
    Returns values and gradients w.r.t. a,b,c.
    """
    ta = cpu.tensor(float(a), requires_grad=True, dtype=torch.float32)
    tb = cpu.tensor(float(b), requires_grad=True, dtype=torch.float32)
    tc = cpu.tensor(float(c), requires_grad=True, dtype=torch.float32)
    s = ta + tb
    y = s * tc
    y.backward()
    return {
        "a": float(ta.detach()),
        "b": float(tb.detach()),
        "c": float(tc.detach()),
        "sum": float(s.detach()),
        "y": float(y.detach()),
        "grad_a": float(ta.grad),
        "grad_b": float(tb.grad),
        "grad_c": float(tc.grad),
    }


def mlp_grad_snapshot(
    sizes: Sequence[int] | None = None,
    x: Sequence[float] | None = None,
    target: Sequence[float] | None = None,
    seed: int = 0,
) -> dict:
    """
    One CPU forward (MSE) + backward on a tiny MLP.
    Returns loss, activation lists, and per-parameter grad norms.
    """
    sizes = list(sizes or [3, 3, 2])
    g = cpu.generator(seed)
    modules: list[nn.Module] = []
    for i in range(len(sizes) - 1):
        lin = nn.Linear(sizes[i], sizes[i + 1])
        with torch.no_grad():
            lin.weight.normal_(0, 0.4, generator=g)
            lin.bias.zero_()
        modules.append(cpu.module_to_cpu(lin))
        if i < len(sizes) - 2:
            modules.append(nn.ReLU())
    net = cpu.module_to_cpu(nn.Sequential(*modules))

    if x is None:
        x_t = cpu.randn(sizes[0], generator=g)
    else:
        x_t = cpu.as_tensor(list(x), dtype=torch.float32)
    if target is None:
        y_t = cpu.randn(sizes[-1], generator=g)
    else:
        y_t = cpu.as_tensor(list(target), dtype=torch.float32)

    activations = [x_t.detach().cpu().tolist()]
    h = x_t
    idx = 0
    while idx < len(net):
        h = net[idx](h)
        idx += 1
        if idx < len(net) and isinstance(net[idx], nn.ReLU):
            h = net[idx](h)
            idx += 1
        activations.append(h.detach().cpu().tolist())

    loss = F.mse_loss(h, y_t)
    loss.backward()

    grad_norms: list[float] = []
    for p in net.parameters():
        if p.grad is not None:
            grad_norms.append(float(p.grad.detach().norm()))
        else:
            grad_norms.append(0.0)

    return {
        "sizes": sizes,
        "activations": activations,
        "loss": float(loss.detach()),
        "grad_norms": grad_norms,
        "grad_norm_total": float(sum(grad_norms)),
    }
