"""CPU-only torch device helpers for manim-ai compute."""

from __future__ import annotations

import os
from typing import Any

import torch
import torch.nn as nn

DEVICE = torch.device("cpu")

# Prefer CPU defaults; never move work to CUDA in this package.
if hasattr(torch, "set_default_device"):
    try:
        torch.set_default_device("cpu")
    except Exception:
        pass

_threads = min(4, os.cpu_count() or 1)
torch.set_num_threads(_threads)


def tensor(data: Any = None, *, requires_grad: bool = False, dtype: torch.dtype | None = None, **kwargs) -> torch.Tensor:
    """Create a tensor always on CPU."""
    kw: dict[str, Any] = {"device": DEVICE, "requires_grad": requires_grad, **kwargs}
    if dtype is not None:
        kw["dtype"] = dtype
    if data is None:
        raise TypeError("tensor() requires data")
    return torch.tensor(data, **kw)


def as_tensor(data: Any, *, dtype: torch.dtype | None = torch.float32, requires_grad: bool = False) -> torch.Tensor:
    """Convert array-like / Tensor to a CPU tensor."""
    if isinstance(data, torch.Tensor):
        t = data.detach().to(DEVICE)
        if dtype is not None:
            t = t.to(dtype=dtype)
        if requires_grad:
            t = t.requires_grad_(True)
        return t
    return tensor(data, dtype=dtype, requires_grad=requires_grad)


def empty(*size: int, dtype: torch.dtype = torch.float32) -> torch.Tensor:
    return torch.empty(*size, dtype=dtype, device=DEVICE)


def randn(*size: int, generator: torch.Generator | None = None, dtype: torch.dtype = torch.float32) -> torch.Tensor:
    return torch.randn(*size, generator=generator, dtype=dtype, device=DEVICE)


def linspace(start: float, end: float, steps: int, dtype: torch.dtype = torch.float32) -> torch.Tensor:
    return torch.linspace(start, end, steps, dtype=dtype, device=DEVICE)


def generator(seed: int) -> torch.Generator:
    return torch.Generator(device="cpu").manual_seed(int(seed))


def module_to_cpu(module: nn.Module) -> nn.Module:
    return module.to(DEVICE)


def ensure_cpu() -> torch.device:
    """Public check used by smoke tests / demos."""
    assert DEVICE.type == "cpu"
    return DEVICE
