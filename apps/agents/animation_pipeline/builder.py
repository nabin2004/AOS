"""Graph builder for constructing the Pydantic Graph animation state machine."""

from __future__ import annotations

from pydantic_graph import Graph, GraphBuilder

from animation_pipeline.nodes import (
    ClassifyNode,
    CodeAgentNode,
    PlanLectureNode,
    PlanTeachingScriptNode,
)
from animation_pipeline.state import AnimationState


class AnimationGraphBuilder:
    """Encapsulates the construction, wiring, and assembly of the animation graph."""

    def __init__(self, name: str = "Manim Animation Graph") -> None:
        self.name = name
        self._builder = GraphBuilder(
            state_type=AnimationState,
            output_type=str,
            name=self.name,
        )
        self._is_built = False
        self._graph: Graph[AnimationState, None, str] | None = None

    def _register_steps(self) -> None:
        @self._builder.step
        async def _start(state: AnimationState) -> ClassifyNode:
            return ClassifyNode()

        self._builder.add(
            self._builder.node(ClassifyNode),
            self._builder.node(PlanLectureNode),
            self._builder.node(PlanTeachingScriptNode),
            self._builder.node(CodeAgentNode),
            self._builder.edge_from(self._builder.start_node).to(_start),
        )

    def build(self) -> Graph[AnimationState, None, str]:
        """Compile and return the initialized animation Graph."""
        if not self._is_built:
            self._register_steps()
            self._graph = self._builder.build()
            self._is_built = True
        assert self._graph is not None
        return self._graph
