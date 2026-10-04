"""Compose multi-scene manifests into a single renderable program."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from motiongram.core import Scene
from motiongram.manifest.build import BuiltScene, build_scene
from motiongram.manifest.properties import hex_to_rgb
from motiongram.manifest.recipes import expand_recipe
from motiongram.manifest.schema import (
    CanvasSpec,
    ElementSpec,
    ManifestDocument,
    SceneSpec,
    SectionSpec,
)
from motiongram.manifest.time import parse_time
from motiongram.subtitles import SubtitleCue, SubtitleStyle, SubtitleTrack


@dataclass
class SceneSegment:
    scene_spec: SceneSpec
    built: BuiltScene
    time_offset: float = 0.0


@dataclass
class ComposedProgram:
    document: ManifestDocument
    segments: list[SceneSegment] = field(default_factory=list)
    canvas: CanvasSpec = field(default_factory=CanvasSpec)
    clear_color: tuple[int, int, int] = (0, 0, 0)
    output_path: Path = field(default_factory=lambda: Path("output.mp4"))
    uses_custom_easing: bool = False
    voiceover_paths: list[Path] = field(default_factory=list)
    base_dir: Path = field(default_factory=Path.cwd)


def _section_title_scene(section: SectionSpec, *, canvas: CanvasSpec, duration: float) -> SceneSpec:
    return SceneSpec(
        id=f"__section_title_{section.id}",
        duration=duration,
        elements=[
            ElementSpec(
                id="title",
                type="Text",
                properties={
                    "content": section.title,
                    "x": canvas.width * 0.08,
                    "y": canvas.height * 0.35,
                    "font_size": 72.0,
                    "color": "#ffffff",
                },
            ),
            ElementSpec(
                id="description",
                type="Text",
                properties={
                    "content": section.description,
                    "x": canvas.width * 0.08,
                    "y": canvas.height * 0.52,
                    "font_size": 36.0,
                    "color": "#abb2bf",
                },
            ),
        ],
    )


def _build_segment(
    spec: SceneSpec,
    *,
    canvas: CanvasSpec,
    base_dir: Path,
) -> BuiltScene:
    built = build_scene(spec, canvas=canvas, base_dir=base_dir)
    if spec.recipe is not None:
        expand_recipe(built.scene, spec.recipe, built.node_map)
    return built


def compose_program(doc: ManifestDocument, *, base_dir: Path) -> ComposedProgram:
    """Flatten scenes and sections into ordered segments."""
    canvas = doc.canvas
    clear_color = hex_to_rgb(canvas.background)
    output_path = Path(doc.output.file)
    segments: list[SceneSegment] = []
    uses_easing = False
    voiceovers: list[Path] = []

    for scene_spec in doc.scenes:
        built = _build_segment(scene_spec, canvas=canvas, base_dir=base_dir)
        uses_easing = uses_easing or built.uses_custom_easing
        if built.voiceover_path:
            voiceovers.append(built.voiceover_path)
        segments.append(SceneSegment(scene_spec=scene_spec, built=built))

    for section in doc.sections:
        if doc.options.generate_section_titles and section.title:
            title_spec = _section_title_scene(
                section,
                canvas=canvas,
                duration=parse_time(
                    doc.options.section_title_duration,
                    field="options.section_title_duration",
                ),
            )
            built = _build_segment(title_spec, canvas=canvas, base_dir=base_dir)
            segments.append(SceneSegment(scene_spec=title_spec, built=built))

        for scene_spec in section.scenes:
            built = _build_segment(scene_spec, canvas=canvas, base_dir=base_dir)
            uses_easing = uses_easing or built.uses_custom_easing
            if built.voiceover_path:
                voiceovers.append(built.voiceover_path)
            segments.append(SceneSegment(scene_spec=scene_spec, built=built))

    if doc.lecture and doc.lecture.voiceover:
        vp = (base_dir / doc.lecture.voiceover).resolve()
        if vp.is_file():
            voiceovers.append(vp)

    return ComposedProgram(
        document=doc,
        segments=segments,
        canvas=canvas,
        clear_color=clear_color,
        output_path=output_path,
        uses_custom_easing=uses_easing,
        voiceover_paths=voiceovers,
        base_dir=base_dir,
    )


def merge_to_single_scene(program: ComposedProgram) -> Scene:
    """Merge all segments into one scene with time-offset timelines."""
    if not program.segments:
        raise ValueError("program has no segments")

    canvas = program.canvas
    merged = Scene(width=canvas.width, height=canvas.height, fps=canvas.fps, duration=0.0)
    all_cues: list[SubtitleCue] = []
    style: SubtitleStyle | None = None
    offset = 0.0

    for segment in program.segments:
        src = segment.built.scene
        segment.time_offset = offset
        dur = src.duration

        for child in list(src.root.children):
            merged.root.add(child)

        for start, end, target, anim in src.timeline.entries:
            merged.add_animation(start + offset, end + offset, target, anim)

        if src.subtitle_track is not None:
            style = src.subtitle_track.style
            for cue in src.subtitle_track.cues:
                all_cues.append(
                    SubtitleCue(
                        start=cue.start + offset,
                        end=cue.end + offset,
                        typst=cue.typst,
                        plain=cue.plain,
                        voice=cue.voice,
                        settings=cue.settings,
                    )
                )

        offset += dur

    merged.duration = offset
    if all_cues:
        merged.subtitle_track = SubtitleTrack(cues=tuple(all_cues), style=style or SubtitleStyle())

    return merged
