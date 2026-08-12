"""HS mechanics concept builders."""

from __future__ import annotations

from manim import DOWN, LEFT, RIGHT, Dot, MathTex, Rectangle, Text, VGroup, WHITE

from manim_physics.compute import collision_1d, newton_second, projectile_trajectory, shm_spring
from manim_physics.registry import register_concept
from manim_viz import (
    DEFAULT_THEME,
    bar_chart,
    curve_from_samples,
    labeled_vector_on_plane,
    make_axes,
    make_plane,
    particle,
    trajectory_curve,
)


@register_concept(
    id="newtons_second_law",
    domain="physics",
    chapter="1.1",
    title="Newton's Second Law",
    tags=["mechanics", "newton"],
)
def build_newtons_second_law(F: float = 10.0, m: float = 2.0) -> VGroup:
    data = newton_second(F, m)
    plane = make_plane(x_range=(-1, 5, 1), y_range=(-2, 2, 1), scale=0.65)
    force = labeled_vector_on_plane(plane, [data["F"] / 4, 0], color=DEFAULT_THEME.force, label=r"\vec F")
    acc = labeled_vector_on_plane(
        plane, [data["a"] / 4, 0], origin=(0, -1.2), color=DEFAULT_THEME.acceleration, label=r"\vec a"
    )
    eq = MathTex(rf"a=F/m={data['a']:g}", font_size=30)
    title = Text("Newton II", font_size=26, color=WHITE)
    return VGroup(title, plane, force, acc, eq).arrange(DOWN, buff=0.2)


@register_concept(
    id="projectile_motion",
    domain="physics",
    chapter="1.2",
    title="Projectile Motion",
    tags=["mechanics", "kinematics"],
)
def build_projectile_motion(v0: float = 12.0, angle_deg: float = 45.0) -> VGroup:
    traj = projectile_trajectory(v0=v0, angle_deg=angle_deg)
    axes = make_axes(x_range=(0, max(traj["x"]) + 1, 2), y_range=(0, max(traj["y"]) + 1, 1), scale=0.8)
    points = [axes.c2p(float(x), float(y)) for x, y in zip(traj["x"], traj["y"])]
    path = trajectory_curve(points, color=DEFAULT_THEME.secondary)
    dot = particle(points[-1] if points else axes.c2p(0, 0))
    title = Text("Projectile", font_size=26, color=WHITE)
    eq = MathTex(rf"v_0={v0:g},\ \theta={angle_deg:g}^\circ", font_size=26)
    return VGroup(title, axes, path, dot, eq).arrange(DOWN, buff=0.15)


@register_concept(
    id="shm_spring",
    domain="physics",
    chapter="1.3",
    title="SHM Spring",
    tags=["mechanics", "shm"],
)
def build_shm_spring() -> VGroup:
    data = shm_spring()
    plot = curve_from_samples(
        data["t"],
        data["x"],
        x_range=(0, 6, 1),
        y_range=(-1.5, 1.5, 1),
        color=DEFAULT_THEME.primary,
    )
    title = Text("Spring SHM: x=A cos(ωt)", font_size=24, color=WHITE)
    eq = MathTex(rf"\omega={data['omega']:.3g}", font_size=26)
    return VGroup(title, plot, eq).arrange(DOWN, buff=0.2)


@register_concept(
    id="mechanical_energy",
    domain="physics",
    chapter="1.4",
    title="Mechanical Energy",
    tags=["mechanics", "energy"],
)
def build_mechanical_energy() -> VGroup:
    data = shm_spring()
    i = len(data["t"]) // 4
    bars = bar_chart(
        [float(data["ke"][i]), float(data["pe"][i]), float(data["E"][i])],
        labels=["KE", "PE", "E"],
    )
    title = Text("Energy partition (SHM sample)", font_size=24, color=WHITE)
    note = MathTex(r"E=KE+PE=\mathrm{const}", font_size=28)
    return VGroup(title, bars, note).arrange(DOWN, buff=0.3)


@register_concept(
    id="momentum_1d_collision",
    domain="physics",
    chapter="1.5",
    title="1D Collision",
    tags=["mechanics", "momentum"],
)
def build_momentum_1d_collision(elastic: bool = True) -> VGroup:
    data = collision_1d(elastic=elastic)
    before = Text(f"Before: u1={data['u1']:g}, u2={data['u2']:g}", font_size=22, color=WHITE)
    after = Text(f"After:  v1={data['v1']:.3g}, v2={data['v2']:.3g}", font_size=22, color=WHITE)
    p = MathTex(
        rf"p_{{\mathrm{{before}}}}={data['p_before']:.3g},\ "
        rf"p_{{\mathrm{{after}}}}={data['p_after']:.3g}",
        font_size=26,
    )
    kind = Text("Elastic" if elastic else "Inelastic", font_size=24, color=DEFAULT_THEME.highlight)
    # simple block sketch
    b1 = Rectangle(width=0.9, height=0.6, color=DEFAULT_THEME.primary, fill_opacity=0.4)
    b2 = Rectangle(width=0.7, height=0.6, color=DEFAULT_THEME.secondary, fill_opacity=0.4)
    blocks = VGroup(b1, Text("m1", font_size=16), b2, Text("m2", font_size=16)).arrange(RIGHT, buff=0.35)
    return VGroup(kind, blocks, before, after, p).arrange(DOWN, buff=0.25)
