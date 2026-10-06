"""Pydantic models for the ManimGram DSL (declarative animation specification)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CanvasConfig(BaseModel):
    """Canvas and video configuration."""
    model_config = ConfigDict(extra="allow")

    pixel_width: int = 1920
    pixel_height: int = 1080
    frame_rate: int = 30
    voice: str = "alba"
    backend: str = "pocket-tts"
    model: str | None = None
    cache_dir: str = "voiceover_cache"
    speech_service: str = "AOSSpeechService"


class VoiceoverConfig(BaseModel):
    """Voiceover and TTS configuration."""
    model_config = ConfigDict(extra="allow")

    voice: str = "alba"
    backend: str = "pocket-tts"
    model: str | None = None
    cache_dir: str = "voiceover_cache"
    speech_service: str = "AOSSpeechService"


class SceneSpec(BaseModel):
    """Top-level scene specification."""
    model_config = ConfigDict(extra="allow")

    class_name: str = "GeneratedScene"
    type: Literal["Scene", "MovingCameraScene", "ThreeDScene", "VoiceoverScene"] = "Scene"
    background_color: str = "#1C1C1C"
    config: CanvasConfig = Field(default_factory=CanvasConfig)
    voiceover: VoiceoverConfig | None = None


class NextToSpec(BaseModel):
    """Relative placement next to another mobject."""
    target: str
    direction: Literal["UP", "DOWN", "LEFT", "RIGHT", "UL", "UR", "DL", "DR", "IN", "OUT"] = "RIGHT"
    buff: float = 0.5
    aligned_edge: Literal["UP", "DOWN", "LEFT", "RIGHT"] | None = None


class AlignToSpec(BaseModel):
    """Alignment to an edge or center of another mobject."""
    target: str
    direction: Literal["UP", "DOWN", "LEFT", "RIGHT"] = "UP"


class EdgeSpec(BaseModel):
    """Edge alignment on canvas."""
    edge: Literal["UP", "DOWN", "LEFT", "RIGHT"] = "UP"
    buff: float = 0.5


class CornerSpec(BaseModel):
    """Corner placement on canvas."""
    corner: Literal["UL", "UR", "DL", "DR"] = "UL"
    buff: float = 0.5


class LayoutSpec(BaseModel):
    """Layout and positioning constraints for a mobject."""
    model_config = ConfigDict(extra="allow")

    shift: list[float] | None = None
    move_to: list[float] | str | None = None
    next_to: NextToSpec | None = None
    to_edge: EdgeSpec | None = None
    to_corner: CornerSpec | None = None
    align_to: AlignToSpec | None = None
    center: bool | None = None
    scale: float | None = None


class StateSpec(BaseModel):
    """Initial rendering state of a mobject."""
    model_config = ConfigDict(extra="allow")

    opacity: float | None = None
    visible: bool = True
    scale: float | None = None


class MobjectSpec(BaseModel):
    """Specification of a visual entity (mobject)."""
    model_config = ConfigDict(extra="allow")

    id: str
    type: str  # Matrix, MathTex, Text, Circle, Square, Rectangle, Axes, ThreeDAxes, Surface, etc.
    props: dict[str, Any] = Field(default_factory=dict)
    layout: LayoutSpec | None = None
    state: StateSpec | None = None


class RouteMappingSpec(BaseModel):
    """Routing of a sub-element during a routed transform."""
    model_config = ConfigDict(populate_by_name=True)

    from_selector: str = Field(alias="from")
    to_selector: str = Field(alias="to")
    animation: str = "ReplacementTransform"


class CameraInitialSpec(BaseModel):
    """Initial camera orientation and zoom."""
    model_config = ConfigDict(extra="allow")

    phi: float | None = None
    theta: float | None = None
    gamma: float | None = None
    zoom: float | None = None
    frame_center: list[float] | None = None


class CameraActionSpec(BaseModel):
    """Dynamic camera operations (Orbit, Focus, Pan, Zoom)."""
    model_config = ConfigDict(extra="allow")

    type: Literal["Orbit", "Focus", "Pan", "Zoom", "ResetView"]
    target: str | None = None
    phi: float | None = None
    theta: float | None = None
    theta_delta: float | None = None
    rate: float | None = None
    zoom: float | None = None
    frame_center: list[float] | None = None
    run_time: float = 1.0


class CameraSpec(BaseModel):
    """Complete camera setup and choreography."""
    model_config = ConfigDict(extra="allow")

    initial: CameraInitialSpec | None = None
    actions: list[CameraActionSpec] = Field(default_factory=list)


class TimelineActionSpec(BaseModel):
    """Single animation or wait command on the timeline."""
    model_config = ConfigDict(extra="allow")

    # Action type (Create, Write, FadeIn, Transform, WaitUntilBookmark, etc.)
    action: str
    target: str | None = None
    source: str | None = None
    targets: list[str] | None = None
    mark: str | None = None  # Bookmark name for WaitUntilBookmark
    duration: float | None = None  # Optional duration alias for Wait
    run_time: float = 1.0
    rate_func: str | None = None
    routes: list[RouteMappingSpec] | None = None
    fallback: Literal["by_index", "fade", "none"] | None = "by_index"
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("run_time", mode="before")
    @classmethod
    def _parse_run_time(cls, v: Any) -> float:
        if isinstance(v, str):
            v = v.rstrip("s")
            return float(v)
        return float(v)


class VoiceoverBlockSpec(BaseModel):
    """Narration block synchronized with local TTS audio and bookmarks."""
    model_config = ConfigDict(extra="allow")

    type: Literal["voiceover_block"] = "voiceover_block"
    text: str
    actions: list[TimelineActionSpec] = Field(default_factory=list)


class ManimGramScene(BaseModel):
    """Root ManimGram document structure."""
    model_config = ConfigDict(extra="allow")

    scene: SceneSpec = Field(default_factory=SceneSpec)
    camera: CameraSpec | None = None
    mobjects: list[MobjectSpec] = Field(default_factory=list)
    timeline: list[VoiceoverBlockSpec | TimelineActionSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_unique_ids(self) -> ManimGramScene:
        ids = set()
        for mob in self.mobjects:
            if mob.id in ids:
                raise ValueError(f"Duplicate mobject id '{mob.id}' found")
            ids.add(mob.id)
        return self
