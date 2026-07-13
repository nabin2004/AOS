from dataclasses import dataclass, fields
from pathlib import Path
import json
# from dotenv import load_dotenv

# load_dotenv()

from pydantic_graph import BaseNode, End, GraphBuilder, GraphRunContext
from pydantic_ai import Agent

from beat_planner_agent import beat_planner_agent
from classifier_agent import classifier_agent
from graph import (
    _assign_beats_to_scenes,
    _plan_narration_for_scenes,
    _plan_scenes_for_storyboard,
)
from ir.manim_ir import (
    Beat,
    Classification,
    Lecture,
    LectureIR,
    Scene,
    Storyboard,
    Subject,
)
from lecture_planner import lecture_planner_agent
from storyboard_planner import storyboard_planner_agent
from tools.deps import ToolDeps
from tools.pipeline import LecturePipelineResult, run_full_pipeline_async
from dotenv import load_dotenv

load_dotenv()

WORKSPACE_DIR = Path("runs") / "final_final_graph"


@dataclass
class AnimationState:
    query: str
    classification: Classification | None = None
    plan: Lecture | None = None
    storyboard: Storyboard | None = None
    scenes: list[Scene] | None = None
    beats: list[Beat] | None = None
    lecture_ir: LectureIR | None = None
    pipeline_result: LecturePipelineResult | None = None


def _serialize_state(state: AnimationState) -> dict:
    """Serialize graph state to JSON-safe dict (Pydantic models use mode=json)."""
    result: dict = {}
    for field in fields(state):
        value = getattr(state, field.name)
        if value is None:
            result[field.name] = None
        elif hasattr(value, "model_dump"):
            result[field.name] = value.model_dump(mode="json")
        elif isinstance(value, list) and value and hasattr(value[0], "model_dump"):
            result[field.name] = [item.model_dump(mode="json") for item in value]
        else:
            result[field.name] = value
    return result


@dataclass
class ClassifyNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "Descision":
        result = await classifier_agent.run(ctx.state.query)
        print(f"Classification result: {result.output.subject} - {result.output.topic}")
        ctx.state.classification = result.output
        return Descision()


@dataclass
class Descision(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "PlanLectureNode":
        print(
            f"Classification result: {ctx.state.classification.subject} - "
            f"{ctx.state.classification.topic}"
        )
        if ctx.state.classification is None:
            print("Classification failed!")
            return PrintResultNode()
        if ctx.state.classification.subject == Subject.UNKNOWN:
            print("Not supported yet!")
            return PrintResultNode()
        return PlanLectureNode()


@dataclass
class PlanLectureNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "StoryboardNode":
        print("Lecture planner started...")
        result = await lecture_planner_agent.run(
            f"Topic: {ctx.state.classification.topic}\n"
            f"Subject: {ctx.state.classification.subject}"
        )
        ctx.state.plan = result.output
        return StoryboardNode()


@dataclass
class StoryboardNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "CreateSceneNode":
        print("Storyboard creator started...")
        result = await storyboard_planner_agent.run(
            f"User request: {ctx.state.query}\n"
            f"Lecture plan: {ctx.state.plan.model_dump_json()}"
        )
        ctx.state.storyboard = result.output
        return CreateSceneNode()


@dataclass
class CreateSceneNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "BeatsAddNode":
        print("Scene creator started...")
        scenes, _ = await _plan_scenes_for_storyboard(ctx.state.storyboard)
        ctx.state.scenes = scenes
        try:
            data = {
                "ctx_state_scenes": [
                    json.loads(s.model_dump_json()) for s in (ctx.state.scenes or [])
                ],
            }
            Path(WORKSPACE_DIR / "scene_results.json").write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Failed to save scene results: {e}")
        return BeatsAddNode()


@dataclass
class BeatsAddNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "NarratingNode":
        print("Beat planner started...")
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
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "AssembleIRNode":
        print("Narration planner started...", len(ctx.state.scenes or []))
        if ctx.state.scenes:
            ctx.state.scenes = await _plan_narration_for_scenes(
                ctx.state.scenes,
                storyboard=ctx.state.storyboard,
            )
            ctx.state.beats = [
                beat for scene in ctx.state.scenes for beat in scene.beats
            ]
        return AssembleIRNode()


@dataclass
class AssembleIRNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "ProduceLectureNode":
        print("Assembling LectureIR...")
        scenes = ctx.state.scenes or []
        if ctx.state.beats and not all(scene.beats for scene in scenes):
            scenes = _assign_beats_to_scenes(scenes, ctx.state.beats)
        ctx.state.scenes = scenes
        ctx.state.lecture_ir = LectureIR(
            lecture=ctx.state.plan,
            storyboard=ctx.state.storyboard,
            scenes=scenes,
        )
        return ProduceLectureNode()


@dataclass
class ProduceLectureNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "PrintResultNode":
        print("Write Manim → narrate → render → mux → final video...")
        if ctx.state.lecture_ir is None:
            return PrintResultNode()
        deps = ToolDeps(workspace_dir=WORKSPACE_DIR)
        ctx.state.pipeline_result = await run_full_pipeline_async(ctx.state.lecture_ir, deps)
        if Path(ctx.state.pipeline_result.lecture_ir_path).exists():
            ctx.state.lecture_ir = LectureIR.model_validate_json(
                Path(ctx.state.pipeline_result.lecture_ir_path).read_text(encoding="utf-8")
            )
        return PrintResultNode()


@dataclass
class PrintResultNode(BaseNode[AnimationState, None, str]):
    async def run(
        self,
        ctx: GraphRunContext[AnimationState],
    ) -> End[str]:
        try:
            state_json = _serialize_state(ctx.state)
            WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
            Path(WORKSPACE_DIR / "ctx_state.json").write_text(json.dumps(state_json, indent=2))
        except Exception as e:
            print(f"Failed to save ctx.state: {e}")

        if ctx.state.pipeline_result:
            pr = ctx.state.pipeline_result
            parts = [f"LectureIR at {pr.lecture_ir_path}"]
            if pr.lecture_py_path:
                parts.append(f"Manim at {pr.lecture_py_path}")
            parts.append(f"{len(pr.narration)} narration clip(s)")
            parts.append(f"{len(pr.scene_videos)} muxed scene(s)")
            if pr.final_video_path:
                parts.append(f"final video at {pr.final_video_path}")
            elif pr.skipped_scenes:
                parts.append(f"skipped: {', '.join(pr.skipped_scenes)}")
            summary = ", ".join(parts)
        elif ctx.state.lecture_ir:
            summary = (
                f"LectureIR assembled with {len(ctx.state.lecture_ir.scenes)} scene(s) "
                "(compile skipped)"
            )
        else:
            summary = "Pipeline complete (no IR output)"

        print(summary)
        return End(summary)


g = GraphBuilder(state_type=AnimationState, output_type=str, name="AnimationGraph")


@g.step
async def start(state: AnimationState) -> ClassifyNode:
    return ClassifyNode()


g.add(
    g.node(ClassifyNode),
    g.node(Descision),
    g.node(PlanLectureNode),
    # g.node(StoryboardNode),
    # g.node(CreateSceneNode),
    # g.node(BeatsAddNode),
    g.node(CoderAgentNode),
    g.node(NarratingNode),
    g.node(AssembleIRNode),
    g.node(ProduceLectureNode),
    g.node(PrintResultNode),
    g.edge_from(g.start_node).to(start),
)

animation_graph = g.build()

if __name__ == "__main__":
    print(animation_graph.render())
