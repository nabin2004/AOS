from dataclasses import dataclass
from pathlib import Path
import re

from pydantic_graph import BaseNode, End, GraphBuilder, GraphRunContext

from beat_planner_agent import beat_planner_agent
from classifier_agent import classifier_agent
from inspector_agent import InspectionResult, inspector_agent
from ir.manim_ir import (
    Beat,
    CREATE_FAMILY,
    Classification,
    EntityType,
    Lecture,
    LectureIR,
    Operation,
    REMOVE_FAMILY,
    Scene,
    SceneObject,
    Storyboard,
)
from lecture_planner import lecture_planner_agent
from repair_agent import repair_agent
from graph import _plan_narration_for_scenes, _plan_scenes_for_storyboard
from storyboard_planner import storyboard_planner_agent
from tools.deps import ToolDeps
from tools.validate import validate_lecture_ir_data
from validation_agent import ValidationResult, validation_agent


@dataclass
class AnimationState:
    query: str
    classification: Classification | None = None
    plan: Lecture | None = None
    storyboard: Storyboard | None = None
    scenes: list[Scene] | None = None
    beats: list[Beat] | None = None
    validation_result: ValidationResult | None = None
    lecture_ir: LectureIR | None = None
    inspection_result: InspectionResult | None = None


@dataclass
class ClassifyNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "PlanLectureNode":
        result = await classifier_agent.run(ctx.state.query)
        ctx.state.classification = result.output
        return PlanLectureNode()


@dataclass
class PlanLectureNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "StoryboardNode":
        result = await lecture_planner_agent.run(
            f"Topic: {ctx.state.classification.topic}\n"
            f"Subject: {ctx.state.classification.subject}"
        )
        ctx.state.plan = result.output
        return StoryboardNode()


@dataclass
class StoryboardNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "CreateSceneNode":
        result = await storyboard_planner_agent.run(
            f"User request: {ctx.state.query}\n"
            f"Lecture plan: {ctx.state.plan.model_dump_json()}"
        )
        ctx.state.storyboard = result.output
        return CreateSceneNode()


@dataclass
class CreateSceneNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "BeatsAddNode":
        scenes, _ = await _plan_scenes_for_storyboard(ctx.state.storyboard)
        ctx.state.scenes = scenes
        return BeatsAddNode()


@dataclass
class BeatsAddNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "NarratingNode":
        updated_scenes: list[Scene] = []
        for scene in ctx.state.scenes or []:
            result = await beat_planner_agent.run(
                f"Scene JSON:\n{scene.model_dump_json()}\n\n"
                "Generate 4-7 pedagogical beats for this scene only.",
                deps=scene,
            )
            beats = [
                beat.model_copy(
                    update={"scene_id": scene.id, "animation_segment": []}
                )
                for beat in result.output
            ]
            updated_scenes.append(scene.model_copy(update={"beats": beats}))
        ctx.state.scenes = updated_scenes
        ctx.state.beats = [beat for scene in updated_scenes for beat in scene.beats]
        return NarratingNode()


@dataclass
class NarratingNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "ValidatingNode":
        if ctx.state.scenes:
            ctx.state.scenes = await _plan_narration_for_scenes(
                ctx.state.scenes,
                storyboard=ctx.state.storyboard,
            )
            ctx.state.beats = [
                beat for scene in ctx.state.scenes for beat in scene.beats
            ]
        return ValidatingNode()


@dataclass
class ValidatingNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "RepairNode":
        ir_json = _ir_context(ctx.state)
        schema = validate_lecture_ir_data(ir_json)

        if not schema["passed"]:
            ctx.state.validation_result = ValidationResult(
                passed=False,
                issues=[str(issue) for issue in schema["issues"]],
            )
        else:
            result = await validation_agent.run(
                "Schema validation already passed. Check semantic invariants only "
                "(reference integrity, cognitive load, storyboard linkage) against "
                "the JSON below.\n\n"
                f"{ir_json}"
            )
            ctx.state.validation_result = result.output

        ctx.state.lecture_ir = _draft_lecture_ir(ctx.state)
        return RepairNode()


@dataclass
class RepairNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "InspectingNode":
        if (
            ctx.state.validation_result
            and not ctx.state.validation_result.passed
            and ctx.state.lecture_ir is not None
        ):
            deps = ToolDeps(workspace_dir=Path("runs") / "final_graph")
            result = await repair_agent.run(
                f"Issues: {ctx.state.validation_result.issues}\n\n"
                f"IR:\n{ctx.state.lecture_ir.model_dump_json()}",
                deps=deps,
            )
            ctx.state.lecture_ir = result.output
        return InspectingNode()


@dataclass
class InspectingNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "PrintResultNode":
        ir = ctx.state.lecture_ir or _draft_lecture_ir(ctx.state)
        if ir is None:
            ctx.state.inspection_result = InspectionResult(
                passed=False,
                summary="Could not assemble a LectureIR document.",
                issues=["Missing plan, storyboard, or scenes."],
            )
            return PrintResultNode()

        result = await inspector_agent.run(
            f"{ir.model_dump_json()}\n\n"
            "Simplified pipeline: compile/render skipped. Review IR quality only."
        )
        ctx.state.inspection_result = result.output
        return PrintResultNode()


@dataclass
class PrintResultNode(BaseNode[AnimationState, None, str]):
    async def run(
        self,
        ctx: GraphRunContext[AnimationState],
    ) -> End[str]:
        summary = (
            ctx.state.inspection_result.summary
            if ctx.state.inspection_result
            else "No result"
        )
        print(summary)
        return End(summary)


g = GraphBuilder(state_type=AnimationState, output_type=str, name="AnimationGraph")


@g.step
async def start(state: AnimationState) -> ClassifyNode:
    return ClassifyNode()


g.add(
    g.node(ClassifyNode),
    g.node(PlanLectureNode),
    g.node(StoryboardNode),
    g.node(CreateSceneNode),
    g.node(BeatsAddNode),
    g.node(NarratingNode),
    g.node(ValidatingNode),
    g.node(RepairNode),
    g.node(InspectingNode),
    g.node(PrintResultNode),
    g.edge_from(g.start_node).to(start),
)

animation_graph = g.build()


if __name__ == "__main__":
    print(animation_graph.render())
