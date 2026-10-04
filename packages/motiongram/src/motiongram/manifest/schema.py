"""Pydantic models for YAML manifest documents."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class CanvasSpec(BaseModel):
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    background: str = "#000000"


class OutputSpec(BaseModel):
    file: str = "output.mp4"
    codec: str = "h264"


class SectionTitleStyleSpec(BaseModel):
    font_size: float = 72.0
    color: str = "#ffffff"
    background: str = "#000000cc"


class OptionsSpec(BaseModel):
    generate_section_titles: bool = False
    section_title_duration: float | str = 3.0
    section_title_style: SectionTitleStyleSpec = Field(default_factory=SectionTitleStyleSpec)


class LectureMeta(BaseModel):
    title: str = ""
    subtitle: str = ""
    author: str = ""
    series: str = ""
    language: str = "en"
    description: str = ""
    voiceover: str | None = None
    narration: Any = None
    subtitles: str | list[dict[str, Any]] | None = None


class CameraInitialSpec(BaseModel):
    position: list[float] = Field(default_factory=lambda: [960.0, 540.0])
    zoom: float = 1.0


class CameraSpec(BaseModel):
    initial: CameraInitialSpec | None = None
    animations: list[dict[str, Any]] = Field(default_factory=list)


class ElementSpec(BaseModel):
    id: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)
    animations: list[dict[str, Any]] = Field(default_factory=list)


class RecipeSpec(BaseModel):
    type: str
    layers: list[str] = Field(default_factory=list)
    start: float | str = 0.0
    duration: float | str = 1.0

    model_config = {"extra": "allow"}


class SceneSpec(BaseModel):
    id: str
    duration: float | str
    canvas: CanvasSpec | None = None
    voiceover: str | None = None
    narration: Any = None
    subtitles: str | list[dict[str, Any]] | None = None
    camera: CameraSpec | None = None
    elements: list[ElementSpec] = Field(default_factory=list)
    animations: list[dict[str, Any]] = Field(default_factory=list)
    recipe: RecipeSpec | None = None

    @field_validator("duration", mode="before")
    @classmethod
    def _duration_raw(cls, v: object) -> object:
        return v


class SectionSpec(BaseModel):
    id: str
    title: str = ""
    description: str = ""
    scenes: list[SceneSpec] = Field(default_factory=list)


class ManifestDocument(BaseModel):
    version: Literal["1.0"] = "1.0"
    lecture: LectureMeta | None = None
    canvas: CanvasSpec = Field(default_factory=CanvasSpec)
    output: OutputSpec = Field(default_factory=OutputSpec)
    options: OptionsSpec = Field(default_factory=OptionsSpec)
    scenes: list[SceneSpec] = Field(default_factory=list)
    sections: list[SectionSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def _has_content(self) -> ManifestDocument:
        if not self.scenes and not self.sections:
            raise ValueError("manifest must include 'scenes' and/or 'sections'")
        return self
