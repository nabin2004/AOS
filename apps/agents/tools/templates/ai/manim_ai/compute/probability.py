"""Probability via scipy.stats."""

from __future__ import annotations

import numpy as np
from scipy import stats


def bernoulli_params(p: float = 0.5) -> dict[str, float]:
    dist = stats.bernoulli(p=p)
    return {"p": float(p), "mean": float(dist.mean()), "var": float(dist.var())}


def gaussian_pdf(xs, mu: float = 0.0, sigma: float = 1.0) -> np.ndarray:
    return stats.norm.pdf(xs, loc=mu, scale=sigma)


def gaussian_pdf_at(x: float, mu: float = 0.0, sigma: float = 1.0) -> float:
    return float(stats.norm.pdf(x, loc=mu, scale=sigma))


def bayes_beta_binomial(
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
    heads: int = 7,
    tails: int = 3,
) -> dict[str, float]:
    """Conjugate Beta-Binomial update (toy Bayes demo)."""
    post_a = prior_alpha + heads
    post_b = prior_beta + tails
    post = stats.beta(post_a, post_b)
    return {
        "prior_alpha": float(prior_alpha),
        "prior_beta": float(prior_beta),
        "posterior_alpha": float(post_a),
        "posterior_beta": float(post_b),
        "posterior_mean": float(post.mean()),
    }
