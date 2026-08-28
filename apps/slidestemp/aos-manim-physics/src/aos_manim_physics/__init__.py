"""
AOS Manim Physics: STEM physics simulation and computational visualization plugin.
"""

from .kinematics.projectile import ProjectileVisualizer, compute_projectile_data
from .dynamics.free_body import FreeBodyDiagram
from .dynamics.pendulum import PendulumVisualizer, simulate_pendulum
from .validators.physics_validators import EnergyConservationValidator

__version__ = "0.1.0"

__all__ = [
    "ProjectileVisualizer",
    "compute_projectile_data",
    "FreeBodyDiagram",
    "PendulumVisualizer",
    "simulate_pendulum",
    "EnergyConservationValidator",
]
