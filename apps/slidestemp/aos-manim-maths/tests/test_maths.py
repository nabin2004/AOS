import pytest
import numpy as np
from aos_manim_core import get_theme, set_theme, use_theme
from aos_manim_maths import (
    DerivativeVisualizer,
    compute_derivative_data,
    IntegralVisualizer,
    compute_integral_data,
    RootFindingVisualizer,
    compute_newton_steps,
    MatrixTransformationVisualizer,
    ProbabilityVisualizer,
    RootPrecisionValidator,
    IntegralConvergenceValidator,
)


def test_derivative_computation_and_mobjects():
    data = compute_derivative_data("x**3 - 2*x", 2.0)
    # f(2) = 8 - 4 = 4
    assert abs(data["y_val"] - 4.0) < 1e-6
    # f'(x) = 3x^2 - 2 -> f'(2) = 12 - 2 = 10
    assert abs(data["slope"] - 10.0) < 1e-6

    vis = DerivativeVisualizer()
    mobs = vis.build_derivative_mobjects("x**2", 1.0)
    assert mobs["axes"] is not None
    assert mobs["curve"] is not None
    assert mobs["tangent_line"] is not None


def test_integral_quadrature_and_mobjects():
    # \int_0^2 x^2 dx = 8/3 \approx 2.666667
    data = compute_integral_data("x**2", 0.0, 2.0)
    assert abs(data["symbolic_result"] - 8.0 / 3.0) < 1e-5
    assert abs(data["numerical_result"] - 8.0 / 3.0) < 1e-5

    val = IntegralConvergenceValidator(tol=1e-4)
    res = val.validate(data["numerical_result"], symbolic_result=data["symbolic_result"])
    assert res.is_valid

    vis = IntegralVisualizer()
    mobs = vis.build_integral_mobjects("x**2", 0.0, 2.0)
    assert mobs["area"] is not None
    assert mobs["riemann_rectangles"] is not None


def test_root_finding_newton_and_validator():
    # Root of x^2 - 4 = 0 starting from x0 = 3
    data = compute_newton_steps("x**2 - 4", 3.0, max_steps=6)
    assert len(data["steps"]) > 0
    assert abs(data["root"] - 2.0) < 1e-4

    val = RootPrecisionValidator(tol=1e-4)
    res = val.validate(data["root"], expression="x**2 - 4")
    assert res.is_valid

    vis = RootFindingVisualizer()
    mobs = vis.build_root_finding_mobjects("x**2 - 4", 3.0)
    assert mobs["root_dot"] is not None

    cueable = vis.build_cueable_root_finding("x**2 - 4", 3.0, show_all_steps=False)
    assert cueable.step_count() > 0
    from aos_manim_core import Cue, CueAction

    class Dummy:
        def wait(self, t):
            pass

    first = cueable.step_groups[0]
    first.set_opacity(0)
    cueable.apply_cue(Dummy(), Cue(mark="s0", target_id="d0", action=CueAction.STEP, payload={"i": 0}))
    assert first.get_fill_opacity() > 0.2
    last_i = cueable.step_count() - 1
    cueable.apply_cue(Dummy(), Cue(mark="sN", target_id="d0", action=CueAction.STEP, payload={"i": last_i}))
    assert cueable.root_dot.get_fill_opacity() > 0.2


def test_matrix_transformations():
    # Shear matrix [[1, 1], [0, 1]] -> det = 1
    vis = MatrixTransformationVisualizer()
    mobs = vis.build_transformation_mobjects([[1, 1], [0, 1]])
    assert abs(mobs["determinant"] - 1.0) < 1e-6
    assert mobs["plane"] is not None
    assert mobs["det_polygon"] is not None


def test_probability_visualizer():
    vis = ProbabilityVisualizer()
    mobs = vis.build_normal_distribution_mobjects(mu=0.0, sigma=1.0)
    assert mobs["curve"] is not None
    assert mobs["sigma1_area"] is not None
