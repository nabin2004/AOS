"""Video export via PyAV — streams Skia RGBA frames into H.264 MP4.

Optionally writes each rendered frame as PNG alongside muxing (single render pass).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import numpy.typing as npt

from motiongram.animate import smoothstep
from motiongram.core import Scene
from motiongram.render import SkiaRenderer


@dataclass(slots=True)
class PyAVEncoder:
    """Encodes a rendered scene to H.264 MP4; optional PNG sequence per frame."""

    scene: Scene
    output_path: str | Path
    renderer: SkiaRenderer = field(default_factory=SkiaRenderer)
    linear_timeline: bool = False
    frames_dir: str | Path | None = None
    audio_path: str | Path | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.output_path, Path):
            self.output_path = Path(self.output_path)
        if self.frames_dir is not None and not isinstance(self.frames_dir, Path):
            self.frames_dir = Path(self.frames_dir)
        if self.audio_path is not None and not isinstance(self.audio_path, Path):
            self.audio_path = Path(self.audio_path)

    def encode(self, *, verbose: bool = True) -> Path:
        """Render every frame and mux into an MP4 container.

        If ``frames_dir`` is set, each frame is also written as
        ``{frames_dir}/{index:06d}.png`` (1-based indices).

        Returns the output path on success.
        """
        import av

        scene = self.scene
        if scene.fps <= 0:
            raise ValueError("scene.fps must be positive")

        n_frames = max(1, round(scene.duration * scene.fps))
        dt = 1.0 / scene.fps

        w = scene.width if scene.width % 2 == 0 else scene.width + 1
        h = scene.height if scene.height % 2 == 0 else scene.height + 1

        frames_root: Path | None = None
        if self.frames_dir is not None:
            frames_root = self.frames_dir.expanduser().resolve()
            frames_root.mkdir(parents=True, exist_ok=True)

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        container = av.open(str(self.output_path), mode="w")
        stream = container.add_stream("libx264", rate=int(scene.fps))
        stream.width = w
        stream.height = h
        stream.pix_fmt = "yuv420p"
        stream.options = {"crf": "23", "preset": "medium"}

        audio_stream = None
        audio_in = None
        in_astream = None
        resampler = None
        if self.audio_path is not None and self.audio_path.is_file():
            try:
                audio_in = av.open(str(self.audio_path))
                in_astream = next((s for s in audio_in.streams if s.type == "audio"), None)
                if in_astream is not None:
                    target_rate = in_astream.rate or 24000
                    audio_stream = container.add_stream("aac", rate=target_rate)
                    resampler = av.AudioResampler(format="fltp", layout="stereo", rate=target_rate)
            except Exception as e:
                if verbose:
                    print(f"\n[Warning] Could not initialize audio stream: {e}", file=sys.stderr)

        try:
            frame_ease = None if self.linear_timeline else smoothstep
            for i in range(n_frames):
                t = min(scene.duration, (i + 1) * dt)
                rgba = self.renderer.render_frame(scene, t, ease=frame_ease)
                if frames_root is not None:
                    self._write_png(frames_root / f"{i + 1:06d}.png", rgba)
                rgb = self._rgba_to_rgb(rgba, w, h)
                video_frame = av.VideoFrame.from_ndarray(rgb, format="rgb24")
                video_frame.pts = i
                for packet in stream.encode(video_frame):
                    container.mux(packet)
                if verbose and (i % max(1, n_frames // 10) == 0 or i == n_frames - 1):
                    print(
                        f"\r  encoding: {i + 1}/{n_frames} frames",
                        end="",
                        file=sys.stderr,
                        flush=True,
                    )

            for packet in stream.encode():
                container.mux(packet)

            # Mux audio frames if audio stream configured
            has_audio = (
                audio_stream is not None
                and audio_in is not None
                and in_astream is not None
                and resampler is not None
            )
            if has_audio:
                assert audio_in is not None and in_astream is not None
                assert resampler is not None and audio_stream is not None
                for packet in audio_in.demux(in_astream):
                    for aframe in packet.decode():
                        resampled = resampler.resample(aframe)
                        if resampled:
                            for rf in resampled:
                                rf.pts = None
                                for a_packet in audio_stream.encode(rf):
                                    container.mux(a_packet)
                for a_packet in audio_stream.encode():
                    container.mux(a_packet)
        finally:
            if audio_in is not None:
                import contextlib
                with contextlib.suppress(Exception):
                    audio_in.close()
            container.close()

        if verbose:
            print(file=sys.stderr)

        return self.output_path

    @staticmethod
    def _write_png(path: Path, rgba: npt.NDArray[np.uint8]) -> None:
        import skia

        arr = np.ascontiguousarray(rgba)
        img = skia.Image.fromarray(arr, skia.ColorType.kRGBA_8888_ColorType)
        data = img.encodeToData(skia.EncodedImageFormat.kPNG, 100)
        path.write_bytes(bytes(data))

    @staticmethod
    def _rgba_to_rgb(
        rgba: npt.NDArray[np.uint8], target_w: int, target_h: int
    ) -> npt.NDArray[np.uint8]:
        """Convert RGBA (potentially odd-sized) to RGB padded to even dimensions."""
        h, w = rgba.shape[:2]
        rgb = rgba[:, :, :3]
        if h == target_h and w == target_w:
            return np.ascontiguousarray(rgb)
        padded = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        padded[:h, :w, :] = rgb
        return padded
