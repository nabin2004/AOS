from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from manim import *

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
        *,
        buff: float = 0.6,
        radius: float = 0.4,
    ) -> None:
        super().__init__()

        input_nodes = VGroup()
        for i in range(in_features):
            if inputs is not None:
                label = MathTex(rf"x_{{{i + 1}}} = {inputs[i]:g}")
            else:
                label = MathTex(rf"x_{{{i + 1}}}")
            node = VGroup(Circle(radius=radius), label.move_to(ORIGIN))
            input_nodes.add(node)

        output_nodes = VGroup()
        for i in range(out_features):
            label = MathTex("y" if out_features == 1 else rf"y_{{{i + 1}}}")
            node = VGroup(Circle(radius=radius), label.move_to(ORIGIN))
            output_nodes.add(node)

        input_nodes.arrange(DOWN, buff=buff).to_edge(LEFT)
        output_nodes.arrange(DOWN, buff=buff).to_edge(RIGHT)

        edges = VGroup(
            *[
                Line(input_node[0].get_right(), output_node[0].get_left())
                for input_node in input_nodes
                for output_node in output_nodes
            ]
        )

        self.add(edges, input_nodes, output_nodes)

    @classmethod
    def from_linear(cls, module: nn.Linear, x: torch.Tensor) -> LinearLayer:
        values = x.detach().flatten().tolist()
        return cls(module.in_features, module.out_features, inputs=values)


class Network(VGroup):
    """Simple multi-layer network diagram from layer sizes, e.g. [3, 4, 2, 1]."""

    def __init__(
        self,
        layers: Sequence[int],
        *,
        layer_spacing: float = 2.0,
        buff: float = 0.5,
        radius: float = 0.3,
    ) -> None:
        super().__init__()

        if len(layers) < 2:
            raise ValueError("layers must have at least two sizes")

        layer_groups: list[VGroup] = []
        for size in layers:
            group = VGroup(*[Circle(radius=radius) for _ in range(size)])
            group.arrange(DOWN, buff=buff)
            layer_groups.append(group)

        for i, group in enumerate(layer_groups):
            group.move_to(RIGHT * i * layer_spacing)
            group.shift(LEFT * (len(layers) - 1) * layer_spacing / 2)

        edges = VGroup()
        for left, right in zip(layer_groups, layer_groups[1:]):
            for n1 in left:
                for n2 in right:
                    edges.add(Line(n1.get_center(), n2.get_center()))

        self.add(edges, *layer_groups)
