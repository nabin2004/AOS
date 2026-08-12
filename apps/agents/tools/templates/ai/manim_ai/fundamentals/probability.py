"""Probability visualizers (d2l Ch 2.6)."""

from __future__ import annotations

from manim import DOWN, Axes, MathTex, Text, VGroup, WHITE

from manim_ai.compute import probability as prob
from manim_ai.core.registry import register_concept
from manim_ai.core.theme import DEFAULT_THEME


@register_concept(
    id="bernoulli_coins",
    domain="fundamental",
    chapter="2.6.1",
    title="Coin Toss Distribution",
    description="Bernoulli / binomial intuition.",
    tags=["probability"],
)
def build_bernoulli_coins(p: float = 0.5) -> VGroup:
    params = prob.bernoulli_params(p)
    title = Text("Coin toss", font_size=30, color=WHITE)
    eq = MathTex(
        rf"P(H)=p={params['p']:g},\quad P(T)=1-p={1 - params['p']:g}",
        font_size=30,
    )
    note = Text(
        f"Bernoulli trial → E[X]={params['mean']:g}, Var={params['var']:g}",
        font_size=22,
        color=DEFAULT_THEME.soft,
    )
    return VGroup(title, eq, note).arrange(DOWN, buff=0.35)


@register_concept(
    id="gaussian_pdf",
    domain="fundamental",
    chapter="2.6.2",
    title="Gaussian PDF",
    description="Plot a normal density.",
    tags=["probability"],
)
def build_gaussian_pdf(mu: float = 0.0, sigma: float = 1.0) -> VGroup:
    axes = Axes(x_range=[-4, 4, 1], y_range=[0, 0.5, 0.1], x_length=7, y_length=3).scale(0.75)
    curve = axes.plot(lambda x: prob.gaussian_pdf_at(x, mu=mu, sigma=sigma), color=DEFAULT_THEME.secondary)
    label = MathTex(rf"\mathcal{{N}}(\mu={mu:g},\sigma={sigma:g})", font_size=28)
    label.next_to(axes, DOWN, buff=0.25)
    return VGroup(axes, curve, label)


@register_concept(
    id="bayes_rule",
    domain="fundamental",
    chapter="2.6.4",
    title="Bayes' Rule",
    description="Prior × likelihood → posterior (Beta-Binomial toy).",
    tags=["probability"],
)
def build_bayes_rule(
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
    heads: int = 7,
    tails: int = 3,
) -> VGroup:
    post = prob.bayes_beta_binomial(prior_alpha, prior_beta, heads, tails)
    title = Text("Bayes' rule", font_size=30, color=WHITE)
    eq = MathTex(r"P(\theta\mid x)=\frac{P(x\mid\theta)P(\theta)}{P(x)}", font_size=34)
    row = MathTex(
        rf"\mathrm{{Beta}}({post['posterior_alpha']:g},{post['posterior_beta']:g}),\ "
        rf"\mathbb{{E}}[\theta]={post['posterior_mean']:.3g}",
        font_size=28,
    )
    return VGroup(title, eq, row).arrange(DOWN, buff=0.4)
