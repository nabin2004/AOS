from dataclasses import dataclass
import os
from pathlib import Path
import re
import sys
from typing import Any
from dotenv import load_dotenv

load_dotenv()

from pydantic_graph import BaseNode, End, EndMarker, GraphBuilder, GraphRunContext
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import RunUsage, UsageLimits

from observability import configure_logfire, sft_batch_enabled
from llm_config import is_ollama, model_for, model_for_agent, settings_for, model_for_agent, settings_for
from openai_compatible import format_custom_endpoint_error
from llm_retry import execute_with_llm_retry
from coder_prompt import (
    build_coder_user_prompt,
    plan_to_payload,
)

configure_logfire()

from coder_agent import SFT_BATCH_ADDENDUM, coder_agent
from coder_run import (
    CoderRunResult,
    arrange_coder_artifacts,
    new_coder_run_dir,
)
from tools.coder_workspace import load_manifest
from tools.manim_source import extract_codemode_dump
from classifier_agent import classifier_agent
from lecture_planner import lecture_planner_agent, Lecture
from teaching_script import (
    TeachingBeat,
    TeachingScript,
    teaching_script_agent,
    teaching_script_to_payload,
    teaching_script_user_prompt,
)
from ir.manim_ir import Subject, Classification
from dbos_setup import dbos_enabled, ensure_dbos_launched


def _heuristic_classification(user_query: str) -> Classification | None:
    """In-domain fallback when the classifier model cannot emit structured output."""
    q = user_query.lower()
    math_hints = (
        "bodmas",
        "pemdas",
        "bidmas",
        "order of operations",
        "algebra",
        "calculus",
        "geometry",
        "trigonometry",
        "fraction",
        "equation",
        "matrix",
        "derivative",
        "integral",
        "probability",
        "statistics",
        "pythagoras",
        "quadratic",
        "arithmetic",
        "math",
        "euler",
        "e^{i",
        "complex number",
        "complex numbers",
        "cis",
        "unit circle",
        "formula",
        "theorem",
        "identity",
        "fourier",
        "de moivre",
        "lorenz",
        "attractor",
        "chaos",
        "differential",
        "dynamical",
        "physics",
        "gravity",
        "system",
    )
    cs_hints = (
        "algorithm",
        "data structure",
        "binary tree",
        "linked list",
        "complexity",
        "sorting",
        "recursion",
        "programming",
    )
    ai_hints = (
        "neural network",
        "machine learning",
        "gradient descent",
        "backpropagation",
        "transformer",
        "llm",
    )
    extracted_topic = re.sub(
        r"^(teach\s+me\s+about|explain|animate|visualize|what\s+is|show\s+me|create\s+a\s+video\s+about|lecture\s+on)\s+",
        "",
        user_query.strip(),
        flags=re.IGNORECASE,
    ).strip() or user_query.strip()

    if any(h in q for h in cs_hints):
        return Classification(subject=Subject.CS, topic=extracted_topic.title() or "Computer Science Topic")
    if any(h in q for h in ai_hints):
        return Classification(subject=Subject.AI, topic=extracted_topic.title() or "AI Topic")

    topic = extracted_topic.title() if extracted_topic else "Math Topic"
    if "bodmas" in q:
        topic = "BODMAS"
    elif "pemdas" in q:
        topic = "PEMDAS"
    elif "euler" in q:
        topic = "Eulers Formula"
    elif "lorenz" in q:
        topic = "Lorenz Attractor"

    return Classification(subject=Subject.MATH, topic=topic)



def _heuristic_lecture_plan(topic: str, subject: Subject | str) -> Lecture:
    """Generate a clean, valid default Lecture plan if the planner LLM fails."""
    subj = (
        Subject(subject)
        if isinstance(subject, str) and subject in Subject._value2member_map_
        else (subject if isinstance(subject, Subject) else Subject.MATH)
    )
    clean_topic = re.sub(r"[^A-Za-z0-9]", "", topic.title()) or "Main"
    scene_name = f"{clean_topic}Scene"
    return Lecture(
        topic=topic,
        subject=subj,
        greeting=f"In this lesson, you will explore {topic}.",
        needed_formulas=[],
        class_names=[scene_name],
        does_it_needs_3d=any(k in topic.lower() for k in ("3d", "lorenz", "space", "sphere")),
        assumptions=[],
        list_of_external_library_needed=[],
        animation_needed=["Write", "FadeIn", "Create", "Transform"],
        animation_updaters_needed=[],
        camera_needed=[],
        Mobjects_needed=["Title", "Text", "MathTex", "VGroup"],
        objectives=[f"Understand the core intuition behind {topic}"],
        opener=f"You will see the fundamental principles of {topic} visualized step by step.",
        learning_outcomes=[f"Explain the key intuition behind {topic}"],
    )


def _heuristic_teaching_script(
    topic: str, subject: Subject | str, plan: Any = None
) -> TeachingScript:
    """Generate a clean, structured default TeachingScript if the teaching script agent fails."""
    clean_topic = re.sub(r"[^A-Za-z0-9 ]", "", topic).strip() or "Mathematical Principles"
    clean_title = topic.replace("'", "").title()
    scene_name = f"{re.sub(r'[^A-Za-z0-9]', '', clean_title) or 'Main'}Scene"

    topic_lower = topic.lower()
    if "euler" in topic_lower:
        beats = [
            TeachingBeat(
                id="intro",
                takeaway="Euler's formula unites exponential growth and circular trigonometry.",
                visual="Title displaying Euler's Formula and master equation e^{i theta} = cos(theta) + i sin(theta)",
                narration="Euler's formula reveals a profound bridge connecting exponential growth directly to trigonometry in the complex plane.",
            ),
            TeachingBeat(
                id="complex_plane",
                takeaway="In the complex plane, multiplying by i rotates by 90 degrees.",
                visual="Draw complex coordinate axes with Real horizontal axis and Imaginary vertical axis.",
                narration="In the complex plane, the horizontal axis represents real numbers and the vertical axis represents imaginary numbers. Multiplying by i corresponds to a 90-degree rotation.",
            ),
            TeachingBeat(
                id="unit_circle",
                takeaway="Points on the unit circle are parameterized by (cos theta, sin theta).",
                visual="Unit circle with radius 1, angle theta arc, and coordinates (cos theta, sin theta)",
                narration="On the unit circle, every point at an angle theta has coordinates cosine theta along the real axis, and sine theta along the imaginary axis.",
            ),
            TeachingBeat(
                id="continuous_rotation",
                takeaway="Imaginary velocity is perpendicular to position, creating uniform circular motion.",
                visual="Rotating vector along the unit circle showing perpendicular velocity vector",
                narration="Because multiplying by i turns velocity perpendicular to position, e to the i theta drives continuous circular motion at unit speed.",
            ),
            TeachingBeat(
                id="formula_synthesis",
                takeaway="Euler's formula connects exponential growth and circular coordinates.",
                visual="Formula highlighted: e^{i theta} = cos(theta) + i sin(theta)",
                narration="Euler's formula synthesizes these insights: e to the i theta equals cosine theta plus i sine theta.",
            ),
            TeachingBeat(
                id="identity_takeaway",
                takeaway="Setting theta = pi yields Euler's identity uniting 5 fundamental constants.",
                visual="Highlight theta = pi rotating to -1, revealing e^{i pi} + 1 = 0",
                narration="Setting theta equal to pi rotates halfway around the circle to minus one, giving Euler's identity: e to the i pi plus one equals zero.",
            ),
        ]
    elif "lorenz" in topic_lower or "attractor" in topic_lower or "chaos" in topic_lower:
        beats = [
            TeachingBeat(
                id="intro",
                takeaway="The Lorenz attractor reveals deterministic chaos arising from simple fluid convection equations.",
                visual="Title card: The Lorenz Attractor, with subtitle: Order, Chaos, and the Butterfly Effect.",
                narration="In 1963, meteorologist Edward Lorenz was studying a simplified mathematical model of atmospheric thermal convection. He simplified fluid dynamics into three coupled nonlinear differential equations. What he discovered revolutionized science: completely deterministic equations could produce behavior so unpredictable that it birthed modern chaos theory.",
            ),
            TeachingBeat(
                id="equations",
                takeaway="The Lorenz system consists of three coupled ordinary differential equations with parameters sigma, rho, and beta.",
                visual="Display the three equations: dx/dt = sigma(y - x), dy/dt = x(rho - z) - y, dz/dt = xy - beta z with parameters sigma=10, rho=28, beta=8/3.",
                narration="Here are the three governing equations. The variable x represents convective circulation speed, y measures horizontal temperature variation, and z represents vertical temperature distortion. The constants sigma, rho, and beta define physical fluid properties. Notice the nonlinear products, x times z and x times y; these two terms are the mathematical engine generating chaos.",
            ),
            TeachingBeat(
                id="phase_space",
                takeaway="In three-dimensional phase space, every point uniquely represents an instantaneous fluid state.",
                visual="Fade out equations and set up 3D coordinate frame with X, Y, and Z axes.",
                narration="To understand this dynamic system, we step into three-dimensional phase space. Here, each axis represents one of our three variables. Every single point in this space corresponds to a complete instantaneous state of the fluid. At every location, our equations assign a velocity vector dictating where the system travels next.",
            ),
            TeachingBeat(
                id="numerical_trajectory",
                takeaway="A trajectory spirals outward around one unstable focus until crossing over to the other.",
                visual="Trace a trajectory spiraling outward around the left focus, then crossing over to the right focus.",
                narration="Let us trace the path of a fluid state starting near the origin. The point spirals outward around one focal point as circulation intensifies. Once its amplitude grows large enough, it flings across to the second focus, beginning another outward spiral. The trajectory endlessly loops between the two sides, never settling into equilibrium and never repeating.",
            ),
            TeachingBeat(
                id="butterfly_geometry",
                takeaway="The full Lorenz attractor forms a double-lobed strange attractor resembling the wings of a butterfly.",
                visual="Display the full iconic butterfly attractor with dense orbital ribbons in yellow and cyan.",
                narration="When we trace thousands of steps, the iconic butterfly silhouette emerges. Mathematicians call this a strange attractor. It is an attractor because trajectories across phase space are pulled toward it; and it is strange because its geometric structure is a fractal, possessing infinite detail within a strictly bounded volume.",
            ),
            TeachingBeat(
                id="butterfly_effect",
                takeaway="The Butterfly Effect: trajectories starting exponentially close diverge into completely different states.",
                visual="Animate two trajectories starting 0.001 apart in contrasting colors, tracing together and then diverging to opposite wings.",
                narration="Now observe the defining hallmark of chaos: sensitive dependence on initial conditions, commonly called the Butterfly Effect. We release two trajectories differing by just one thousandth of a unit. At first, they trace identical paths side by side. But exponential divergence soon takes over; within moments, one trajectory turns left while the other turns right, ending on completely opposite wings.",
            ),
            TeachingBeat(
                id="bounded_fractal",
                takeaway="Because trajectories never intersect, the attractor has a fractional dimension between 2 and 3.",
                visual="Gently rotate view around the attractor, showing that sheets of trajectories never cross.",
                narration="A remarkable consequence of determinism is that the trajectory can never intersect itself, because that would mean two identical states having different futures. Since it loops forever within finite space without intersecting or repeating, the attractor cannot be a simple two-dimensional surface. It is a fractal manifold with a dimension of approximately 2.06.",
            ),
            TeachingBeat(
                id="conclusion",
                takeaway="Deterministic chaos reveals fundamental predictability horizons in nature.",
                visual="Final summary card: Determinism Does Not Imply Predictability.",
                narration="The Lorenz attractor taught humanity a profound truth: determinism does not guarantee predictability. Even with flawless mathematical laws, tiny measurement uncertainties inevitably blind our forecasts over time. In this balance of order and chaos, mathematics reveals its deepest elegance.",
            ),
        ]
    else:
        beats = [
            TeachingBeat(
                id="intro",
                takeaway=f"Introduction to {clean_topic}",
                visual=f"Title card displaying {clean_topic} and educational objective",
                narration=f"In this lesson, we explore the core intuition and geometric beauty of {clean_topic}.",
            ),
            TeachingBeat(
                id="setup",
                takeaway="Foundational components",
                visual="Coordinate frame and essential mathematical components",
                narration=f"To understand {clean_topic}, we first establish the foundational coordinate framework.",
            ),
            TeachingBeat(
                id="formula",
                takeaway="The central relationship",
                visual="Key mathematical formula written and highlighted",
                narration="Notice how this fundamental relationship connects distinct branches of mathematics together.",
            ),
            TeachingBeat(
                id="intuition",
                takeaway="Visual intuition",
                visual="Transformation illustrating the behavior of the expression",
                narration="When we trace this operation visually, the underlying geometric harmony becomes clear.",
            ),
            TeachingBeat(
                id="synthesis",
                takeaway="Synthesis of concepts",
                visual="Combined visualization showing the complete structure",
                narration="This perspective bridges algebraic calculation directly with geometric insight.",
            ),
            TeachingBeat(
                id="conclusion",
                takeaway="Summary and key takeaway",
                visual="Final summary card with highlighted conclusion",
                narration=f"In conclusion, {clean_topic} reveals how elegant relationships unify mathematical thinking.",
            ),
        ]
    return TeachingScript(
        scene_class_name=scene_name,
        throughline=f"A step-by-step visual exploration of {clean_topic}.",
        beats=beats,
    )


def _run_classifier():
    if dbos_enabled():
        from durable_agents import durable_classifier

        return durable_classifier
    return classifier_agent


def _run_planner():
    if dbos_enabled():
        from durable_agents import durable_lecture_planner

        return durable_lecture_planner
    return lecture_planner_agent


def _run_teaching_script():
    if dbos_enabled():
        from durable_agents import durable_teaching_script

        return durable_teaching_script
    return teaching_script_agent


def _run_coder():
    if dbos_enabled():
        from durable_agents import durable_coder

        return durable_coder
    return coder_agent


@dataclass
class PipelineDeps:
    topic: str | None = None
    subject: str | None = None
    lecture_plan: dict | None = None
    teaching_script: dict | None = None


# pai web (and other callers) often run the agent without deps=PipelineDeps().
# Keep pipeline state in a module store reset at classify_topic.
_pipeline_state = PipelineDeps()


def _reset_pipeline_state() -> PipelineDeps:
    global _pipeline_state
    _pipeline_state = PipelineDeps()
    return _pipeline_state


def _pipeline_state_for(ctx: RunContext[PipelineDeps]) -> PipelineDeps:
    if ctx.deps is not None:
        return ctx.deps
    return _pipeline_state


@dataclass
class AnimationState:
    user_query: str
    target_length: str = "medium"
    cinematic: bool = False
    classification: Classification | None = None
    plan: Lecture | None = None
    teaching_script: TeachingScript | None = None
    code: str | None = None
    run_dir: str | None = None
    coder_result: CoderRunResult | None = None
    prompt_index: int | None = None
    animation_mode: str = "keyframe"


def _subject_str(subject: str | Subject) -> str:
    if isinstance(subject, Subject):
        return subject.value
    return str(subject)


def _assistant_text_from_messages(messages: list | None) -> str:
    if not messages:
        return ""
    chunks: list[str] = []
    for msg in messages:
        if getattr(msg, "kind", None) not in (None, "response"):
            continue
        for part in getattr(msg, "parts", None) or []:
            content = getattr(part, "content", None)
            if not isinstance(content, str) or not content.strip():
                continue
            part_kind = getattr(part, "part_kind", None)
            if part_kind in (None, "text"):
                chunks.append(content)
    return "\n".join(chunks)


def _salvage_codemode_text_dump(
    run_dir,
    *,
    summary: str,
    messages: list | None,
) -> None:
    """If the model dumped run_code as chat text or wrote a scene without compiling, compile."""
    from tools.compile import compile_manim_code
    from tools.manim_write import manim_write

    manifest = load_manifest(run_dir)
    if manifest.get("scene_file") and not (manifest.get("last_compile") or {}).get("ok"):
        scene_file = Path(run_dir) / manifest["scene_file"]
        if scene_file.exists():
            code = scene_file.read_text(encoding="utf-8")
            scene_name = manifest.get("scene_name") or (manifest.get("last_write") or {}).get("scene_name") or "Scene"
            compile_manim_code(
                code=code,
                scene_name=scene_name,
                output_dir=str(run_dir),
            )
            return

    if manifest.get("scene_file") or (manifest.get("last_write") or {}).get("ok"):
        return

    blob = summary or ""
    extracted = extract_codemode_dump(blob)
    if extracted is None:
        extracted = extract_codemode_dump(_assistant_text_from_messages(messages))
    if extracted is None:
        for cand in Path(run_dir).glob("*.py"):
            if cand.name not in ("__init__.py",):
                cand_code = cand.read_text(encoding="utf-8")
                extracted = extract_codemode_dump(cand_code)
                if extracted:
                    break
    if extracted is None:
        return

    manim_write(
        code=extracted.code,
        scene_name=extracted.scene_name,
        output_dir=str(run_dir),
    )
    compile_manim_code(
        code=extracted.code,
        scene_name=extracted.scene_name,
        output_dir=str(run_dir),
    )


async def run_coder_step(
    topic: str,
    subject: str | Subject,
    plan: Lecture | str | dict,
    *,
    teaching_script: TeachingScript | dict | None = None,
    usage: RunUsage | None = None,
    user_prompt: str | None = None,
    prompt_index: int | None = None,
    existing_run_dir: str | None = None,
    feedback: str | None = None,
    length: str = "medium",
    cinematic: bool = False,
    animation_mode: str = "keyframe",
) -> CoderRunResult:
    """Write/compile Manim for a topic; shared by the graph node and web tools."""
    if dbos_enabled():
        ensure_dbos_launched()

    run_dir = Path(existing_run_dir) if existing_run_dir else new_coder_run_dir(topic)

    payload = plan_to_payload(plan)
    script_payload = teaching_script_to_payload(teaching_script)
    if script_payload:
        payload["teaching_script"] = script_payload
        try:
            (run_dir / "teaching_script.json").write_text(
                json.dumps(script_payload, indent=2), encoding="utf-8"
            )
            manifest = load_manifest(run_dir)
            manifest["teaching_script"] = script_payload
            manifest["topic"] = topic
            save_manifest(run_dir, manifest)
        except Exception:
            pass
    local_coder = is_ollama(model_for("coder"))
    prompt = build_coder_user_prompt(
        topic=topic,
        subject=_subject_str(subject),
        output_dir=run_dir,
        plan_payload=payload,
        compact=local_coder,
        include_codemode_hint=local_coder,
        length=length,
        cinematic=cinematic,
        mode=animation_mode,
    )
    if feedback and existing_run_dir:
        from pathlib import Path
        code_file = Path(existing_run_dir) / "lecture.py"
        if not code_file.exists():
            code_file = Path(existing_run_dir) / "scene.py"
        current_code = code_file.read_text(encoding="utf-8") if code_file.exists() else ""
        prompt += f"\n\nExisting Code:\n```python\n{current_code}\n```\n\nUser Feedback for Revision:\n{feedback}\nRevise the code to address this feedback."

    if sft_batch_enabled():
        prompt += SFT_BATCH_ADDENDUM

    messages = None
    run_usage = usage
    summary = ""
    stopped_reason = "completed"
    request_limit = int(os.getenv("AOS_CODER_MAX_REQUESTS", "6"))
    coder_limits = UsageLimits(request_limit=request_limit)

    try:
        async def _call_coder():
            return await _run_coder().run(prompt, usage=usage, usage_limits=coder_limits)

        result = await execute_with_llm_retry(_call_coder, operation_name="Coder Agent")
        messages = result.all_messages()
        run_usage = result.usage
        summary = str(result.output) if result.output is not None else ""
    except UsageLimitExceeded as exc:
        stopped_reason = f"usage_limit: {exc}"
        summary = stopped_reason
    except Exception as exc:
        stopped_reason = format_custom_endpoint_error(exc)
        summary = stopped_reason

    _salvage_codemode_text_dump(run_dir, summary=summary, messages=messages)

    manifest = load_manifest(run_dir)
    if (manifest.get("last_compile") or {}).get("ok"):
        stopped_reason = "completed"

    return arrange_coder_artifacts(
        run_dir,
        messages=messages,
        usage=run_usage,
        summary=summary,
        stopped_reason=stopped_reason,
        request_limit=request_limit,
        tool_calls_limit=None,
        user_prompt=user_prompt or topic,
        prompt_index=prompt_index,
    )


@dataclass
class ClassifyNode(BaseNode[AnimationState, None, str]):
    async def run(
        self, ctx: GraphRunContext[AnimationState]
    ) -> "PlanLectureNode | End[str]":
        if dbos_enabled():
            ensure_dbos_launched()
        classify_error: str | None = None
        try:
            async def _call_classify():
                return await _run_classifier().run(ctx.state.user_query)

            result = await execute_with_llm_retry(_call_classify, operation_name="Classifier Agent")
            ctx.state.classification = result.output
        except Exception as exc:
            classify_error = format_custom_endpoint_error(exc)
            print(f"classifier error: {classify_error}", file=sys.stderr, flush=True)
            ctx.state.classification = None

        if (
            ctx.state.classification is None
            or ctx.state.classification.subject == Subject.UNKNOWN
        ):
            fallback = _heuristic_classification(ctx.state.user_query)
            if fallback is not None:
                print(
                    f"-> ClassifyFallback {fallback.subject} {fallback.topic}",
                    file=sys.stderr,
                    flush=True,
                )
                ctx.state.classification = fallback
            else:
                detail = "Domain not supported or classification failed."
                if classify_error:
                    detail = f"{detail} ({classify_error[:400]})"
                return End(detail)

        return PlanLectureNode()


@dataclass
class PlanLectureNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "PlanTeachingScriptNode":
        if dbos_enabled():
            ensure_dbos_launched()
        plan_error: str | None = None
        classification = ctx.state.classification
        topic = classification.topic if classification else "Math Topic"
        subject = classification.subject if classification else Subject.MATH
        try:
            async def _call_planner():
                return await _run_planner().run(
                    f"Topic: {topic}\n"
                    f"Subject: {subject}"
                )

            result = await execute_with_llm_retry(_call_planner, operation_name="Lecture Planner Agent")
            ctx.state.plan = result.output
        except Exception as exc:
            plan_error = format_custom_endpoint_error(exc)
            print(f"planner error: {plan_error}", file=sys.stderr, flush=True)
            ctx.state.plan = None

        if ctx.state.plan is None:
            print(
                f"-> PlanFallback {subject} {topic}",
                file=sys.stderr,
                flush=True,
            )
            ctx.state.plan = _heuristic_lecture_plan(topic, subject)

        return PlanTeachingScriptNode()


@dataclass
class PlanTeachingScriptNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "CodeAgent":
        if dbos_enabled():
            ensure_dbos_launched()
        classification = ctx.state.classification
        plan = ctx.state.plan
        if classification is None or plan is None:
            return CodeAgent()
        try:
            async def _call_teaching_script():
                return await _run_teaching_script().run(
                    teaching_script_user_prompt(
                        classification.topic,
                        _subject_str(classification.subject),
                        plan,
                        length=ctx.state.target_length,
                        cinematic=ctx.state.cinematic,
                    )
                )

            result = await execute_with_llm_retry(_call_teaching_script, operation_name="Teaching Script Agent")
            ctx.state.teaching_script = result.output
        except Exception as exc:
            print(
                f"teaching script error: {format_custom_endpoint_error(str(exc))}",
                file=sys.stderr,
                flush=True,
            )
            ctx.state.teaching_script = None

        if ctx.state.teaching_script is None:
            print(
                f"-> TeachingScriptFallback {classification.subject} {classification.topic}",
                file=sys.stderr,
                flush=True,
            )
            ctx.state.teaching_script = _heuristic_teaching_script(
                classification.topic, classification.subject, plan
            )

        return CodeAgent()


@dataclass
class CodeAgent(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> End[str]:
        coder_result = await run_coder_step(
            ctx.state.classification.topic,
            ctx.state.classification.subject,
            ctx.state.plan,
            teaching_script=ctx.state.teaching_script,
            user_prompt=ctx.state.user_query,
            prompt_index=ctx.state.prompt_index,
            length=ctx.state.target_length,
            cinematic=ctx.state.cinematic,
            animation_mode=ctx.state.animation_mode,
        )
        ctx.state.run_dir = coder_result.run_dir
        ctx.state.coder_result = coder_result
        ctx.state.code = coder_result.code

        end_summary = (
            f"stopped={coder_result.stopped_reason} "
            f"compile_ok={coder_result.compile_ok} "
            f"scene={coder_result.scene_name} "
            f"run_dir={coder_result.run_dir} "
            f"audio={len(coder_result.audio_paths)}"
        )
        return End(end_summary)


g = GraphBuilder(
    state_type=AnimationState, output_type=str, name="Manim Animation Graph"
)


@g.step
async def start(state: AnimationState) -> ClassifyNode:
    return ClassifyNode()


g.add(
    g.node(ClassifyNode),
    g.node(PlanLectureNode),
    g.node(PlanTeachingScriptNode),
    g.node(CodeAgent),
    g.edge_from(g.start_node).to(start),
)

animation_graph = g.build()

import asyncio


def _find_compiled_video(run_dir: str | None) -> Path | None:
    if not run_dir:
        return None
    root = Path(run_dir)
    if not root.is_dir():
        return None
    manifest_path = root / "manifest.json"
    if manifest_path.is_file():
        try:
            import json
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            last = manifest.get("last_compile") or {}
            candidate = last.get("video_path") or manifest.get("video_path")
            if candidate and Path(candidate).is_file():
                return Path(candidate)
        except Exception:
            pass
    for path in root.rglob("*.mp4"):
        if path.is_file() and "partial_movie_files" not in path.parts:
            return path
    return None


async def run_pipeline(
    user_query: str,
    *,
    length: str = "medium",
    cinematic: bool = False,
    prompt_index: int | None = None,
    mode: str = "keyframe",
    output_dir: str | Path | None = None,
) -> dict:
    if dbos_enabled():
        ensure_dbos_launched()

    # Integrated Keyframe Producer-Consumer Engine for UI Animate Mode
    if mode == "keyframe":
        from keyframe_engine import run_producer_consumer

        total_slides = 3
        if length in ("5m", "medium", "5"):
            total_slides = 3
        elif length in ("10m", "long", "10"):
            total_slides = 4
        elif length in ("short", "1m", "1"):
            total_slides = 2

        res = await asyncio.to_thread(
            run_producer_consumer,
            user_query,
            output_dir=output_dir,
            total_slides=total_slides,
        )
        if res.get("scene_file") and not res.get("scene_path"):
            res["scene_path"] = res["scene_file"]
        return res

    from cinematic_director import is_cinematic_mode
    cinematic_active = is_cinematic_mode(user_query, flag=cinematic)
    state = AnimationState(
        user_query=user_query,
        target_length=length,
        cinematic=cinematic_active,
        prompt_index=prompt_index,
        animation_mode=mode,
    )
    # Prefer iter so UI/Celery can stream ``-> {node_id}`` on stderr.
    summary = ""
    try:
        async with animation_graph.iter(state=state) as run:
            async for step in run:
                if isinstance(step, EndMarker):
                    summary = step.value if isinstance(step.value, str) else ""
                    break
                for task in step:
                    print(f"-> {task.node_id}", file=sys.stderr, flush=True)
    except Exception as exc:
        raise RuntimeError(format_custom_endpoint_error(exc)) from exc
    if state.coder_result is not None:
        result = state.coder_result.model_dump(mode="json")
        if prompt_index is not None:
            result["prompt_index"] = prompt_index

        import os
        if os.getenv("S3_VIDEO_ENDPOINT"):
            try:
                import uuid
                from tools.minio_storage import upload_to_minio
                video_path = _find_compiled_video(state.coder_result.run_dir)
                if video_path and video_path.is_file():
                    gen_id = uuid.uuid4()
                    video_key = f"videos/pipeline/{gen_id}.mp4"
                    code_key = f"videos/pipeline/{gen_id}.py"

                    video_url = upload_to_minio(video_path, object_key=video_key, content_type="video/mp4")
                    result["minio_url"] = video_url
                    result["minio_key"] = video_key
                    print(f"[minio] Uploaded video to {video_url}", file=sys.stderr, flush=True)

                    if state.coder_result.scene_file:
                        scene_path = Path(state.coder_result.run_dir) / state.coder_result.scene_file
                        if scene_path.is_file():
                            code_url = upload_to_minio(scene_path, object_key=code_key, content_type="text/x-python")
                            result["code_minio_url"] = code_url
                            result["code_minio_key"] = code_key
                            print(f"[minio] Uploaded scene code to {code_url}", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"[minio] Upload failed: {e}", file=sys.stderr, flush=True)

        return result
    return {
        "result": summary,
        "stopped_reason": "classification_failed_or_unsupported",
        "error": summary or "classification_failed_or_unsupported",
        "message": summary or "Domain not supported or classification failed.",
    }


animation_agent = Agent(
    model_for_agent("animation"),
    deps_type=PipelineDeps,
    name="Manim Animation Pipeline",
    description="Runs classify → lecture plan → Manim code/compile for a learning topic.",
    model_settings=settings_for("animation"),
    system_prompt=(
        "You run the Manim animation pipeline for educational topics.\n"
        "Act immediately — do not write long reasoning or preambles.\n"
        "Call tools in this exact order:\n"
        "1. classify_topic with the user's exact message\n"
        "2. plan_lecture with the returned topic and subject "
        "(skip if subject is unknown / unsupported — tell the user and stop)\n"
        "3. write_manim_animation with topic and subject only "
        "(the lecture plan and teaching script are stored automatically — "
        "do not pass plan text)\n"
        "4. If the user provides feedback on an already generated animation (e.g. 'make the circle blue', 'fix the error'), call "
        "revise_manim_animation with their feedback and the run_dir from the previous step.\n"
        "Between tools, at most one short status line "
        "(e.g. 'Classifying…', 'Planning…', 'Writing Manim…', 'Revising…').\n"
        "After write_manim_animation or revise_manim_animation, summarize only from the tool result: "
        "stopped_reason, compile_ok, scene_name, run_dir, audio count. "
        "Do not invent paths or invent success if the tool reported failure."
    ),
)


@animation_agent.tool
async def classify_topic(ctx: RunContext[PipelineDeps], user_query: str) -> dict:
    """Classify the user request into a subject domain and lecture topic."""
    _reset_pipeline_state()
    result = await classifier_agent.run(user_query, usage=ctx.usage)
    classification = result.output
    if classification is None:
        return {
            "ok": False,
            "supported": False,
            "subject": "unknown",
            "topic": None,
            "message": "Classification failed.",
        }
    supported = classification.subject != Subject.UNKNOWN
    payload = classification.model_dump(mode="json")
    payload["ok"] = True
    payload["supported"] = supported
    if not supported:
        payload["message"] = "Domain not supported (outside Math/CS/AI)."
    return payload


@animation_agent.tool
async def plan_lecture(ctx: RunContext[PipelineDeps], topic: str, subject: str) -> dict:
    """Generate a lecture plan and teaching script for the classified topic."""
    result = await lecture_planner_agent.run(
        f"Topic: {topic}\nSubject: {subject}",
        usage=ctx.usage,
    )
    plan = result.output
    if plan is None:
        return {"ok": False, "message": "Lecture planning failed."}
    if hasattr(plan, "model_dump"):
        plan_payload = plan.model_dump(mode="json")
    else:
        plan_payload = {"raw": str(plan)}
    state = _pipeline_state_for(ctx)
    state.topic = topic
    state.subject = subject
    state.lecture_plan = plan_payload
    script_payload = None
    try:
        script_result = await teaching_script_agent.run(
            teaching_script_user_prompt(topic, subject, plan_payload),
            usage=ctx.usage,
        )
        script_payload = teaching_script_to_payload(script_result.output)
        state.teaching_script = script_payload
    except Exception as exc:
        print(
            f"teaching script error: {format_custom_endpoint_error(str(exc))}",
            file=sys.stderr,
            flush=True,
        )
        state.teaching_script = None
    return {"ok": True, "plan": plan_payload, "teaching_script": script_payload}


@animation_agent.tool
async def write_manim_animation(
    ctx: RunContext[PipelineDeps],
    topic: str,
    subject: str,
) -> dict:
    """Write, compile, and optionally narrate Manim code from the stored lecture plan."""
    state = _pipeline_state_for(ctx)
    if state.lecture_plan is None:
        return {
            "ok": False,
            "stopped_reason": "no_plan",
            "message": "No lecture plan stored — call plan_lecture first.",
        }
    if state.teaching_script is None:
        try:
            script_result = await teaching_script_agent.run(
                teaching_script_user_prompt(topic, subject, state.lecture_plan),
                usage=ctx.usage,
            )
            state.teaching_script = teaching_script_to_payload(script_result.output)
        except Exception as exc:
            print(
                f"teaching script error: {format_custom_endpoint_error(str(exc))}",
                file=sys.stderr,
                flush=True,
            )
    coder_result = await run_coder_step(
        topic,
        subject,
        state.lecture_plan,
        teaching_script=state.teaching_script,
        usage=ctx.usage,
    )
    return coder_result.model_dump(mode="json")


@animation_agent.tool
async def revise_manim_animation(
    ctx: RunContext[PipelineDeps],
    feedback: str,
    run_dir: str,
) -> dict:
    """Revise an existing Manim animation based on user feedback."""
    state = _pipeline_state_for(ctx)
    if not state.topic or not state.subject or not state.lecture_plan:
        return {
            "ok": False,
            "message": "Cannot revise: no lecture plan in current state. Please generate an animation first.",
        }

    coder_result = await run_coder_step(
        state.topic,
        state.subject,
        state.lecture_plan,
        teaching_script=state.teaching_script,
        usage=ctx.usage,
        existing_run_dir=run_dir,
        feedback=feedback,
    )
    return coder_result.model_dump(mode="json")


if __name__ == "__main__":
    prompt = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "I want to learn about Hairy Ball theorem."
    )
    result = asyncio.run(run_pipeline(prompt))
    print(result)
