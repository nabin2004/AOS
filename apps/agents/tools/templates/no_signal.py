"""
DVD-logo screensaver on a "NO SIGNAL" CRT static background.

Why this is one scene, not two composited later:
  The static needs to regenerate every frame (an ImageMobject updater),
  and the logo needs its own per-frame physics updater. Manim runs all
  updaters against the same clock each frame, so keeping them in one
  Scene guarantees they stay in sync -- no risk of the static and the
  bounce drifting out of step if rendered separately and layered in
  post.

Bounce math (unchanged from the original, it was already correct):
  Velocities are derived from the period T and integers a, b so the
  logo's trajectory is EXACTLY periodic over T seconds -> the render
  loops seamlessly. Over one period the logo bounces 2*(a+b) times;
  choosing a+b as a multiple of 7 (the number of colours) means the
  colour cycle also lands back on its starting colour at t = T.

What changed from the original:
  - Added the CRT "no signal" static background (grayscale noise +
    scanlines + flicker + vignette), reusing the technique from
    tv_static.py, since a scene named "NoSignal" should look like one.
  - Bounce detection now distinguishes an edge hit from a genuine
    CORNER hit (both axes in the same frame) and fires the classic
    DVD-logo Easter egg: a quick pop/flash on the logo.
  - Flicker "NO SIGNAL" caption in the corner for the CRT feel.
  - Z-indexing so the logo always renders above the static/vignette.

RENDER (from this directory):
    uv run manim -ql --media_dir . dvd_logo_no_signal.py DVDLogoNoSignal
"""

from manim import *
import numpy as np


# ---------------------------------------------------------------- static ----


def _grayscale_noise(h: int, w: int, contrast: float = 1.5) -> np.ndarray:
    """Uniform grayscale noise, contrast-boosted toward black/white."""
    noise = np.random.randint(0, 255, (h, w), dtype=np.uint8).astype(np.float32)
    noise = (noise - 127.5) * contrast + 127.5
    return np.clip(noise, 0, 255).astype(np.uint8)


def _static_frame(h: int, w: int) -> np.ndarray:
    """One frame of CRT-style static: noise + scanlines + glitch + flicker."""
    gray = _grayscale_noise(h, w).astype(np.float32)
    gray = np.clip(gray, 15, 235)  # avoid pure black/white so the logo pops

    gray[::2, :] *= 0.55  # scanlines

    if np.random.random() < 0.12:  # occasional sync-roll glitch band
        row = np.random.randint(0, h)
        gray[row : min(row + 2, h), :] = 255

    flicker = np.random.uniform(0.8, 1.0)
    gray = np.clip(gray * flicker, 0, 255).astype(np.uint8)
    return np.stack([gray, gray, gray], axis=-1)  # broadcast to true gray RGB


class DVDLogoNoSignal(Scene):
    def construct(self):
        tex_w, tex_h = 192, 108

        # ---- background static ----
        static = ImageMobject(_static_frame(tex_h, tex_w))
        static.width = config.frame_width
        static.height = config.frame_height
        static.set_z_index(0)

        def update_static(mob, dt):
            mob.pixel_array[:, :, :3] = _static_frame(tex_h, tex_w)
            mob.pixel_array = mob.pixel_array

        static.add_updater(update_static)

        vignette = Rectangle(
            width=config.frame_width,
            height=config.frame_height,
            fill_color=BLACK,
            fill_opacity=0.4,
            stroke_width=0,
        )
        vignette.set_z_index(1)

        # ---- "NO SIGNAL" caption, flickering ----
        caption = Text("NO SIGNAL", font_size=28, color=WHITE)
        caption.to_corner(UL, buff=0.4)
        caption.set_z_index(2)

        def update_caption(mob, dt):
            mob.set_opacity(0.0 if np.random.random() < 0.12 else 1.0)

        caption.add_updater(update_caption)

        self.add(static, vignette, caption)

        # ---- DVD logo ----
        dvd_logo = VGroup(
            Text("PROMPT", weight="BOLD", font_size=96),
            Ellipse(
                width=1.6,
                height=0.35,
                fill_color=BLACK,
                fill_opacity=0.35,
                stroke_width=0,
            ),
        )
        dvd_logo.arrange(DOWN, buff=0.05)
        dvd_logo.scale(0.7)
        dvd_logo.set_color(BLUE)
        dvd_logo.set_z_index(3)

        # Bounce region (margins keep the logo fully on screen)
        margin_x, margin_y = 0.7, 0.5
        left = -config.frame_width / 2 + margin_x
        right = config.frame_width / 2 - margin_x
        bottom = -config.frame_height / 2 + margin_y
        top = config.frame_height / 2 - margin_y
        W, H = right - left, top - bottom

        # Period T and integers a, b so a+b is a multiple of 7
        # -> colour cycle (2*(a+b) bounces) realigns exactly at t = T.
        T = 20
        a, b = 2, 5
        velocity = np.array([2 * W * a / T, 2 * H * b / T, 0.0])

        colors = [BLUE, RED, GREEN, YELLOW, PURPLE, ORANGE, TEAL]
        color_index = 0

        # Corner-hit pop (classic Easter egg). Tracks the scale factor
        # currently applied so it can be cleanly undone next frame
        # instead of compounding.
        pop_age = None
        pop_duration = 0.35
        pop_scale_applied = 1.0

        dvd_logo.move_to(ORIGIN)

        def update_logo(mob, dt):
            nonlocal velocity, color_index, pop_age, pop_scale_applied

            mob.shift(velocity * dt)
            x, y = mob.get_center()[0], mob.get_center()[1]
            hit_x = hit_y = False

            if x <= left:
                mob.set_x(left)
                velocity[0] *= -1
                hit_x = True
            elif x >= right:
                mob.set_x(right)
                velocity[0] *= -1
                hit_x = True

            if y <= bottom:
                mob.set_y(bottom)
                velocity[1] *= -1
                hit_y = True
            elif y >= top:
                mob.set_y(top)
                velocity[1] *= -1
                hit_y = True

            if hit_x or hit_y:
                color_index = (color_index + 1) % len(colors)
                mob.set_color(colors[color_index])

            if hit_x and hit_y:
                pop_age = 0.0  # exact corner -> trigger the pop

            # Animate the pop over a few frames without compounding scale.
            if pop_age is not None:
                pop_age += dt
                if pop_age >= pop_duration:
                    target_scale = 1.0
                    pop_age = None
                else:
                    progress = pop_age / pop_duration
                    target_scale = 1 + 0.3 * np.sin(progress * PI)
                mob.scale(target_scale / pop_scale_applied)
                pop_scale_applied = target_scale
            elif pop_scale_applied != 1.0:
                mob.scale(1.0 / pop_scale_applied)
                pop_scale_applied = 1.0

        dvd_logo.add_updater(update_logo)
        self.add(dvd_logo)

        # Runs for exactly one period -- state repeats, so looping the
        # rendered clip is seamless.
        self.wait(T)

        dvd_logo.clear_updaters()
        static.clear_updaters()
        caption.clear_updaters()
