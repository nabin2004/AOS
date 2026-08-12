"""Convolution / pooling via torch.nn.functional on CPU."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import torch
import torch.nn.functional as F

from manim_ai.compute import device as cpu


def _to_nchw(image: Sequence[Sequence[float]]) -> torch.Tensor:
    arr = np.asarray(image, dtype=np.float32)
    return cpu.as_tensor(arr, dtype=torch.float32)[None, None, :, :]


def cross_correlate(
    image: Sequence[Sequence[float]],
    kernel: Sequence[Sequence[float]],
) -> np.ndarray:
    """2D cross-correlation (conv2d without kernel flip) on CPU."""
    x = _to_nchw(image)
    k = cpu.as_tensor(kernel, dtype=torch.float32)[None, None, :, :]
    y = F.conv2d(x, k)
    return y.squeeze().detach().cpu().numpy()


def max_pool2d(
    image: Sequence[Sequence[float]],
    kernel_size: int = 2,
    stride: int | None = None,
) -> np.ndarray:
    x = _to_nchw(image)
    y = F.max_pool2d(x, kernel_size=kernel_size, stride=stride or kernel_size)
    return y.squeeze().detach().cpu().numpy()


def avg_pool2d(
    image: Sequence[Sequence[float]],
    kernel_size: int = 2,
    stride: int | None = None,
) -> np.ndarray:
    x = _to_nchw(image)
    y = F.avg_pool2d(x, kernel_size=kernel_size, stride=stride or kernel_size)
    return y.squeeze().detach().cpu().numpy()
