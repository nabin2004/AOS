from manim import *
import torch
import torch.nn as nn
from manim_deeplearning import LinearLayer


class Neuron(Scene):
    def construct(self):
        x = torch.tensor([1.0, 2.0, 3.0])
        linear = nn.Linear(3, 1)
        y = linear(x)

        diagram = LinearLayer.from_linear(linear, x)
        self.add(diagram)
        self.wait(1)
