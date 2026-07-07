from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from ir.manim_ir import Beat, Lecture, LectureIR, Scene, Storyboard
from pydantic_graph import BaseNode, End, GraphBuilder, GraphRunContext, StepContext

from beat_planner_agent import beat_planner_agent
from classifier_agent import Classification, classifier_agent
from inspector_agent import InspectionResult, inspector_agent
from lecture_planner import lecture_planner_agent
from narration_planner_agent import narration_planner_agent
from repair_agent import repair_agent
from scene_planner_agent import scene_planner_agent
from storyboard_planner import storyboard_planner_agent
from tools import ToolDeps
from validation_agent import ValidationResult, validation_agent

load_dotenv()

TOOL_DEPS = ToolDeps(workspace_dir=Path(__file__).parent / "workspace")


@dataclass
class AnimationState:
    user_request: str = ""
    classification: Classification | None = None
    lecture_plan: Lecture | None = None
    storyboard: Storyboard | None = None
    scenes: list[Scene] | None = None
    beats: list[Beat] | None = None
    narration_beats: list[Beat] | None = None
    validation_result: ValidationResult | None = None
    lecture_ir: LectureIR | None = None
    inspection_result: InspectionResult | None = None
    validation_attempts: int = 0
    max_validation_attempts: int = 3


def _ir_context(state: AnimationState) -> str:
    if state.lecture_ir is not None:
        return state.lecture_ir.model_dump_json()
    parts = []
    if state.lecture_plan is not None:
        parts.append(f"Lecture: {state.lecture_plan.model_dump_json()}")
    if state.storyboard is not None:
        parts.append(f"Storyboard: {state.storyboard.model_dump_json()}")
    if state.scenes is not None:
        parts.append(f"Scenes: {[s.model_dump_json() for s in state.scenes]}")
    if state.narration_beats is not None:
        parts.append(f"Beats: {[b.model_dump_json() for b in state.narration_beats]}")
    return "\n".join(parts)


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
        ctx.state.narration_beats = result.output
        return Validate()


@dataclass
class Validate(BaseNode[AnimationState]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> Repair | Inspect:
        ctx.state.validation_attempts += 1
        result = await validation_agent.run(_ir_context(ctx.state), deps=TOOL_DEPS)
        ctx.state.validation_result = result.output

        if result.output.passed or ctx.state.validation_attempts >= ctx.state.max_validation_attempts:
            return Inspect()
        return Repair()


@dataclass
class Repair(BaseNode[AnimationState]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> Validate:
        issues = ctx.state.validation_result.issues if ctx.state.validation_result else []
        result = await repair_agent.run(
            f"Issues: {issues}\n\n{_ir_context(ctx.state)}",
            deps=TOOL_DEPS,
        )
        ctx.state.lecture_ir = result.output
        return Validate()


@dataclass
class Inspect(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> End[str]:
        result = await inspector_agent.run(_ir_context(ctx.state), deps=TOOL_DEPS)
        ctx.state.inspection_result = result.output
        return End(result.output.summary)


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
