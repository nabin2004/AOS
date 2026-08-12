"""Demo: BFS traversal with glowing visit order (Manim defaults)."""

from manim import *

from manim_dsa.compute.graph_search import DEFAULT_GRAPH, bfs_steps
from manim_viz import graph_nodes_edges


class DemoBFS(Scene):
    def construct(self):
        title = Text("Breadth-first search (BFS)", font_size=36)
        title.to_edge(UP)
        self.play(Write(title), run_time=0.6)

        graph = graph_nodes_edges(DEFAULT_GRAPH)
        graph.scale(1.15).shift(DOWN * 0.2)
        edges, nodes = graph[0], graph[1]
        self.play(Create(edges), run_time=0.7)
        self.play(LaggedStart(*[FadeIn(n, scale=0.8) for n in nodes], lag_ratio=0.1), run_time=1.0)

        # map label -> node mobject
        label_to_node = {}
        for n in nodes:
            label_to_node[n[1].text] = n

        steps = bfs_steps(DEFAULT_GRAPH, "A")
        order_text = Text("Order: ", font_size=28).to_edge(DOWN)
        order_vals = Text("", font_size=28, color=YELLOW).next_to(order_text, RIGHT)
        self.play(FadeIn(order_text), FadeIn(order_vals), run_time=0.4)

        seen = []
        last_current = None
        for step in steps:
            cur = step.get("current")
            if cur is None or cur == last_current:
                continue
            last_current = cur
            node = label_to_node.get(str(cur))
            if node is None:
                continue
            self.play(
                node[0].animate.set_fill(YELLOW, opacity=0.7).set_color(YELLOW),
                run_time=0.35,
            )
            seen.append(str(cur))
            new_vals = Text(" → ".join(seen), font_size=28, color=YELLOW).next_to(order_text, RIGHT)
            self.play(Transform(order_vals, new_vals), run_time=0.25)
            self.play(node[0].animate.set_fill(GREEN, opacity=0.55).set_color(GREEN), run_time=0.25)

        self.play(Indicate(order_vals, color=GREEN), run_time=0.7)
        self.wait(1.0)
