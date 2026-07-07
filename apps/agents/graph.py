from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from pydantic_graph import BaseNode, End, GraphBuilder, GraphRunContext, StepContext

from beat_planner_agent import beat_planner_agent
from classifier_agent import classifier_agent
from inspector_agent import inspector_agent
from lecture_planner import lecture_planner_agent
from narration_planner_agent import narration_planner_agent
from repair_agent import repair_agent
from scene_planner_agent import scene_planner_agent
from storyboard_planner import storyboard_planner_agent
from validation_agent import validation_agent

load_dotenv()


@dataclass
class AnimationState:
    user_request: str = ""
    classification: Any = None
    lecture_plan: Any = None
    storyboard: Any = None
    scenes: Any = None
    beats: Any = None
    narration: Any = None
    validation_result: Any = None
    repair_result: Any = None
    inspection_result: Any = None
    validation_attempts: int = 0
    max_validation_attempts: int = 3


@dataclass
class Classify(BaseNode[AnimationState]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> PlanLecture:
        result = await classifier_agent.run(ctx.state.user_request)
        ctx.state.classification = result.output
        return PlanLecture()


@dataclass
class PlanLecture(BaseNode[AnimationState]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> MakeStoryboard:
        result = await lecture_planner_agent.run(
            f"User request: {ctx.state.user_request}\n"
            f"Classification: {ctx.state.classification}"
        )
        ctx.state.lecture_plan = result.output
        return MakeStoryboard()


@dataclass
class MakeStoryboard(BaseNode[AnimationState]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> CreateScenes:
        result = await storyboard_planner_agent.run(
            f"User request: {ctx.state.user_request}\n"
            f"Lecture plan: {ctx.state.lecture_plan}"
        )
        ctx.state.storyboard = result.output
        return CreateScenes()


@dataclass
class CreateScenes(BaseNode[AnimationState]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> AddBeats:
        result = await scene_planner_agent.run(
            f"Storyboard: {ctx.state.storyboard}"
        )
        ctx.state.scenes = result.output
        return AddBeats()


@dataclass
class AddBeats(BaseNode[AnimationState]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> AddNarration:
        result = await beat_planner_agent.run(
            f"Scenes: {ctx.state.scenes}"
        )
        ctx.state.beats = result.output
        return AddNarration()


@dataclass
class AddNarration(BaseNode[AnimationState]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> Validate:
        result = await narration_planner_agent.run(
            f"Beats: {ctx.state.beats}"
        )
        ctx.state.narration = result.output
        return Validate()


@dataclass
class Validate(BaseNode[AnimationState]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> Repair | Inspect:
        ctx.state.validation_attempts += 1
        result = await validation_agent.run(
            f"Narration/IR: {ctx.state.narration}"
        )
        ctx.state.validation_result = result.output

        passed = getattr(result.output, "passed", False)
        if passed or ctx.state.validation_attempts >= ctx.state.max_validation_attempts:
            return Inspect()
        return Repair()


@dataclass
class Repair(BaseNode[AnimationState]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> Validate:
        result = await repair_agent.run(
            f"Issues: {ctx.state.validation_result}\nIR: {ctx.state.narration}"
        )
        ctx.state.repair_result = result.output
        ctx.state.narration = result.output
        return Validate()


@dataclass
class Inspect(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> End[str]:
        result = await inspector_agent.run(
            f"Final IR: {ctx.state.narration}"
        )
        ctx.state.inspection_result = result.output
        return End(str(result.output))


g = GraphBuilder(state_type=AnimationState, output_type=str)


@g.step
async def start(ctx: StepContext[AnimationState, None, None]) -> Classify:
    return Classify()


g.add(
    g.node(Classify),
    g.node(PlanLecture),
    g.node(MakeStoryboard),
    g.node(CreateScenes),
    g.node(AddBeats),
    g.node(AddNarration),
    g.node(Validate),
    g.node(Repair),
    g.node(Inspect),
    g.edge_from(g.start_node).to(start),
)

animation_graph = g.build()

if __name__ == "__main__":
    print(animation_graph.render())
