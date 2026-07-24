"""
TV static / CRT noise effects for Manim.

Three scenes:
  1. TVStatic          - pure black/white noise, fast (ImageMobject-based)
  2. TVStaticCRT       - noise + scanlines + flicker + vignette, still fast
  3. TVStaticTransition - static burst used as a scene transition

Why ImageMobject instead of a grid of Rectangles:
  A grid of N Rectangle mobjects means N separate objects Manim has to
  track, re-fill, and re-render every frame -> slow for anything above
  a few thousand pixels. An ImageMobject is ONE mobject whose pixel
  buffer is a numpy array, so "randomizing every pixel" is just a numpy
  call (np.random.randint) and re-assigning .pixel_array. This scales
  to full HD resolutions without frame-rate collapse.

Why grayscale, not RGB noise:
  Randomizing R, G, and B independently (the old approach) makes each
  pixel an arbitrary color, since a pixel gets an unrelated random value
  per channel -> the frame reads as rainbow confetti, not TV snow. Real
  analog static is monochrome: every pixel is some shade of gray, i.e.
  R == G == B. So we generate ONE random value per pixel and broadcast
  it across all three channels. A mild contrast boost is applied too,
  since real snow looks like crisp black/white speckle rather than the
  smooth mid-gray haze you get from raw uniform noise.

RENDER (from this directory):
    uv run manim -ql --media_dir . tv_static.py TVStatic
    uv run manim -ql --media_dir . tv_static.py TVStaticCRT
    uv run manim -ql --media_dir . tv_static.py TVStaticTransition
"""

from manim import *
import numpy as np


def _grayscale_noise(h: int, w: int, contrast: float = 1.35) -> np.ndarray:
    """Uniform random grayscale noise (h, w), uint8, contrast-boosted.

    contrast > 1 pushes mid-grays toward black/white for a punchier,
    more "authentic snow" look. contrast == 1 leaves it as raw uniform
    noise (softer, more uniform-gray).
    """
    noise = np.random.randint(0, 255, (h, w), dtype=np.uint8).astype(np.float32)
    noise = (noise - 127.5) * contrast + 127.5
    return np.clip(noise, 0, 255).astype(np.uint8)


def _to_rgb(gray: np.ndarray) -> np.ndarray:
    """Broadcast a (h, w) grayscale array to (h, w, 3) so R == G == B."""
    return np.stack([gray, gray, gray], axis=-1)


def _fullframe_static(frame: np.ndarray) -> ImageMobject:
    """Create an ImageMobject scaled to the current frame."""
    static = ImageMobject(frame)
    static.width = config.frame_width
    static.height = config.frame_height
    return static


def _attach_noise_updater(static: ImageMobject, frame_fn) -> None:
    """Regenerate pixel data every frame."""

    def update_static(mob: ImageMobject, dt: float) -> None:
        mob.pixel_array[:, :, :3] = frame_fn()
        # Re-assign to bust Manim's texture cache.
        mob.pixel_array = mob.pixel_array

    static.add_updater(update_static)


class TVStatic(Scene):
    def construct(self):
        tex_w, tex_h = 192, 108  # 16:9, cheap to regenerate every frame

        def random_frame():
            return _to_rgb(_grayscale_noise(tex_h, tex_w))

        static = _fullframe_static(random_frame())
        _attach_noise_updater(static, random_frame)

        self.add(static)
        self.wait(10)
        static.clear_updaters()
        # self.play(FadeOut(static))


class TVStaticCRT(Scene):
    """A more convincing CRT-style static: noise + scanlines + flicker + vignette."""

    def construct(self):
        tex_w, tex_h = 192, 108

        def random_frame():
            gray = _grayscale_noise(tex_h, tex_w, contrast=1.5).astype(np.float32)
            # Keep a floor above pure black so scanlines still read as gray, not void.
            gray = np.clip(gray, 25, 255)

            # Scanlines: darken every other row.
            gray[::2, :] *= 0.5

            # Occasional bright horizontal glitch band (vertical-sync roll).
            if np.random.random() < 0.15:
                row = np.random.randint(0, tex_h)
                band = slice(row, min(row + 2, tex_h))
                gray[band, :] = 255

            # Global flicker (brightness jitter frame to frame).
            flicker = np.random.uniform(0.75, 1.0)
            gray = gray * flicker

            gray = np.clip(gray, 0, 255).astype(np.uint8)
            return _to_rgb(gray)

        static = _fullframe_static(random_frame())
        _attach_noise_updater(static, random_frame)

        vignette = Rectangle(
            width=config.frame_width,
            height=config.frame_height,
            fill_color=BLACK,
            fill_opacity=0.35,
            stroke_width=0,
        )
        vignette.set_z_index(1)

        self.add(static, vignette)
        self.wait(3)
        static.clear_updaters()
        self.play(FadeOut(static, vignette))


class TVStaticTransition(Scene):
    """Example: using static as a transition between two scenes."""

    def construct(self):
        sq = Square(color=BLUE)
        self.play(Create(sq))
        self.wait(0.5)

        tex_w, tex_h = 160, 90

        def random_frame():
            return _to_rgb(_grayscale_noise(tex_h, tex_w))

        static = _fullframe_static(random_frame())
        static.set_opacity(0)
        static.set_z_index(2)
        _attach_noise_updater(static, random_frame)
        self.add(static)

        # Static bursts in over the square, then out to reveal the next scene.
        self.play(static.animate.set_opacity(1), FadeOut(sq), run_time=0.3)
        self.wait(0.4)

        circ = Circle(color=RED)
        self.add(circ)
        self.play(static.animate.set_opacity(0), run_time=0.3)

        static.clear_updaters()
        self.remove(static)
        self.wait(0.5)
