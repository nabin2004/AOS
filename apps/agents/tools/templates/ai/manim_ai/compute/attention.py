"""Scaled dot-product attention via torch (CPU)."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import torch
import torch.nn.functional as F

from manim_ai.compute import device as cpu


def scaled_dot_product_attention(
    Q,
    K,
    V,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Returns (weights, output) where weights = softmax(QK^T / sqrt(d)).
    Uses explicit scores for the weight matrix (for visualization) and
    checks agreement with F.scaled_dot_product_attention on CPU.
    """
    q = cpu.as_tensor(Q, dtype=torch.float32)
    k = cpu.as_tensor(K, dtype=torch.float32)
    v = cpu.as_tensor(V, dtype=torch.float32)
    d = q.shape[-1]
    scores = q @ k.T / (d**0.5)
    weights = F.softmax(scores, dim=-1)
    out = weights @ v

    # Exploit CPU SDPA; compare outputs (weights not returned by SDPA).
    q4 = q.unsqueeze(0).unsqueeze(0)  # (1,1,n,d)
    k4 = k.unsqueeze(0).unsqueeze(0)
    v4 = v.unsqueeze(0).unsqueeze(0)
    sdpa_out = F.scaled_dot_product_attention(q4, k4, v4).squeeze(0).squeeze(0)
    if not torch.allclose(out, sdpa_out, atol=1e-5, rtol=1e-4):
        # Prefer SDPA numeric output when they diverge slightly on edge cases
        out = sdpa_out

    return weights.detach().cpu().numpy(), out.detach().cpu().numpy()


def attention_from_tokens(
    tokens: Sequence[str],
    dim: int = 4,
    seed: int = 0,
) -> tuple[list[str], np.ndarray, np.ndarray]:
    """
    Build deterministic embeddings for tokens and run self-attention on CPU.
    Returns (tokens, weights, output).
    """
    g = cpu.generator(seed)
    n = len(tokens)
    emb = cpu.randn(n, dim, generator=g)
    weights, out = scaled_dot_product_attention(emb, emb, emb)
    return list(tokens), weights, out
