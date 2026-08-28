import pytest
import numpy as np
from aos_manim_core import get_theme, set_theme
from aos_manim_physics import (
    ProjectileVisualizer,
    compute_projectile_data,
    FreeBodyDiagram,
    PendulumVisualizer,
    simulate_pendulum,
    EnergyConservationValidator,
)


def test_projectile_computation():
    # v0 = 20 m/s, theta = 45 deg, g = 9.81
    data = compute_projectile_data(20.0, 45.0, g=9.81)
    # Range = v0^2 / g \approx 400 / 9.81 \approx 40.774
    assert abs(data["total_range"] - 40.774) < 0.1
    # Max height = (v0 sin 45)^2 / (2g) = 200 / 19.62 \approx 10.19
    assert abs(data["max_height"] - 10.19) < 0.1

    vis = ProjectileVisualizer()
    mobs = vis.build_projectile_mobjects(20.0, 45.0)
    assert mobs["axes"] is not None
    assert mobs["curve"] is not None


def test_free_body_diagram():
    fbd = FreeBodyDiagram(mass=2.0)
    net = fbd.compute_net_force()
    # fx = 2.5 - 1.0 = 1.5, fy = 2.0 - 2.0 = 0.0
    assert abs(net[0] - 1.5) < 1e-6
    assert abs(net[1] - 0.0) < 1e-6


def test_pendulum_simulation_and_energy_conservation():
    sim = simulate_pendulum(length=2.0, theta0_deg=30.0, t_span=(0, 5))
    assert len(sim["t"]) > 0

    val = EnergyConservationValidator(rel_tol=1e-3)
    res = val.validate(sim["energy"])
    assert res.is_valid

    vis = PendulumVisualizer()
    mobs = vis.build_pendulum_mobjects(length=2.0, theta0_deg=30.0)
    assert mobs["bob"] is not None
