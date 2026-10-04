"""Pydantic validation schemas for Scientific Simulation and Animation DSL."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SceneHeader(BaseModel):
    """Header information for the scientific scene."""

    id: str = "scientific_demo"
    template: str = "ode_3d_trajectory"
    style: str = "soothing_science"
    fps: int = 60


class ODESolverConfig(BaseModel):
    """Configuration options for ODE solvers."""

    method: str = "DOP853"
    t_span: list[float] = Field(default_factory=lambda: [0.0, 25.0])
    dt: float = 0.01
    rtol: float = 1e-9
    atol: float = 1e-11
    cache: bool = True
    downsample: int = 1


class DataSourceSpec(BaseModel):
    """Specification of a numerical data generator, DL solver, or derived metric."""

    id: str
    source: str = "ode_solver"  # ode_solver, function_sampler, analytical_surface, optimization_tracer, softmax_normalizer, derived_metric
    model: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    initial_conditions: list[float] = Field(default_factory=list)
    solver: ODESolverConfig = Field(default_factory=ODESolverConfig)
    operation: str | None = None
    inputs: list[str] = Field(default_factory=list)

    # Deep learning specific fields
    function: str | None = None
    functions: list[str] = Field(default_factory=list)
    equation: str | None = None
    grid: dict[str, Any] = Field(default_factory=dict)
    algorithm: str | None = None  # sgd, momentum, rmsprop, adam
    loss_function: str | None = None
    start: list[float] = Field(default_factory=list)
    steps: int = 50
    learning_rate: float = 0.1
    momentum: float = 0.9
    beta1: float = 0.9
    beta2: float = 0.999
    logits: list[float] = Field(default_factory=list)
    temperature: float = 1.0
    x_range: list[float] = Field(default_factory=list)
    samples: int = 200
    derivative: bool = False


class CoordinateSystemSpec(BaseModel):
    """Specification of spatial coordinate axes."""

    id: str = "axes3d"
    type: str = "axes_3d"  # "axes_3d", "axes_2d", "number_plane"
    x_range: list[float] = Field(default_factory=lambda: [-50.0, 50.0, 10.0])
    y_range: list[float] = Field(default_factory=lambda: [-50.0, 50.0, 10.0])
    z_range: list[float] = Field(default_factory=lambda: [0.0, 50.0, 10.0])
    x_length: float = 12.0
    y_length: float = 12.0
    z_length: float = 6.0


class VisualComponentSpec(BaseModel):
    """Specification of visual mobjects mapped to data sources."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str  # trajectory_curve, tracer_dot, dynamic_line, divergence_line, inset_graph, activation_plot, loss_landscape, optimizer_path, network_graph, tensor_grid
    source: str | None = None
    sources: list[str] = Field(default_factory=list)
    coordinate_system: str | None = None
    from_dot: str | None = Field(default=None, alias="from")
    to_dot: str | None = Field(default=None, alias="to")
    style: dict[str, Any] = Field(default_factory=dict)
    position: str | list[float] = "UR"
    width: float = 3.5
    height: float = 2.0
    y_scale: str = "linear"

    # Deep learning specific visual properties
    layout: str | None = None  # grid_2x2, horizontal, vertical
    overlay_on: str | None = None
    layer_sizes: list[int] = Field(default_factory=list)
    shape: list[int] = Field(default_factory=list)
    values: list[Any] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    color: str | None = None


class CameraSpec(BaseModel):
    """3D or 2D Camera orientation and motion settings."""

    type: str = "three_d"
    initial: dict[str, float] = Field(
        default_factory=lambda: {"phi_deg": 76.0, "theta_deg": 43.0}
    )
    ambient_rotation: dict[str, Any] | None = None
    zoom: float | None = None
    frame_center: list[float] | None = None
    auto_fit: bool = True


class NarrationSpec(BaseModel):
    """Spoken voiceover narration and bookmark timing configuration."""

    model_config = ConfigDict(extra="allow")

    backend: str = "auto"
    model: str | None = None
    voice: str = "alba"
    text: str = ""
    cache_dir: str = "voiceover_cache"


class TimelineActionSpec(BaseModel):
    """Directed action scheduled on the animation timeline."""

    at: str = "start"
    action: str = "create"
    target: str | None = None
    targets: list[str] = Field(default_factory=list)
    run_time: float = 1.0
    duration: float | None = None
    rate_func: str = "linear"


class ScientificSceneSpec(BaseModel):
    """Root specification for a declarative scientific animation scene."""

    scene: SceneHeader = Field(default_factory=SceneHeader)
    data: list[DataSourceSpec] = Field(default_factory=list)
    coordinate_systems: list[CoordinateSystemSpec] = Field(
        default_factory=lambda: [CoordinateSystemSpec()]
    )
    visuals: list[VisualComponentSpec] = Field(default_factory=list)
    camera: CameraSpec = Field(default_factory=CameraSpec)
    narration: NarrationSpec | None = None
    timeline: list[TimelineActionSpec] = Field(default_factory=list)
