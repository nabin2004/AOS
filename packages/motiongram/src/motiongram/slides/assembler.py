"""Deck assembler: multi-slide rendering with caching and FFmpeg concatenation."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from motiongram.manimgram.runner import render_scene
from motiongram.slides.compiler import compile_deck

if TYPE_CHECKING:
    from motiongram.slides.schema import DeckSpec


def concatenate_slides(slide_videos: list[Path], output_path: Path) -> Path:
    """Concatenate multiple rendered slide MP4 videos into a single final presentation."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not slide_videos:
        raise ValueError("No slide videos provided for concatenation.")

    if len(slide_videos) == 1:
        shutil.copy2(slide_videos[0], output_path)
        return output_path

    concat_file = output_path.parent / "concat_list.txt"
    lines = [f"file '{v.resolve()}'" for v in slide_videos]
    concat_file.write_text("\n".join(lines), encoding="utf-8")

    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"

    # Try stream copy first (instantaneous, lossless)
    cmd_copy = [
        ffmpeg_bin,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output_path),
    ]

    proc = subprocess.run(cmd_copy, capture_output=True, text=True)
    if proc.returncode != 0:
        # Fallback to re-encoding if stream copy fails
        cmd_reencode = [
            ffmpeg_bin,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            str(output_path),
        ]
        proc_re = subprocess.run(cmd_reencode, capture_output=True, text=True)
        if proc_re.returncode != 0:
            raise RuntimeError(f"FFmpeg concatenation failed: {proc_re.stderr}")

    return output_path


def render_deck_slides(
    slide_scripts: list[Path],
    quality: str = "ql",
    still: bool = False,
    use_cache: bool = True,
    output_dir: Path | None = None,
    ultra_fast: bool = False,
) -> list[Path]:
    """Render all compiled slide scenes sequentially utilizing content-addressed caching."""
    rendered_artifacts: list[Path] = []

    custom_res = (640, 360) if ultra_fast else None
    fps = 10.0 if ultra_fast else None

    for script in slide_scripts:
        res = render_scene(
            script_path=script,
            quality=quality,
            still=still,
            use_cache=use_cache,
            output_dir=output_dir,
            custom_res=custom_res,
            fps=fps,
        )
        if not res.success:
            raise RuntimeError(
                f"Failed to render slide '{script.stem}': {res.error_summary or res.stderr}"
            )

        artifact = res.image_path if still else res.video_path
        if artifact and artifact.exists():
            rendered_artifacts.append(artifact)
        else:
            raise RuntimeError(f"Slide '{script.stem}' rendered without producing an artifact.")

    return rendered_artifacts


def build_deck(
    deck: DeckSpec,
    quality: str = "ql",
    output_file: Path | None = None,
    work_dir: Path | None = None,
    use_cache: bool = True,
    ultra_fast: bool = False,
) -> Path:
    """Full end-to-end pipeline: compile deck -> render with cache -> assemble MP4."""
    base_dir = work_dir or Path(f"output/decks/{deck.id}")
    final_output = output_file or base_dir / f"{deck.id}.mp4"

    # 1. Compile deck
    scripts = compile_deck(deck, output_dir=base_dir)

    # 2. Render all slides
    video_clips = render_deck_slides(
        slide_scripts=scripts,
        quality=quality,
        still=False,
        use_cache=use_cache,
        output_dir=base_dir / "media",
        ultra_fast=ultra_fast,
    )

    # 3. Concatenate slides
    return concatenate_slides(video_clips, final_output)
