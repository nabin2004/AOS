"""Linear algebra — numpy pedagogy + torch CPU twins."""

from __future__ import annotations

import numpy as np
import torch

from manim_ai.compute import device as cpu
from manim_ai.compute.tensors import as_array


def matmul(A, B) -> np.ndarray:
    return as_array(A) @ as_array(B)


def vector_norms(v) -> dict[str, float]:
    arr = as_array(v).ravel()
    return {
        "l1": float(np.linalg.norm(arr, ord=1)),
        "l2": float(np.linalg.norm(arr, ord=2)),
        "linf": float(np.linalg.norm(arr, ord=np.inf)),
    }


def svd(A) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    u, s, vh = np.linalg.svd(as_array(A), full_matrices=False)
    return u, s, vh


def torch_matmul(A, B) -> np.ndarray:
    a = cpu.as_tensor(A, dtype=torch.float32)
    b = cpu.as_tensor(B, dtype=torch.float32)
    return (a @ b).detach().cpu().numpy()


def torch_svd(A) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """CPU torch.linalg.svd; returns U, S, Vh (numpy)."""
    a = cpu.as_tensor(A, dtype=torch.float32)
    u, s, vh = torch.linalg.svd(a, full_matrices=False)
    return u.detach().cpu().numpy(), s.detach().cpu().numpy(), vh.detach().cpu().numpy()
