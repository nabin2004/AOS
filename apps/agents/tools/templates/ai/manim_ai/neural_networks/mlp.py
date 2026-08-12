"""MLP and network diagrams (d2l Ch 5) — absorbs manim-deeplearning patterns."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from manim import DOWN, LEFT, RIGHT, Circle, Line, MathTex, Text, VGroup, WHITE

from manim_ai.compute import autodiff
from manim_ai.compute import nn as nn_ops
from manim_ai.core.registry import register_concept
from manim_ai.core.theme import DEFAULT_THEME

if TYPE_CHECKING:
    import torch
    import torch.nn as nn


class LinearLayer(VGroup):
    """Visualize in_features -> out_features as circles and connecting lines."""

    def __init__(
        self,
        in_features: int,
        out_features: int = 1,
        inputs: Sequence[float] | None = None,
        outputs: Sequence[float] | None = None,
        *,
        buff: float = 0.6,
        radius: float = 0.35,
    ) -> None:
        super().__init__()
        input_nodes = VGroup()
        for i in range(in_features):
            if inputs is not None:
                label = MathTex(rf"x_{{{i + 1}}}={float(inputs[i]):.2g}", font_size=18)
            else:
                label = MathTex(rf"x_{{{i + 1}}}", font_size=20)
            node = VGroup(Circle(radius=radius, color=WHITE), label)
            input_nodes.add(node)

        output_nodes = VGroup()
        for i in range(out_features):
            if outputs is not None:
                lab = rf"y={float(outputs[i]):.2g}" if out_features == 1 else rf"y_{{{i + 1}}}={float(outputs[i]):.2g}"
                label = MathTex(lab, font_size=18)
            else:
                label = MathTex("y" if out_features == 1 else rf"y_{{{i + 1}}}", font_size=20)
            node = VGroup(Circle(radius=radius, color=WHITE), label)
            output_nodes.add(node)

        input_nodes.arrange(DOWN, buff=buff)
        output_nodes.arrange(DOWN, buff=buff)
        input_nodes.move_to(LEFT * 2.5)
        output_nodes.move_to(RIGHT * 2.5)

        edges = VGroup(
            *[
                Line(a[0].get_right(), b[0].get_left(), stroke_opacity=0.6)
                for a in input_nodes
                for b in output_nodes
            ]
        )
        self.add(edges, input_nodes, output_nodes)
        self.input_nodes = input_nodes
        self.output_nodes = output_nodes
        self.edges = edges

    @classmethod
    def from_linear(cls, module: "nn.Linear", x: "torch.Tensor") -> "LinearLayer":
        from manim_ai.compute import device as cpu

        x_cpu = cpu.as_tensor(x)
        module = cpu.module_to_cpu(module)
        y = module(x_cpu)
        return cls(
            module.in_features,
            module.out_features,
            inputs=x_cpu.detach().flatten().tolist(),
            outputs=y.detach().flatten().tolist(),
        )


class Network(VGroup):
    """Multi-layer network diagram from layer sizes, e.g. [3, 4, 2, 1]."""

    def __init__(
        self,
        layers: Sequence[int],
        activations: Sequence[Sequence[float]] | None = None,
        *,
        layer_spacing: float = 1.8,
        buff: float = 0.4,
        radius: float = 0.25,
    ) -> None:
        super().__init__()
        if len(layers) < 2:
            raise ValueError("layers must have at least two sizes")
        layer_groups: list[VGroup] = []
        for li, size in enumerate(layers):
            nodes = VGroup()
            for j in range(size):
                if activations is not None and li < len(activations) and j < len(activations[li]):
                    lab = Text(f"{float(activations[li][j]):.2g}", font_size=12, color=WHITE)
                else:
                    lab = Text("", font_size=12)
                nodes.add(VGroup(Circle(radius=radius, color=WHITE), lab))
            nodes.arrange(DOWN, buff=buff)
            layer_groups.append(nodes)
        for i, group in enumerate(layer_groups):
            group.move_to(RIGHT * i * layer_spacing)
            group.shift(LEFT * (len(layers) - 1) * layer_spacing / 2)
        edges = VGroup()
        for left, right in zip(layer_groups, layer_groups[1:]):
            for n1 in left:
                for n2 in right:
                    edges.add(Line(n1[0].get_center(), n2[0].get_center(), stroke_opacity=0.45))
        self.add(edges, *layer_groups)
        self.layer_groups = layer_groups


@register_concept(
    id="linear_layer",
    domain="neural_network",
    chapter="5.1",
    title="Linear Layer",
    tags=["mlp"],
)
def build_linear_layer(
    in_features: int = 3,
    out_features: int = 2,
    x: Sequence[float] | None = None,
    seed: int = 0,
) -> VGroup:
    result = nn_ops.linear_module_forward(in_features, out_features, x=x, seed=seed)
    layer = LinearLayer(
        in_features,
        out_features,
        inputs=[float(v) for v in result["x"]],
        outputs=[float(v) for v in result["y"]],
    )
    note = Text("nn.Linear (CPU torch)", font_size=18, color=DEFAULT_THEME.soft)
    return VGroup(layer, note).arrange(DOWN, buff=0.25)


@register_concept(
    id="mlp_network",
    domain="neural_network",
    chapter="5.1",
    title="Multilayer Perceptron",
    tags=["mlp"],
)
def build_mlp_network(
    layers: Sequence[int] | None = None,
    x: Sequence[float] | None = None,
    seed: int = 0,
) -> VGroup:
    layers = list(layers or [3, 4, 2, 1])
    fwd = nn_ops.mlp_forward(layers, x=x, seed=seed)
    net = Network(layers, activations=fwd["activations"])
    title = Text("MLP (CPU torch forward)", font_size=26, color=WHITE)
    return VGroup(title, net).arrange(DOWN, buff=0.35)


@register_concept(
    id="forward_backward",
    domain="neural_network",
    chapter="5.3",
    title="Forward and Backpropagation",
    tags=["mlp", "backprop"],
)
def build_forward_backward(
    sizes: Sequence[int] | None = None,
    seed: int = 0,
) -> VGroup:
    sizes = list(sizes or [3, 3, 2])
    snap = autodiff.mlp_grad_snapshot(sizes=sizes, seed=seed)
    net = Network(sizes, activations=snap["activations"])
    fwd = Text(
        f"Forward →  L={snap['loss']:.3g}",
        font_size=22,
        color=DEFAULT_THEME.positive,
    ).next_to(net, DOWN, buff=0.3)
    bwd = Text(
        f"← Backward  ‖∇‖={snap['grad_norm_total']:.3g}",
        font_size=22,
        color=DEFAULT_THEME.accent,
    ).next_to(fwd, DOWN, buff=0.2)
    return VGroup(net, fwd, bwd)
