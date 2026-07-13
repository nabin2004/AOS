from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from ir.manim_ir import (
    Beat,
    CREATE_FAMILY,
    EntityType,
    Lecture,
    LectureIR,
    NarrationSegment,
    Operation,
    OperationType,
    Position,
    REMOVE_FAMILY,
    Scene,
    SceneObject,
    SemanticLabel,
    Storyboard,
)
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from pydantic_ai.usage import UsageLimits
from pydantic_graph import BaseNode, End, GraphBuilder, GraphRunContext, StepContext

from beat_planner_agent import beat_planner_agent
from classifier_agent import Classification, classifier_agent
from inspector_agent import InspectionResult, inspector_agent
from lecture_planner import lecture_planner_agent
from narration_planner_agent import narration_planner_agent
# from repair_agent import repair_agent  # Disabled — repair agent was a pipeline bottleneck
from scene_planner_agent import scene_planner_agent
from storyboard_planner import storyboard_planner_agent
from tools import ToolDeps
from tools.compile import persist_compiled_lecture, persist_lecture_ir
from tools.narrate import narrate_scenes
from tools.render import render_scenes_for_deps
from tools.validate import validate_lecture_ir_data
from validation_agent import ValidationResult, validation_agent

load_dotenv()

import logfire

logfire.configure()
logfire.instrument_pydantic_ai()


RUNS_DIR = Path(__file__).parent / "workspace" / "runs"
_DEBUG_LOG = Path(__file__).parent / "debug-1bf03e.log"


def _debug_log(
    location: str,
    message: str,
    data: dict[str, Any],
    hypothesis_id: str,
    run_id: str = "pre-fix",
) -> None:
    # #region agent log
    entry = {
        "sessionId": "1bf03e",
        "timestamp": int(time.time() * 1000),
        "location": location,
        "message": message,
        "data": data,
        "hypothesisId": hypothesis_id,
        "runId": run_id,
    }
    with _DEBUG_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, default=str) + "\n")
    # #endregion


def _scene_content_stats(scenes: list[Scene]) -> dict[str, Any]:
    empty_content = [
        obj.id
        for scene in scenes
        for obj in scene.scene_graph
        if obj.entity_type.value in ("math_tex", "text") and not obj.content.strip()
    ]
    empty_graph = [scene.id for scene in scenes if not scene.scene_graph]
    return {
        "scene_count": len(scenes),
        "object_count": sum(len(s.scene_graph) for s in scenes),
        "empty_graph_scenes": empty_graph,
        "empty_content_ids": empty_content,
        "empty_content_count": len(empty_content),
    }


def _storyboard_step_for_scene(storyboard: Storyboard | None, scene_id: str):
    if storyboard is None:
        return None
    for step in storyboard.steps:
        if step.scene_id == scene_id:
            return step
    return None


def _storyboard_goal_for_scene(storyboard: Storyboard | None, scene_id: str) -> str:
    step = _storyboard_step_for_scene(storyboard, scene_id)
    return step.pedagogical_goal if step else ""


def _pedagogical_context_for_scene(storyboard: Storyboard | None, scene_id: str) -> str:
    """Render the storyboard step's teaching intent as prompt context.

    Both the beat planner and the narration planner need *why* a scene
    exists, not just its geometry — this is the one place that context is
    assembled so both prompts stay in sync with the Storyboard schema.
    """
    step = _storyboard_step_for_scene(storyboard, scene_id)
    if step is None:
        return ""
    lines = [
        f"Pedagogical move: {step.pedagogical_move.value}",
        f"Pedagogical goal: {step.pedagogical_goal}",
    ]
    if step.viewer_question:
        lines.append(f"Viewer question posed to the audience: {step.viewer_question}")
    if step.narration_script:
        lines.append(f"Storyboard narration sketch: {step.narration_script}")
    return "\n".join(lines)


def _issues_are_missing_beats(issues: list[str]) -> bool:
    if not issues:
        return False
    beat_markers = ("no beats", "missing beats")
    return all(any(marker in issue.lower() for marker in beat_markers) for issue in issues)


_WRITE_ENTITY_TYPES = {
    EntityType.TEXT,
    EntityType.MATH_TEX,
    EntityType.TITLE,
    EntityType.CODE_BLOCK,
}


def _fallback_beats_for_scene(scene: Scene) -> list[Beat]:
    """Deterministic beats when flash-lite returns [] after retries."""
    beats: list[Beat] = []
    for obj in scene.scene_graph:
        op = (
            OperationType.WRITE
            if obj.entity_type in _WRITE_ENTITY_TYPES
            else OperationType.FADE_IN
        )
        beats.append(
            Beat(
                animation_segment=[
                    Operation(target=obj.id, op=op, run_time=1.0),
                ],
                hold_seconds=1.5,
            )
        )
    return beats


def _fallback_narration_for_beats(
    beats: list[Beat],
    scene: Scene,
    goal: str,
) -> list[Beat]:
    """Use on-screen content or the scene goal when narration agent fails."""
    content_by_id = {
        obj.id: obj.content.strip()
        for obj in scene.scene_graph
        if obj.content.strip()
    }
    narrated: list[Beat] = []
    for beat in beats:
        target = beat.animation_segment[0].target if beat.animation_segment else ""
        raw = content_by_id.get(target) or goal or "Watch what appears on screen."
        text = " ".join(raw.split()[:35])
        narrated.append(
            beat.model_copy(
                update={"narration": NarrationSegment(text=text)},
            )
        )
    return narrated


async def _plan_scenes_for_storyboard(
    storyboard: Storyboard,
) -> tuple[list[Scene], list[ModelMessage]]:
    """Plan scenes one storyboard step at a time — bulk all-scenes prompts corrupt output."""
    scenes: list[Scene] = []
    messages: list[ModelMessage] = []
    for i, step in enumerate(storyboard.steps):
        prompt = (
            f"Storyboard step {i + 1}/{len(storyboard.steps)}:\n"
            f"{step.model_dump_json()}\n\n"
            "Produce one Scene for this step only."
        )
        result = await scene_planner_agent.run(prompt, deps=step)
        scenes.append(result.output)
        messages.extend(result.all_messages())
    return scenes, messages


async def _plan_beats_for_scenes(
    scenes: list[Scene],
    storyboard: Storyboard | None,
    *,
    run_id: str = "pre-fix",
) -> tuple[list[Beat], list[ModelMessage]]:
    """Plan beats one scene at a time — bulk all-scenes prompts make flash-lite return []."""
    all_beats: list[Beat] = []
    all_messages: list[ModelMessage] = []
    for scene in scenes:
        context = _pedagogical_context_for_scene(storyboard, scene.id)
        prompt = (
            f"Scene JSON:\n{scene.model_dump_json()}\n\n"
            f"{context}\n\n"
            "Generate 4-7 beats for this scene only."
        )
        used_fallback = False
        try:
            result = await beat_planner_agent.run(prompt, deps=scene)
            scene_beats = result.output
            all_messages.extend(result.all_messages())
        except UnexpectedModelBehavior as exc:
            scene_beats = _fallback_beats_for_scene(scene)
            used_fallback = True
            # #region agent log
            _debug_log(
                "graph.py:_plan_beats_for_scenes",
                "beat planner fallback",
                {"scene_id": scene.id, "error": str(exc), "beat_count": len(scene_beats)},
                "G",
                run_id,
            )
            # #endregion
        # #region agent log
        _debug_log(
            "graph.py:_plan_beats_for_scenes",
            "per-scene beat planner result",
            {
                "scene_id": scene.id,
                "beat_count": len(scene_beats),
                "object_ids": [obj.id for obj in scene.scene_graph],
                "used_fallback": used_fallback,
            },
            "A",
            run_id,
        )
        # #endregion
        all_beats.extend(
            beat.model_copy(update={"scene_id": scene.id, "animation_segment": []})
            for beat in scene_beats
        )
    return all_beats, all_messages


async def _plan_narration_for_beats(
    beats: list[Beat],
    *,
    scenes: list[Scene] | None = None,
    storyboard: Storyboard | None = None,
    run_id: str = "pre-fix",
) -> tuple[list[Beat], list[ModelMessage]]:
    if not beats:
        return [], []
    scene_by_object: dict[str, Scene] = {}
    if scenes:
        for scene in scenes:
            for obj in scene.scene_graph:
                scene_by_object[obj.id] = scene

    def _scene_for_beat(beat: Beat) -> Scene | None:
        if beat.scene_id and scenes:
            for scene in scenes:
                if scene.id == beat.scene_id:
                    return scene
        for op in beat.animation_segment:
            scene = scene_by_object.get(op.target)
            if scene is not None:
                return scene
        return None

    # Group consecutive beats by owning scene (order-preserving) so each
    # narration call carries that scene's pedagogical_intent/viewer_question
    # instead of an arbitrary flat window of 8 that can straddle unrelated
    # scenes with no shared context.
    groups: list[tuple[Scene | None, list[Beat]]] = []
    for beat in beats:
        scene = _scene_for_beat(beat)
        if groups and groups[-1][0] is scene:
            groups[-1][1].append(beat)
        else:
            groups.append((scene, [beat]))

    chunk_size = 8
    narrated: list[Beat] = []
    all_messages: list[ModelMessage] = []
    chunk_start = 0
    for scene, group_beats in groups:
        context = _pedagogical_context_for_scene(storyboard, scene.id) if scene else ""
        for i in range(0, len(group_beats), chunk_size):
            chunk = group_beats[i : i + chunk_size]
            payload = json.dumps([b.model_dump(mode="json") for b in chunk])
            prompt = (f"{context}\n\n" if context else "") + f"Beats JSON:\n{payload}"
            used_fallback = False
            try:
                result = await narration_planner_agent.run(prompt)
                chunk_out = result.output
                all_messages.extend(result.all_messages())
                if not chunk_out or any(
                    b.narration is None or not b.narration.text.strip() for b in chunk_out
                ):
                    raise UnexpectedModelBehavior("narration agent returned empty narration")
            except UnexpectedModelBehavior as exc:
                used_fallback = True
                goal = _storyboard_goal_for_scene(storyboard, scene.id) if scene else ""
                chunk_out = (
                    _fallback_narration_for_beats(chunk, scene, goal)
                    if scene
                    else chunk
                )
                # #region agent log
                _debug_log(
                    "graph.py:_plan_narration_for_beats",
                    "narration fallback",
                    {"chunk_start": chunk_start, "error": str(exc), "beats": len(chunk_out)},
                    "G",
                    run_id,
                )
                # #endregion
            # #region agent log
            _debug_log(
                "graph.py:_plan_narration_for_beats",
                "narration chunk result",
                {
                    "chunk_start": chunk_start,
                    "scene_id": scene.id if scene else None,
                    "input_beats": len(chunk),
                    "output_beats": len(chunk_out),
                    "with_narration": sum(
                        1 for b in chunk_out if b.narration and b.narration.text.strip()
                    ),
                    "used_fallback": used_fallback,
                },
                "B",
                run_id,
            )
            # #endregion
            narrated.extend(chunk_out)
            chunk_start += len(chunk)
    return narrated, all_messages


async def _plan_narration_for_scenes(
    scenes: list[Scene],
    *,
    storyboard: Storyboard | None = None,
    run_id: str = "pre-fix",
) -> list[Scene]:
    """Narrate beats per scene in storyboard order (pedagogical beat path)."""
    if not scenes:
        return []
    updated: list[Scene] = []
    for scene in scenes:
        if not scene.beats:
            updated.append(scene)
            continue
        narrated_beats, _ = await _plan_narration_for_beats(
            scene.beats,
            scenes=[scene],
            storyboard=storyboard,
            run_id=run_id,
        )
        updated.append(scene.model_copy(update={"beats": narrated_beats}))
    return updated


def _run_tool_deps(state: AnimationState) -> ToolDeps:
    """Per-run workspace for compile/render — avoids cross-run overwrites."""
    if state.run_dir is None:
        raise RuntimeError("run_dir is not set; start node must run first")
    return ToolDeps(workspace_dir=state.run_dir)


def _pascal_case(identifier: str) -> str:
    parts = re.split(r"[^a-zA-Z0-9]+", identifier)
    name = "".join(p[:1].upper() + p[1:] for p in parts if p)
    if not name or not name[0].isalpha() or not name[0].isupper():
        name = "Scene" + (name or "Scene")
    return name


def _ensure_unique_class_names(scenes: list[Scene]) -> list[Scene]:
    """Assign unique PascalCase class_name values when the planner leaves defaults."""
    used: set[str] = set()
    result: list[Scene] = []
    for scene in scenes:
        base = scene.class_name
        if base == "GeneratedScene" or base in used:
            base = _pascal_case(scene.id)
        name = base
        suffix = 2
        while name in used:
            name = f"{base}{suffix}"
            suffix += 1
        used.add(name)
        result.append(scene.model_copy(update={"class_name": name}))
    return result


_TEXT_ENTITY_TYPES = frozenset({EntityType.TEXT, EntityType.MATH_TEX, EntityType.TITLE})
_ALLOWED_LABELS = {label.value for label in SemanticLabel}


def _infer_scene_object_label(obj: SceneObject) -> str:
    if obj.label in _ALLOWED_LABELS:
        return obj.label
    id_lower = obj.id.lower()
    if "reveal" in id_lower or "question" in id_lower:
        return SemanticLabel.REVEAL.value
    if "title" in id_lower:
        return SemanticLabel.ANNOTATION.value
    if obj.entity_type in (
        EntityType.AXES,
        EntityType.NUMBER_LINE,
        EntityType.NUMBER_PLANE,
        EntityType.COMPLEX_PLANE,
        EntityType.THREE_D_AXES,
    ):
        return SemanticLabel.SUPPORTING_CONTEXT.value
    if obj.entity_type in _TEXT_ENTITY_TYPES:
        return SemanticLabel.ANNOTATION.value
    if "contrast" in id_lower or "counter" in id_lower:
        return SemanticLabel.CONTRAST.value
    if "metaphor" in id_lower or "bowl" in id_lower or "fog" in id_lower:
        return SemanticLabel.METAPHOR.value
    return SemanticLabel.PRIMARY_FOCUS.value


def _ensure_visual_entity(scene: Scene) -> Scene:
    """Inject a minimal visual anchor when the planner returns a text-only scene."""
    if any(obj.entity_type not in _TEXT_ENTITY_TYPES for obj in scene.scene_graph):
        return scene
    anchor = SceneObject(
        id=f"{scene.id}_visual_anchor",
        entity_type=EntityType.DOT,
        label=SemanticLabel.METAPHOR.value,
        position=Position(x=0.0, y=0.0),
    )
    return scene.model_copy(update={"scene_graph": [anchor, *scene.scene_graph]})


def _enrich_scene_graph_labels(scenes: list[Scene]) -> list[Scene]:
    return [
        _ensure_visual_entity(
            scene.model_copy(
                update={
                    "scene_graph": [
                        obj.model_copy(update={"label": _infer_scene_object_label(obj)})
                        for obj in scene.scene_graph
                    ]
                }
            )
        )
        for scene in scenes
    ]


def _enrich_scenes_from_storyboard(
    scenes: list[Scene], storyboard: Storyboard | None
) -> list[Scene]:
    """Fill copy fields from the storyboard so the scene planner need not repeat them."""
    if storyboard is None:
        return scenes
    return [
        scene.model_copy(
            update={
                "pedagogical_intent": scene.pedagogical_intent
                or (_storyboard_goal_for_scene(storyboard, scene.id)),
            }
        )
        for scene in scenes
    ]


def _normalize_scene_graph(scenes: list[Scene]) -> list[Scene]:
    """Objects must start invisible; beats introduce them via create/write ops."""
    return [
        scene.model_copy(
            update={
                "scene_graph": [
                    obj.model_copy(update={"visible": False})
                    for obj in scene.scene_graph
                ]
            }
        )
        for scene in scenes
    ]


def _new_run_dir(user_request: str) -> Path:
    """Create a fresh per-invocation directory for step-by-step agent logs."""
    slug = re.sub(r"[^a-z0-9]+", "-", user_request.lower()).strip("-")[:40] or "run"
    run_dir = RUNS_DIR / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{slug}"
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"[logs] step-by-step agent output: {run_dir}")
    return run_dir


def _dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_dump(v) for v in value]
    return value


def _log_step(state: AnimationState, name: str, output: Any, messages: list[ModelMessage] | None = None) -> None:
    """Write a node's output (and, for agent runs, its full message/tool-call trace) to disk."""
    if state.run_dir is None:
        return
    state.step_index += 1
    stem = state.run_dir / f"{state.step_index:02d}_{name}"
    stem.with_suffix(".output.json").write_text(
        json.dumps(_dump(output), indent=2, default=str), encoding="utf-8"
    )
    if messages:
        stem.with_suffix(".messages.json").write_bytes(
            ModelMessagesTypeAdapter.dump_json(messages, indent=2)
        )


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
    validation_messages: list[ModelMessage] = field(default_factory=list)
    repair_messages: list[ModelMessage] = field(default_factory=list)
    run_dir: Path | None = None
    step_index: int = 0


def _assign_beats_to_scenes(scenes: list[Scene], beats: list[Beat]) -> list[Scene]:
    if beats and all(beat.scene_id for beat in beats):
        buckets: dict[str, list[Beat]] = {scene.id: [] for scene in scenes}
        for beat in beats:
            if beat.scene_id in buckets:
                buckets[beat.scene_id].append(beat)
        return [scene.model_copy(update={"beats": buckets[scene.id]}) for scene in scenes]

    owners: dict[str, str] = {}
    for scene in scenes:
        for obj in scene.scene_graph:
            owners[obj.id] = scene.id

    buckets: dict[str, list[Beat]] = {scene.id: [] for scene in scenes}
    unassigned: list[Beat] = []
    for beat in beats:
        target_counts: dict[str, int] = {}
        for op in beat.animation_segment:
            if op.target == "__camera__":
                continue
            scene_id = owners.get(op.target)
            if scene_id is None:
                continue
            target_counts[scene_id] = target_counts.get(scene_id, 0) + 1
        if len(target_counts) == 1:
            buckets[next(iter(target_counts))].append(beat)
        elif target_counts:
            buckets[max(target_counts, key=target_counts.get)].append(beat)
        else:
            unassigned.append(beat)

    for index, beat in enumerate(unassigned):
        buckets[scenes[index % len(scenes)].id].append(beat)

    return [scene.model_copy(update={"beats": buckets[scene.id]}) for scene in scenes]


def _sanitize_scene_beats(scene: Scene) -> Scene:
    """Drop redundant CREATE ops so LectureIR liveness validation passes.

    Beat planners often emit create + fade_in on the same target; only the first
    introduction op is needed because CREATE_FAMILY ops mark an object live.
    """
    live: set[str] = {obj.id for obj in scene.scene_graph if obj.visible}
    sanitized_beats: list[Beat] = []

    for beat in scene.beats:
        kept_ops: list[Operation] = []
        for op in beat.animation_segment:
            if op.op in CREATE_FAMILY:
                if op.target in live:
                    continue
                live.add(op.target)
                kept_ops.append(op)
            elif op.op in REMOVE_FAMILY:
                if op.target not in live:
                    continue
                live.discard(op.target)
                kept_ops.append(op)
            elif op.target in live:
                kept_ops.append(op)

        if kept_ops:
            sanitized_beats.append(
                beat.model_copy(update={"animation_segment": kept_ops})
            )

    return scene.model_copy(update={"beats": sanitized_beats})


def _heal_scene_graph(scene: Scene) -> Scene:
    """Add stub scene-graph objects for CREATE targets missing from the graph."""
    known = {obj.id for obj in scene.scene_graph}
    stubs: list[SceneObject] = []
    for beat in scene.beats:
        for op in beat.animation_segment:
            if op.op in CREATE_FAMILY and op.target not in known:
                known.add(op.target)
                stubs.append(
                    SceneObject(
                        id=op.target,
                        entity_type=EntityType.TEXT,
                        visible=False,
                        content=op.target,
                    )
                )
    if not stubs:
        return scene
    return scene.model_copy(update={"scene_graph": [*scene.scene_graph, *stubs]})


def _sync_scenes_to_storyboard(
    scenes: list[Scene], storyboard: Storyboard | None
) -> list[Scene]:
    """Add stub scenes when the planner omits storyboard-referenced scene ids."""
    if storyboard is None:
        return scenes
    by_id = {scene.id: scene for scene in scenes}
    stubs: list[Scene] = []
    for step in storyboard.steps:
        if step.scene_id in by_id:
            continue
        stubs.append(
            Scene(
                id=step.scene_id,
                class_name=_pascal_case(step.scene_id),
                title=(step.pedagogical_goal[:80] if step.pedagogical_goal else step.scene_id),
                pedagogical_intent=step.pedagogical_goal,
                scene_graph=[
                    SceneObject(
                        id="placeholder",
                        entity_type=EntityType.TEXT,
                        visible=False,
                        content=step.visual_description or step.pedagogical_goal or step.scene_id,
                        label="primary_focus",
                    )
                ],
            )
        )
    return [*scenes, *stubs] if stubs else scenes


def _prepare_scenes(state: AnimationState) -> list[Scene] | None:
    if not state.scenes:
        return None
    beats = state.narration_beats or state.beats or []
    scenes = _assign_beats_to_scenes(state.scenes, beats) if beats else list(state.scenes)
    scenes = _sync_scenes_to_storyboard(scenes, state.storyboard)
    return [_sanitize_scene_beats(_heal_scene_graph(scene)) for scene in scenes]


def _build_lecture_ir(state: AnimationState) -> LectureIR | None:
    if state.lecture_plan is None or state.storyboard is None:
        return None
    scenes = _prepare_scenes(state)
    if not scenes:
        return None
    return LectureIR(
        lecture=state.lecture_plan,
        storyboard=state.storyboard,
        scenes=scenes,
    )


def _draft_lecture_ir(state: AnimationState) -> LectureIR | None:
    if state.lecture_ir is not None:
        return state.lecture_ir
    draft = _build_lecture_ir(state)
    if draft is None:
        return None
    state.lecture_ir = draft
    return draft


def _ir_context(state: AnimationState) -> str:
    """JSON context for validation/repair."""
    draft = _build_lecture_ir(state)
    if draft is None:
        return "{}"
    return draft.model_dump_json()


@dataclass
class Classify(BaseNode[AnimationState]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> PlanLecture:
        result = await classifier_agent.run(ctx.state.user_request)
        ctx.state.classification = result.output
        _log_step(ctx.state, "classify", result.output, result.all_messages())
        return PlanLecture()


@dataclass
class PlanLecture(BaseNode[AnimationState]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> MakeStoryboard:
        result = await lecture_planner_agent.run(
            f"User request: {ctx.state.user_request}\n"
            f"Classification: {ctx.state.classification}"
        )
        ctx.state.lecture_plan = result.output
        _log_step(ctx.state, "plan_lecture", result.output, result.all_messages())
        return MakeStoryboard()


@dataclass
class MakeStoryboard(BaseNode[AnimationState]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> CreateScenes:
        result = await storyboard_planner_agent.run(
            f"User request: {ctx.state.user_request}\n"
            f"Lecture plan: {ctx.state.lecture_plan}"
        )
        ctx.state.storyboard = result.output
        _log_step(ctx.state, "make_storyboard", result.output, result.all_messages())
        return CreateScenes()


@dataclass
class CreateScenes(BaseNode[AnimationState]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> AddBeats:
        scenes, scene_messages = await _plan_scenes_for_storyboard(ctx.state.storyboard)
        ctx.state.scenes = _normalize_scene_graph(
            _enrich_scene_graph_labels(
                _ensure_unique_class_names(
                    _enrich_scenes_from_storyboard(scenes, ctx.state.storyboard)
                )
            )
        )
        _log_step(ctx.state, "create_scenes", ctx.state.scenes, scene_messages)
        return AddBeats()


@dataclass
class AddBeats(BaseNode[AnimationState]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> AddNarration:
        scenes = ctx.state.scenes or []
        # #region agent log
        _debug_log(
            "graph.py:AddBeats",
            "beat planning input",
            _scene_content_stats(scenes),
            "C",
        )
        # #endregion
        ctx.state.beats, beat_messages = await _plan_beats_for_scenes(
            scenes, ctx.state.storyboard
        )
        # #region agent log
        _debug_log(
            "graph.py:AddBeats",
            "beat planning output",
            {"total_beats": len(ctx.state.beats or [])},
            "A",
        )
        # #endregion
        _log_step(ctx.state, "add_beats", ctx.state.beats, beat_messages)
        return AddNarration()


@dataclass
class AddNarration(BaseNode[AnimationState]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> Validate:
        beats = ctx.state.beats or []
        # #region agent log
        _debug_log(
            "graph.py:AddNarration",
            "narration planning input",
            {"input_beats": len(beats)},
            "B",
        )
        # #endregion
        ctx.state.narration_beats, narration_messages = await _plan_narration_for_beats(
            beats,
            scenes=ctx.state.scenes,
            storyboard=ctx.state.storyboard,
        )
        # #region agent log
        _debug_log(
            "graph.py:AddNarration",
            "narration planning output",
            {
                "output_beats": len(ctx.state.narration_beats or []),
                "with_narration": sum(
                    1
                    for b in (ctx.state.narration_beats or [])
                    if b.narration and b.narration.text.strip()
                ),
            },
            "B",
        )
        # #endregion
        _log_step(ctx.state, "add_narration", ctx.state.narration_beats, narration_messages)
        return Validate()


@dataclass
class Validate(BaseNode[AnimationState]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> Narrate:
        ctx.state.validation_attempts += 1
        attempt = ctx.state.validation_attempts
        ir_json = _ir_context(ctx.state)
        prepared_scenes = _prepare_scenes(ctx.state)
        scene_beat_counts = (
            {s.id: len(s.beats) for s in prepared_scenes}
            if prepared_scenes is not None
            else {}
        )
        # #region agent log
        _debug_log(
            "graph.py:Validate",
            "validation input",
            {
                "attempt": attempt,
                "state_beats": len(ctx.state.beats or []),
                "state_narration_beats": len(ctx.state.narration_beats or []),
                "has_lecture_ir": ctx.state.lecture_ir is not None,
                "scene_beat_counts": scene_beat_counts,
            },
            "D",
        )
        # #endregion
        schema = validate_lecture_ir_data(ir_json)

        if not schema["passed"]:
            ctx.state.validation_result = ValidationResult(
                passed=False,
                issues=[str(issue) for issue in schema["issues"]],
            )
            _log_step(ctx.state, f"validate_attempt{attempt}_schema", ctx.state.validation_result)
            return Narrate()

        max_requests = ctx.state.max_validation_attempts
        result = await validation_agent.run(
            (
                "Schema validation already passed. Check semantic invariants only "
                "(reference integrity, cognitive load, storyboard linkage) against "
                "the JSON below.\n\n"
                f"{ir_json}"
            ),
            message_history=ctx.state.validation_messages,
            usage_limits=UsageLimits(request_limit=max_requests),
        )
        ctx.state.validation_messages = result.all_messages()
        ctx.state.validation_result = result.output
        _log_step(ctx.state, f"validate_attempt{attempt}_semantic", result.output, result.all_messages())

        return Narrate()


# Disabled — repair agent was a pipeline bottleneck
# @dataclass
# class Repair(BaseNode[AnimationState]):
#     async def run(self, ctx: GraphRunContext[AnimationState]) -> Validate:
#         issues = ctx.state.validation_result.issues if ctx.state.validation_result else []
#         if _issues_are_missing_beats(issues) and ctx.state.scenes:
#             # #region agent log
#             _debug_log(
#                 "graph.py:Repair",
#                 "re-planning beats instead of full IR repair",
#                 {"issue_count": len(issues), "scene_count": len(ctx.state.scenes)},
#                 "E",
#             )
#             # #endregion
#             ctx.state.beats, _ = await _plan_beats_for_scenes(
#                 ctx.state.scenes,
#                 ctx.state.storyboard,
#                 run_id="repair-replan",
#             )
#             ctx.state.narration_beats, _ = await _plan_narration_for_beats(
#                 ctx.state.beats or [],
#                 scenes=ctx.state.scenes,
#                 storyboard=ctx.state.storyboard,
#                 run_id="repair-replan",
#             )
#             ctx.state.lecture_ir = None
#             _log_step(
#                 ctx.state,
#                 f"repair_attempt{ctx.state.validation_attempts}_replan_beats",
#                 {
#                     "beats": len(ctx.state.beats or []),
#                     "narration_beats": len(ctx.state.narration_beats or []),
#                 },
#             )
#             return Validate()
#
#         result = await repair_agent.run(
#             f"Issues: {issues}\n\n{_ir_context(ctx.state)}",
#             deps=_run_tool_deps(ctx.state),
#             message_history=ctx.state.repair_messages,
#         )
#         ctx.state.repair_messages = result.all_messages()
#         repaired = result.output
#         if repaired.scenes:
#             repaired = repaired.model_copy(
#                 update={"scenes": _ensure_unique_class_names(repaired.scenes)}
#             )
#         # Repair agent often returns scenes with empty beats; preserve planned beats.
#         beats = ctx.state.narration_beats or ctx.state.beats or []
#         if beats and any(not s.beats for s in repaired.scenes):
#             repaired = repaired.model_copy(
#                 update={
#                     "scenes": _assign_beats_to_scenes(repaired.scenes, beats),
#                 }
#             )
#         ctx.state.lecture_ir = repaired
#         repaired_beat_total = sum(len(s.beats) for s in repaired.scenes)
#         # #region agent log
#         _debug_log(
#             "graph.py:Repair",
#             "repair agent output",
#             {
#                 "repaired_scene_count": len(repaired.scenes),
#                 "repaired_beat_total": repaired_beat_total,
#             },
#             "E",
#         )
#         # #endregion
#         _log_step(
#             ctx.state,
#             f"repair_attempt{ctx.state.validation_attempts}",
#             result.output,
#             result.all_messages(),
#         )
#         return Validate()


@dataclass
class Narrate(BaseNode[AnimationState]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> Inspect:
        draft = _draft_lecture_ir(ctx.state)
        if draft is None:
            _log_step(
                ctx.state,
                "narrate",
                {"skipped": "missing lecture plan, storyboard, or scenes"},
            )
            return Inspect()

        deps = _run_tool_deps(ctx.state)
        audio_dir = deps.workspace_dir / "audio"
        try:
            narration_paths = narrate_scenes(draft.scenes, audio_dir)
        except Exception as exc:
            narration_paths = {"error": str(exc)}
            print(f"[narrate] skipped (TTS unavailable): {exc}")
        _log_step(ctx.state, "narrate", narration_paths)
        return Inspect()


def _summarize_render_results(results: dict[str, dict]) -> str:
    summary: dict[str, dict[str, str | bool]] = {}
    for scene_class, outcome in results.items():
        log = outcome.get("log") or ""
        summary[scene_class] = {
            "success": outcome.get("success", False),
            "output_path": outcome.get("output_path", ""),
            "log_tail": log[-500:] if log else "",
        }
    return json.dumps(summary, indent=2)


@dataclass
class Inspect(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> End[str]:
        draft = _draft_lecture_ir(ctx.state)
        if draft is None:
            summary = "Could not assemble a LectureIR document (missing plan, storyboard, or scenes)."
            ctx.state.inspection_result = InspectionResult(
                passed=False,
                summary=summary,
                issues=[summary],
            )
            _log_step(ctx.state, "inspect", ctx.state.inspection_result)
            return End(summary)

        deps = _run_tool_deps(ctx.state)
        lecture_path = persist_compiled_lecture(deps.workspace_dir, draft)
        persist_lecture_ir(deps.workspace_dir, draft)
        print(f"[compile] wrote {lecture_path}")

        scene_classes = [s.class_name for s in draft.scenes]
        render_results = render_scenes_for_deps(
            deps,
            scene_file="lecture.py",
            scene_classes=scene_classes,
            render_config=draft.render,
        )
        render_results_path = deps.workspace_dir / "render_results.json"
        render_results_path.write_text(
            json.dumps(render_results, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"[render] results: {render_results_path}")

        inspector_prompt = (
            f"{draft.model_dump_json()}\n\n"
            "Compile and Docker render already completed deterministically.\n"
            f"lecture.py: {lecture_path}\n"
            f"Scene classes: {scene_classes}\n"
            f"Render results:\n{_summarize_render_results(render_results)}\n\n"
            "Review the IR and render outcomes above for pedagogical quality. "
            "Do not compile or render again."
        )
        result = await inspector_agent.run(inspector_prompt)
        ctx.state.inspection_result = result.output
        _log_step(ctx.state, "inspect", result.output, result.all_messages())
        return End(result.output.summary)


g = GraphBuilder(state_type=AnimationState, output_type=str)


@g.step
async def start(ctx: StepContext[AnimationState, None, None]) -> Classify:
    ctx.state.run_dir = _new_run_dir(ctx.state.user_request)
    return Classify()


g.add(
    g.node(Classify),
    g.node(PlanLecture),
    g.node(MakeStoryboard),
    g.node(CreateScenes),
    g.node(AddBeats),
    g.node(AddNarration),
    g.node(Validate),
    # g.node(Repair),  # Disabled — repair agent was a pipeline bottleneck
    g.node(Narrate),
    g.node(Inspect),
    g.edge_from(g.start_node).to(start),
)

animation_graph = g.build()

if __name__ == "__main__":
    print(animation_graph.render())
