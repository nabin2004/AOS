"""
AOS Manim Maths: Flagship STEM mathematics visualization plugin.
"""

from .calculus.derivative import DerivativeVisualizer, compute_derivative_data
from .calculus.integral import IntegralVisualizer, compute_integral_data
from .algebra.roots import RootFindingVisualizer, compute_newton_steps, NewtonCueable
from .linear_algebra.transformations import MatrixTransformationVisualizer
from .linear_algebra.vector_field import VectorFieldVisualizer
from .probability.distributions import ProbabilityVisualizer
from .validators.math_validators import RootPrecisionValidator, IntegralConvergenceValidator

__version__ = "0.1.0"

__all__ = [
    "DerivativeVisualizer",
    "compute_derivative_data",
    "IntegralVisualizer",
    "compute_integral_data",
    "RootFindingVisualizer",
    "NewtonCueable",
    "compute_newton_steps",
    "MatrixTransformationVisualizer",
    "VectorFieldVisualizer",
    "ProbabilityVisualizer",
    "RootPrecisionValidator",
    "IntegralConvergenceValidator",
]
