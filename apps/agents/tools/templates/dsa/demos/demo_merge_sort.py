"""Demo: merge sort with animated bar swaps (Manim defaults)."""

from manim import *

from manim_dsa.compute.sorting import merge_sort_steps


class DemoMergeSort(Scene):
    def construct(self):
        title = Text("Merge sort", font_size=36)
        title.to_edge(UP)
        self.play(Write(title), run_time=0.5)

        values = [8, 3, 7, 1, 9, 2]
        steps = merge_sort_steps(values)
        # subsample steps for a snappy demo
        key_steps = [steps[0]] + [s for i, s in enumerate(steps) if i % max(1, len(steps) // 12) == 0] + [steps[-1]]

        def make_bars(arr):
            peak = max(arr) or 1
            bars = VGroup()
            for v in arr:
                h = max(0.35, 2.8 * (v / peak))
                rect = Rectangle(width=0.7, height=h, color=BLUE, fill_opacity=0.85, stroke_width=1)
                lab = Text(str(v), font_size=22)
                g = VGroup(rect, lab).arrange(DOWN, buff=0.08)
                bars.add(g)
            bars.arrange(RIGHT, buff=0.25)
            bars.move_to(ORIGIN + DOWN * 0.3)
            return bars

        bars = make_bars(key_steps[0]["array"])
        self.play(LaggedStart(*[GrowFromEdge(b[0], DOWN) for b in bars], lag_ratio=0.08), run_time=1.2)

        status = Text("sorting…", font_size=24, color=GREY_B).to_edge(DOWN)
        self.play(FadeIn(status), run_time=0.3)

        for step in key_steps[1:]:
            new_bars = make_bars(step["array"])
            # highlight compared / placed indices
            for idx in step.get("highlights") or []:
                if 0 <= idx < len(new_bars):
                    new_bars[idx][0].set_color(YELLOW)
            self.play(Transform(bars, new_bars), run_time=0.35)

        done = Text(f"Sorted: {steps[-1]['array']}", font_size=28, color=GREEN)
        done.to_edge(DOWN)
        self.play(Transform(status, done), run_time=0.5)
        self.play(*[Indicate(b[0], color=GREEN) for b in bars], run_time=0.8)
        self.wait(1.0)
