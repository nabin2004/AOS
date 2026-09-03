"""Reference scene extracted from 3b1b/videos.

Source: _2026/print_gallery/supplements.py
Class: AppreciatingWithMath
Year: 2026
License: CC BY-NC-SA 4.0 (Grant Sanderson / 3Blue1Brown)
"""
from manim_imports_ext import *

class AppreciatingWithMath(InteractiveScene):
    def construct(self):
        # Test
        randy = Randolph()
        randy.to_edge(DOWN)

        path = Path(
            self.file_writer.get_output_file_rootname().parent.parent,
            'exponential/LogImage.png',
        )
        log_image = ImageMobject(path)
        log_image.set_width(7)
        log_image.to_corner(UL)
        log_label = Tex(R"\ln(z)", t2c={"z": BLUE})
        log_label.move_to(log_image).shift(0.45 * UP)
        log_group = Group(log_image, log_label)

        self.play(
            randy.change("raise_left_hand", 3 * UL),
            FadeIn(log_image, UP),
            Write(log_label),
        )
        self.play(Blink(randy))
        self.wait()
        self.play(randy.change("pondering", 3 * UR))
        self.play(Blink(randy))
        self.wait()

        # Add bubble
        rect = Rectangle(3, 1.5).set_opacity(0)
        bubble = randy.get_bubble(rect, direction=RIGHT)
        self.play(
            Write(bubble),
            log_group.animate.replace(rect, 0),
            randy.animate.look_at(bubble)
        )
        self.play(Blink(randy))
        self.play(randy.change("tease", 3 * UR))
        self.wait()
        self.play(Blink(randy))
        self.wait()
