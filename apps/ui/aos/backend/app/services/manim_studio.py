"""Interactive Manim Studio Service: Multi-stage human-in-the-loop pipeline.

Provides a class-based, object-oriented architecture for:
1. ManimTextClassifier: Analyzes educational text animatability using regex heuristics and Pydantic AI agent.
2. ManimPlanComposer: Generates structured scenes.md visual plans and SSE streaming events.
3. ManimCodeSynthesizer: Generates safe Manim Community Edition code from approved plans with SSE streaming.
4. ManimCodeRepairer: Performs in-place targeted repair of compiler and runtime tracebacks.
5. ManimRenderEngine: Executes native or Docker renders, artifact collection, and MinIO storage sync.
6. ManimStudioService: Unified master service facade orchestrating all stages.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any, AsyncGenerator, Literal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import app.agents.hitl_agents as hitl_agents
from app.agents.error_classifier import classify_error, get_repair_guidance
from app.core.config import settings
from app.db.models.video_generation import VideoGeneration
from app.repositories import video_generation as video_repo
from app.schemas.video_generation import (
    VideoClassifyResponse,
    VideoCodeResponse,
    VideoPlanResponse,
    VideoRenderCustomResponse,
)
from app.services.manim_code import preflight_manim_code, repair_manim_code
from app.services.video_storage import get_video_storage, video_object_key, code_object_key

logger = logging.getLogger(__name__)

# ── LLM generation limits ────────────────────────────────────────────────────
MANIM_MAX_OUTPUT_TOKENS: int = 3_000
MANIM_MAX_CONTEXT_CHARS: int = 4_000
LLM_MAX_RETRIES: int = 3

# Heuristic patterns indicating mathematical or scientific content suitable for Manim
MATH_PATTERNS = [
    r"\$\$[\s\S]+?\$\$",  # Display math
    r"\$[^\$]+?\$",        # Inline math
    r"\\frac\{.*?\}\{.*?\}",
    r"\\sum_?\{?.*?\}?",
    r"\\int_?\{?.*?\}?",
    r"\\prod_?\{?.*?\}?",
    r"\\lim_?\{?.*?\}?",
    r"\\begin\{equation\}",
    r"\\begin\{align\}",
    r"\\begin\{matrix\}",
    r"\\mathbf\{",
    r"f\([a-z]\)",
    r"f'\(",
    r"f''\(",
    r"e\^\{?[a-z0-9\+\-]+?\}?",
    r"\\sin|\\cos|\\tan|\\theta|\\pi|\\alpha|\\beta|\\lambda",
    r"\\partial",
    r"\\sqrt",
]

KEYWORDS_ANIMATABLE = [
    # Series & approximations
    "taylor series", "taylor's formula", "taylor's series", "maclaurin series",
    "fourier transform", "fourier series", "power series", "geometric series",
    # Exponential & logarithm
    "exponential", "euler's number", "number e", "natural logarithm", "logarithm",
    "e^x", "e^{x", "compound interest", "continuous growth", "exponential growth",
    "exponential decay", "half-life",
    # Calculus
    "derivative", "integral", "calculus", "differential", "antiderivative",
    "riemann sum", "limit", "continuity", "chain rule", "product rule",
    "integration by parts", "fundamental theorem",
    # Algebra & linear algebra
    "euler's formula", "complex number", "imaginary number", "pythagorean",
    "eigenvector", "eigenvalue", "matrix multiplication", "linear transformation",
    "determinant", "dot product", "cross product", "vector",
    # Probability & statistics
    "probability", "normal distribution", "binomial distribution", "bayes",
    "central limit theorem", "standard deviation", "variance", "markov chain",
    "random variable", "expected value",
    # Geometry & topology
    "trigonometry", "coordinate system", "vector field", "complex plane",
    "polar coordinates", "parametric", "surface area", "volume",
    # CS & algorithms
    "gradient descent", "neural network", "backpropagation", "sorting algorithm",
    "binary search", "dijkstra", "graph traversal", "big o", "time complexity",
    "dynamic programming", "recursion",
]


# ── OOP Class 1: Text Classifier ──────────────────────────────────────────────

class ManimTextClassifier:
    """Classifies educational text for Manim animatability using heuristics and LLM agents."""

    def __init__(
        self,
        math_patterns: list[str] | None = None,
        keywords_animatable: list[str] | None = None,
        max_context_chars: int = MANIM_MAX_CONTEXT_CHARS,
    ) -> None:
        self.math_patterns = math_patterns or MATH_PATTERNS
        self.keywords_animatable = keywords_animatable or KEYWORDS_ANIMATABLE
        self.max_context_chars = max_context_chars

    def classify_heuristic(self, text: str) -> VideoClassifyResponse:
        """Classify educational text animatability using fast deterministic patterns."""
        lower_text = text.lower()

        # Check for exact keywords
        for kw in self.keywords_animatable:
            if kw in lower_text:
                topic = kw.title()
                is_math = any(m in kw for m in (
                    "series", "formula", "calculus", "derivative", "integral",
                    "matrix", "linear", "vector", "exponential", "logarithm",
                    "probability", "distribution", "euler", "fourier",
                    "e^x", "e^{x", "number e", "pythagorean", "eigen",
                    "determinant", "dot", "cross", "trigonometry", "coordinate",
                    "polar", "parametric", "surface", "volume", "limit",
                ))
                return VideoClassifyResponse(
                    animatable=True,
                    subject="math" if is_math else "cs",
                    topic=topic,
                    reason=f"Identified core animatable concept '{topic}'.",
                )

        # Check for LaTeX / math patterns
        math_matches = 0
        for pattern in self.math_patterns:
            if re.search(pattern, text):
                math_matches += 1

        if math_matches >= 2 or (math_matches >= 1 and any(
            term in lower_text for term in (
                "formula", "equation", "function", "theorem",
                "approximation", "series", "number",
            )
        )):
            # Extract potential title from heading or first line
            lines = [line.strip("#* \t\r\n") for line in text.splitlines() if line.strip("#* \t\r\n")]
            title = lines[0][:60] if lines else "Mathematical Derivation"
            return VideoClassifyResponse(
                animatable=True,
                subject="math",
                topic=title,
                reason="Detected mathematical content suitable for Manim visualization.",
            )

        # Computer science / algorithms check
        if any(k in lower_text for k in ("algorithm", "tree", "node", "time complexity", "big o", "recursion", "array")):
            return VideoClassifyResponse(
                animatable=True,
                subject="cs",
                topic="Algorithmic Structure",
                reason="Detected data structure / algorithm concepts.",
            )

        return VideoClassifyResponse(
            animatable=False,
            subject="unknown",
            topic="",
            reason="Content does not appear to contain visual material suited for Manim.",
        )

    async def classify(
        self,
        text: str,
        *,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> VideoClassifyResponse:
        """Classify educational text animatability using a Pydantic AI agent with fallback."""
        stripped = (text or "").strip()
        if not stripped:
            return VideoClassifyResponse(
                animatable=False,
                subject="unknown",
                topic="",
                reason="Empty text provided.",
            )

        try:
            key, url, _ = hitl_agents._resolve_llm_config(
                api_key=api_key, base_url=base_url, model_name=model_name
            )
            if (not key or key == "sk-local") and "openrouter.ai" in url:
                return self.classify_heuristic(text)

            agent = hitl_agents.get_classifier_agent(
                model_name=model_name, base_url=base_url, api_key=api_key
            )
            capped_text = text[:self.max_context_chars]
            prompt = (
                "Please classify the following educational content for Manim animatability:\n\n"
                f"{capped_text}"
            )
            result = await asyncio.wait_for(agent.run(prompt), timeout=15.0)
            output = getattr(result, "output", getattr(result, "data", None))
            if isinstance(output, VideoClassifyResponse):
                return output
        except Exception as exc:
            logger.warning(
                "Pydantic AI classification agent failed or timed out (%s); falling back to heuristic.",
                exc,
            )

        return self.classify_heuristic(text)

    def classify_sync(
        self,
        text: str,
        *,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> VideoClassifyResponse:
        """Synchronous wrapper for classify."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            return self.classify_heuristic(text)

        return asyncio.run(
            self.classify(text, model_name=model_name, base_url=base_url, api_key=api_key)
        )


# ── OOP Class 2: Plan Composer ────────────────────────────────────────────────

class ManimPlanComposer:
    """Generates structured visual plans (scenes.md) and SSE streams using composer skills."""

    def __init__(self, max_context_chars: int = MANIM_MAX_CONTEXT_CHARS) -> None:
        self.max_context_chars = max_context_chars

    def generate_fallback_plan(self, text: str, topic: str) -> str:
        """Generate a topic-aware pedagogical plan when LLM is unavailable."""
        clean_topic = topic or "Mathematical Concept"
        first_lines = [l.strip() for l in text.splitlines() if l.strip()][:3]
        text_hint = " ".join(first_lines)[:200] if first_lines else clean_topic
        return f"""# Visualizing {clean_topic}

## Overview
- **Topic**: {clean_topic}
- **Hook**: How does the core idea behind {clean_topic} connect to visual geometric intuition?
- **Target Audience**: STEM learners
- **Estimated Length**: ~30 seconds
- **Key Insight**: Understanding {clean_topic} through step-by-step visual construction.

## Narrative Arc
We begin with the definition of {clean_topic}, introduce its key formula, and build visual intuition using annotated Manim animations.

---

## Scene 1: Introduction & Core Definition
**Duration**: ~12 seconds
**Purpose**: Introduce {clean_topic} and present its primary definition.

### Visual Elements
- Title: `Text("{clean_topic}", font_size=40).to_edge(UP)`
- Core definition or formula as `MathTex`.
- Annotated labels explaining each symbol.

### Content
1. Fade in the title with an accent underline.
2. Write the core definition or equation at the screen centre.
3. Highlight key symbols in YELLOW and TEAL.

### Technical Notes
- Use `MathTex` with color-coded substrings.
- Use `to_edge(UP)` for title and `next_to` for annotations.

---

## Scene 2: Key Properties & Visual Intuition
**Duration**: ~18 seconds
**Purpose**: Demonstrate the most important properties or applications of {clean_topic}.

### Visual Elements
- Secondary formulas or visual diagrams.
- Annotated arrows or highlight boxes.

### Content
1. Present key properties one-by-one with `Write` and `FadeIn` animations.
2. Use `SurroundingRectangle` to emphasise each key term.
3. Conclude with a summary line.

---

## Color Palette
- Primary: `BLUE_C`
- Secondary: `YELLOW`
- Accent: `TEAL`
- Text: `WHITE` / `LIGHT_GREY`

## Mathematical Content
Derived from source material: {text_hint}
"""

    async def compose(
        self,
        text: str,
        hints: str | None = None,
        *,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> VideoPlanResponse:
        """Generate a structured scenes.md visual plan using manim-composer skills."""
        classification = await classify_text_for_manim(
            text, model_name=model_name, base_url=base_url, api_key=api_key
        )
        topic = classification.topic or "Mathematical Concept"

        capped_text = text[:self.max_context_chars]
        if len(text) > self.max_context_chars:
            capped_text += "\n\n[... content truncated for context window ...]"
            logger.info(
                "compose_plan: knowledge_text truncated from %d to %d chars",
                len(text), self.max_context_chars,
            )

        user_prompt = f"Educational Content:\n{capped_text}\n\n"
        if hints:
            user_prompt += f"User specific visual preferences / hints:\n{hints}\n\n"
        user_prompt += f"Please construct a comprehensive scenes.md visual plan for Manim focusing on topic '{topic}'."

        plan_markdown = ""
        try:
            agent = hitl_agents.get_composer_agent(model_name, base_url, api_key)
            deps = hitl_agents.HitlPlanDeps(topic=topic, hints=hints, source_text=capped_text)
            result = await agent.run(user_prompt, deps=deps)
            plan_markdown = getattr(result, "output", getattr(result, "data", "")) or ""
        except Exception as exc:
            logger.warning("Plan LLM call failed (%s); using topic-aware fallback plan.", exc)

        if not plan_markdown or len(plan_markdown.strip()) < 100:
            plan_markdown = self.generate_fallback_plan(text, topic)

        return VideoPlanResponse(
            plan=plan_markdown,
            title=f"Visual Plan: {topic}",
            topic=topic,
        )

    async def compose_stream(
        self,
        text: str,
        hints: str | None = None,
        *,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream scenes.md visual plan generation events via SSE."""
        classification = await classify_text_for_manim(
            text, model_name=model_name, base_url=base_url, api_key=api_key
        )
        topic = classification.topic or "Mathematical Concept"

        yield f"data: {json.dumps({'type': 'start', 'topic': topic, 'title': f'Visual Plan: {topic}'})}\n\n"
        yield f"data: {json.dumps({'type': 'status', 'message': 'Analyzing the lesson and preparing a visual brief…'})}\n\n"

        capped_text = text[:self.max_context_chars]
        if len(text) > self.max_context_chars:
            capped_text += "\n\n[... content truncated for context window ...]"

        user_prompt = f"Educational Content:\n{capped_text}\n\n"
        if hints:
            user_prompt += f"User specific visual preferences / hints:\n{hints}\n\n"
        user_prompt += f"Please construct a comprehensive scenes.md visual plan for Manim focusing on topic '{topic}'."

        accumulated: list[str] = []
        stream_failed = False
        try:
            agent = hitl_agents.get_composer_agent(model_name, base_url, api_key)
            deps = hitl_agents.HitlPlanDeps(topic=topic, hints=hints, source_text=capped_text)
            async with agent.run_stream(user_prompt, deps=deps) as result:
                async for chunk in result.stream_text(delta=True):
                    accumulated.append(chunk)
                    yield f"data: {json.dumps({'type': 'token', 'token': chunk})}\n\n"
        except Exception as exc:
            logger.warning("Streaming plan generation failed: %s", exc)
            stream_failed = True

        full_plan = "".join(accumulated).strip()
        if stream_failed or len(full_plan) < 100:
            yield f"data: {json.dumps({'type': 'status', 'message': 'Completing the visual plan with the local fallback…'})}\n\n"
            fallback = self.generate_fallback_plan(text, topic)
            if not accumulated:
                chunk_size = 64
                for i in range(0, len(fallback), chunk_size):
                    chunk = fallback[i : i + chunk_size]
                    yield f"data: {json.dumps({'type': 'token', 'token': chunk})}\n\n"
                    await asyncio.sleep(0.01)
                full_plan = fallback

        yield f"data: {json.dumps({'type': 'status', 'message': 'Visual plan complete.'})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'plan': full_plan, 'topic': topic, 'title': f'Visual Plan: {topic}'})}\n\n"


# ── OOP Class 3: Code Synthesizer ─────────────────────────────────────────────

class ManimCodeSynthesizer:
    """Synthesizes valid Manim Community Edition code from approved visual plans."""

    def __init__(self, max_context_chars: int = MANIM_MAX_CONTEXT_CHARS) -> None:
        self.max_context_chars = max_context_chars

    def generate_fallback_code(self, plan: str, knowledge_text: str | None = None) -> tuple[str, str]:
        """Generate a topic-aware minimal Manim scene when LLM code generation fails."""
        topic = "Mathematical Concept"
        if plan:
            header_match = re.search(r"^#\s+(.+)$", plan, re.MULTILINE)
            if header_match:
                topic = header_match.group(1).strip().replace("Visualizing ", "")
        if topic == "Mathematical Concept" and knowledge_text:
            first = [l.strip() for l in knowledge_text.splitlines() if l.strip()]
            if first:
                topic = first[0][:60]

        clean_topic = re.sub(r"['’]s\b", "", topic, flags=re.IGNORECASE)
        clean_topic = re.sub(r"[^A-Za-z0-9 ]+", " ", clean_topic)
        safe_name = re.sub(r"[^A-Za-z0-9]", "", clean_topic.title())
        if not safe_name or not safe_name[0].isalpha():
            safe_name = "TopicScene"
        scene_name = f"{safe_name}Scene"

        topic_escaped = topic.replace("\\", "\\\\").replace('"', '\\"')

        code = f'''from manim import *

class {scene_name}(Scene):
    def construct(self):
        # Title
        title = Text("{topic_escaped}", font_size=40, color=BLUE_C)
        title.to_edge(UP, buff=0.5)
        underline = Line(LEFT * 5, RIGHT * 5, color=BLUE_E).next_to(title, DOWN, buff=0.15)
        self.play(Write(title), GrowFromCenter(underline))
        self.wait(1)

        # Intro description
        intro = Text(
            "Exploring the core ideas of {topic_escaped}.",
            font_size=26, color=GRAY_A
        )
        intro.next_to(underline, DOWN, buff=0.5)
        self.play(FadeIn(intro, shift=UP * 0.2))
        self.wait(1.5)

        # Highlight box
        box = SurroundingRectangle(intro, color=YELLOW, buff=0.25)
        self.play(Create(box))
        self.wait(1.5)

        # Conclusion
        self.play(FadeOut(box), FadeOut(intro))
        conclusion = Text(
            "Visual animation for {topic_escaped} is ready.",
            font_size=28, color=TEAL
        ).next_to(underline, DOWN, buff=0.5)
        self.play(FadeIn(conclusion))
        self.wait(2)
        self.play(FadeOut(Group(*self.mobjects)))
'''
        return code, scene_name

    async def synthesize(
        self,
        plan: str,
        knowledge_text: str | None = None,
        scene_name: str | None = None,
        *,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        repair_error: str | None = None,
    ) -> VideoCodeResponse:
        """Generate Manim Community Edition code from the approved visual plan."""
        capped_plan = plan[:self.max_context_chars]
        if len(plan) > self.max_context_chars:
            capped_plan += "\n\n[... plan truncated for context window ...]"
            logger.info("synthesize_code: plan truncated from %d to %d chars", len(plan), self.max_context_chars)

        capped_knowledge: str | None = None
        if knowledge_text:
            capped_knowledge = knowledge_text[:self.max_context_chars]
            if len(knowledge_text) > self.max_context_chars:
                capped_knowledge += "\n\n[... knowledge truncated for context window ...]"
                logger.info(
                    "synthesize_code: knowledge_text truncated from %d to %d chars",
                    len(knowledge_text), self.max_context_chars,
                )

        user_prompt = f"Approved Visual Plan (scenes.md):\n{capped_plan}\n\n"
        if capped_knowledge:
            user_prompt += f"Original Knowledge & Mathematical Formulas:\n{capped_knowledge}\n\n"
        if repair_error:
            repair_docs = "No additional documentation was available."
            try:
                from app.agents.tools.rag_tool import search_knowledge_base

                repair_docs = await search_knowledge_base(
                    query=f"ManimCE repair documentation for this compiler error: {repair_error[-2400:]}",
                    kb_collection_names=[settings.rag.collection_name],
                    top_k=5,
                )
            except Exception as exc:
                logger.warning("Repair documentation retrieval failed: %s", exc)
            user_prompt += (
                "\nThis is a repair request. Preserve the scene's teaching content, narration, "
                "VoiceoverScene, and timing. Fix the reported error with official ManimCE APIs. "
                "Never chain methods from get_part_by_tex unless the result is checked for None; "
                "for arrows, use a stable parent-mobject point or a known submobject reference.\n"
                f"Manim compiler traceback:\n{repair_error[-6000:]}\n\n"
                f"Retrieved Manim documentation:\n{repair_docs[:10000]}\n\n"
            )
        user_prompt += "Synthesize a complete, elegant Manim Community scene implementing this plan."

        llm_error: str | None = None
        raw_response = ""
        try:
            agent = hitl_agents.get_coder_agent(model_name, base_url, api_key)
            deps = hitl_agents.HitlCoderDeps(plan=capped_plan, knowledge_text=capped_knowledge, scene_name=scene_name)
            result = await agent.run(user_prompt, deps=deps)
            raw_response = getattr(result, "output", getattr(result, "data", "")) or ""
        except Exception as exc:
            llm_error = str(exc)
            logger.warning("Code synthesis agent failed: %s", llm_error)

        code, detected_scene = hitl_agents.extract_manim_code(
            raw_response, default_scene=scene_name or "GeneratedScene"
        )

        if not code or "def construct" not in code:
            if llm_error:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Code generation failed: {llm_error}",
                )
            code, detected_scene = self.generate_fallback_code(plan, knowledge_text)

        return VideoCodeResponse(code=code, scene_name=detected_scene)

    async def synthesize_stream(
        self,
        plan: str,
        knowledge_text: str | None = None,
        scene_name: str | None = None,
        *,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream Manim Community Edition code synthesis via SSE."""
        detected_scene = scene_name or "GeneratedScene"
        yield f"data: {json.dumps({'type': 'start', 'scene_name': detected_scene})}\n\n"
        yield f"data: {json.dumps({'type': 'status', 'message': 'Translating the visual plan into safe ManimCE code…'})}\n\n"

        capped_plan = plan[:self.max_context_chars]
        if len(plan) > self.max_context_chars:
            capped_plan += "\n\n[... plan truncated for context window ...]"

        capped_knowledge: str | None = None
        if knowledge_text:
            capped_knowledge = knowledge_text[:self.max_context_chars]
            if len(knowledge_text) > self.max_context_chars:
                capped_knowledge += "\n\n[... knowledge truncated for context window ...]"

        user_prompt = f"Approved Visual Plan (scenes.md):\n{capped_plan}\n\n"
        if capped_knowledge:
            user_prompt += f"Original Knowledge & Mathematical Formulas:\n{capped_knowledge}\n\n"
        user_prompt += "Synthesize a complete, elegant Manim Community scene implementing this plan."

        accumulated: list[str] = []
        stream_failed = False
        try:
            agent = hitl_agents.get_coder_agent(model_name, base_url, api_key)
            deps = hitl_agents.HitlCoderDeps(plan=capped_plan, knowledge_text=capped_knowledge, scene_name=detected_scene)
            async with agent.run_stream(user_prompt, deps=deps) as result:
                async for chunk in result.stream_text(delta=True):
                    accumulated.append(chunk)
                    yield f"data: {json.dumps({'type': 'token', 'token': chunk})}\n\n"
        except Exception as exc:
            logger.warning("Streaming code synthesis failed: %s", exc)
            stream_failed = True

        raw_response = "".join(accumulated).strip()
        code, detected_scene = hitl_agents.extract_manim_code(raw_response, default_scene=detected_scene)

        if stream_failed or not code or "def construct" not in code:
            yield f"data: {json.dumps({'type': 'status', 'message': 'Checking the generated scene and preparing a fallback if needed…'})}\n\n"
            fallback_code, detected_scene = self.generate_fallback_code(plan, knowledge_text)
            if not accumulated:
                chunk_size = 64
                for i in range(0, len(fallback_code), chunk_size):
                    chunk = fallback_code[i : i + chunk_size]
                    yield f"data: {json.dumps({'type': 'token', 'token': chunk})}\n\n"
                    await asyncio.sleep(0.01)
                code = fallback_code
            elif not code:
                code = fallback_code

        yield f"data: {json.dumps({'type': 'status', 'message': 'Manim scene code complete.'})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'code': code, 'scene_name': detected_scene})}\n\n"


# ── OOP Class 4: Code Repairer ────────────────────────────────────────────────

class ManimCodeRepairer:
    """Repairs existing Manim scenes in place against compiler and runtime tracebacks."""

    async def repair(
        self,
        code: str,
        error: str,
        scene_name: str | None = None,
        *,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> VideoCodeResponse:
        """Repair the current scene in place using targeted model calls and self-correction."""
        classified = classify_error(error)
        if not classified.is_repairable:
            logger.info(
                "Repair aborted: classified error is not repairable code-wise (%s): %s",
                classified.category,
                classified.user_message,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{classified.user_message} (Category: {classified.category.value})",
            )

        guidance = get_repair_guidance(classified)
        original = repair_manim_code(code)
        current_code = original.code
        preflight = preflight_manim_code(current_code)
        diagnostic_bundle = {
            "stage": "repair",
            "category": classified.category.value,
            "guidance": guidance,
            "runtime_or_compiler": error[-9000:],
            "static_findings": list(preflight.errors),
            "deterministic_repairs_already_applied": list(original.changes),
        }
        docs = "No additional documentation was available."
        try:
            from app.agents.tools.rag_tool import search_knowledge_base

            docs = await search_knowledge_base(
                query=f"ManimCE API repair for this runtime error: {error[-2400:]}",
                kb_collection_names=[settings.rag.collection_name],
                top_k=4,
            )
        except Exception as exc:
            logger.warning("Repair documentation retrieval failed: %s", exc)

        prompt = f"""Repair this existing Manim Community Edition source in place.

Diagnostic bundle (address every item in one pass; do not wait for the next render to discover obvious issues):
```json
{json.dumps(diagnostic_bundle, indent=2)[:18000]}
```

Targeted repair guidance:
{guidance}

Relevant Manim documentation:
{docs[:9000]}

Current source:
```python
{current_code[:36000]}
```

Rules:
- Return the complete corrected source in one python code block and nothing else.
- Make the smallest targeted change that fixes the reported error.
- Preserve all educational content, narration, VoiceoverScene, bookmarks, timing, and scene order.
- For Mobject indexing, never assume question[5] exists; use get_part_by_tex safely or a stable VGroup.
- For any MobjectIndexOutOfRange finding, inspect the supplied construction definition and repair both the
  construction and use site. Split MathTex/Tex into explicit arguments, use isolate=[...], or transform the
  whole mobject safely; do not just change the failing index without checking its intended visual meaning.
- Fix every static finding in the bundle, including all non-raw MathTex/Tex literals, unsupported methods,
  undefined names, and brittle indexes that can be out of range.
- Do not regenerate unrelated code or introduce new dependencies.
"""
        deps = hitl_agents.HitlRepairDeps(
            error=error,
            current_code=current_code,
            scene_name=scene_name,
            classified_error=classified,
            diagnostic_bundle=diagnostic_bundle,
        )

        try:
            agent = hitl_agents.get_repair_agent(model_name, base_url, api_key)
            repaired_code, detected_scene = await hitl_agents.run_repair_with_self_correction(
                agent=agent,
                prompt=prompt,
                deps=deps,
                max_attempts=2,
                timeout=90.0,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Manim repair agent timed out or failed: {exc}",
            ) from exc

        if not repaired_code or "def construct" not in repaired_code:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Repair agent returned incomplete Python source",
            )

        repaired_code = repair_manim_code(repaired_code).code
        preflight = preflight_manim_code(repaired_code)
        if not preflight.valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"stage": "repair_preflight", "status": "failed", "errors": list(preflight.errors)},
            )

        return VideoCodeResponse(code=repaired_code, scene_name=detected_scene)


# ── OOP Class 5: Render Engine ────────────────────────────────────────────────

class ManimRenderEngine:
    """Executes Manim scene compilation, captures diagnostics, and syncs media with storage."""

    def execute_render(
        self,
        code: str,
        scene_name: str,
        quality: Literal["l", "m", "h", "k"],
        workspace_dir: Path,
    ) -> tuple[Path | None, str]:
        """Render the Manim scene using the native Manim compiler or Docker fallback."""
        scene_file = workspace_dir / "scene.py"
        scene_file.write_text(code, encoding="utf-8")
        media_dir = workspace_dir / "media"
        media_dir.mkdir(parents=True, exist_ok=True)

        manim_bin = shutil.which("manim")
        if not manim_bin and Path("/app/.venv/bin/manim").exists():
            manim_bin = "/app/.venv/bin/manim"

        error_log = ""
        if manim_bin:
            cmd = [
                manim_bin,
                f"-q{quality}",
                "scene.py",
                scene_name,
                "--media_dir",
                str(media_dir),
            ]
            logger.info("Executing native Manim render: %s", " ".join(cmd))
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(workspace_dir),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=180,
                )
                logger.info("Native Manim render finished with code: %s", proc.returncode)
                if proc.returncode != 0:
                    error_log = (proc.stderr or proc.stdout or "")[-1500:]
                    logger.warning("Manim compile error: %s", error_log)
            except Exception as exc:
                logger.error("Native Manim execution failed: %s", exc)
                error_log = str(exc)
        else:
            docker_bin = shutil.which("docker")
            if docker_bin:
                vol_path = str(workspace_dir.resolve()).replace("\\", "/")
                cmd = [
                    docker_bin, "run", "--rm",
                    "-v", f"{vol_path}:/manim",
                    "manimcommunity/manim:latest",
                    "manim", f"-q{quality}", "scene.py", scene_name,
                    "--media_dir", "/manim/media",
                ]
                logger.info("Running Manim Docker render: %s", " ".join(cmd))
                try:
                    proc = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=180,
                    )
                    if proc.returncode != 0:
                        error_log = (proc.stderr or proc.stdout or "")[-1500:]
                except Exception as exc:
                    logger.error("Docker Manim render failed: %s", exc)
                    error_log = str(exc)
            else:
                error_log = "Neither native 'manim' nor 'docker' compiler was found on the system."

        # Search for resulting mp4
        candidates = list(workspace_dir.glob(f"media/videos/**/{scene_name}.mp4"))
        if candidates:
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return candidates[0], ""

        # Include LaTeX log diagnostics if available
        log_files = sorted(workspace_dir.rglob("*.log"), key=lambda p: p.stat().st_mtime)[-5:]
        for log_file in log_files:
            try:
                error_log += f"\n--- {log_file.name} (tail) ---\n{log_file.read_text(encoding='utf-8', errors='replace')[-6000:]}"
            except OSError:
                continue

        return None, error_log or "Animation video file was not generated by Manim."

    async def render_custom_code(
        self,
        code: str,
        scene_name: str | None,
        quality: Literal["l", "m", "h", "k"],
        user_id: UUID,
        db: AsyncSession,
        conversation_id: UUID | None = None,
        prompt: str | None = None,
        skip_preflight: bool = False,
    ) -> VideoRenderCustomResponse:
        """Compile and render user-approved Manim code, upload to MinIO/storage, and return playback info."""
        repair = repair_manim_code(code)
        effective_code = repair.code
        if repair.changes:
            logger.info("Applied deterministic Manim compatibility repairs: %s", "; ".join(repair.changes))

        if not skip_preflight:
            preflight = preflight_manim_code(effective_code)
            has_blocking = any(item.get("blocking", False) or item.get("severity", "error") == "error" for item in preflight.errors)
            has_warning = any(item.get("severity", "error") == "warning" for item in preflight.errors)
            if not preflight.valid or has_blocking or has_warning:
                diagnostic_bundle = {
                    "stage": "preflight",
                    "status": "failed" if has_blocking else "warning",
                    "blocking": has_blocking,
                    "errors": list(preflight.errors),
                    "issues": list(preflight.issues or preflight.errors),
                    "repair_changes": list(repair.changes),
                }
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=json.dumps(diagnostic_bundle),
                )

        effective_scene = "GeneratedScene"
        class_match = re.search(r"class\s+([A-Za-z0-9_]+)\s*\(", effective_code or "")
        if class_match:
            effective_scene = class_match.group(1)
        elif scene_name:
            effective_scene = scene_name

        gen_id = uuid4()
        temp_base = Path(tempfile.gettempdir()) / "aos_renders"
        temp_base.mkdir(parents=True, exist_ok=True)
        run_dir = temp_base / f"custom_{gen_id.hex[:10]}"
        run_dir.mkdir(parents=True, exist_ok=True)

        from app.db.models.conversation import Conversation
        from sqlalchemy import select

        conv_id = conversation_id
        if conv_id:
            existing_conv = await db.get(Conversation, conv_id)
            if not existing_conv:
                conv_id = None

        if not conv_id:
            res = await db.execute(
                select(Conversation.id).where(Conversation.user_id == user_id).limit(1)
            )
            found = res.scalar_one_or_none()
            if found:
                conv_id = found
            else:
                new_conv = Conversation(
                    id=uuid4(),
                    user_id=user_id,
                    title="Manim Studio Animation",
                )
                db.add(new_conv)
                await db.flush()
                conv_id = new_conv.id

        prompt_text = prompt or f"Custom Manim Scene: {effective_scene}"
        row = await video_repo.create(
            db,
            user_id=user_id,
            conversation_id=conv_id,
            prompt=prompt_text,
            mode="animate",
            status="running",
        )
        gen_id = row.id

        rendered_mp4, compile_err = await asyncio.to_thread(
            self.execute_render,
            effective_code,
            effective_scene,
            quality,
            run_dir,
        )

        minio_key = f"videos/{user_id}/{conv_id}/{gen_id}.mp4"
        code_key = f"videos/{user_id}/{conv_id}/{gen_id}.py"

        if rendered_mp4 and rendered_mp4.exists():
            final_local = run_dir / "final.mp4"
            try:
                final_local.write_bytes(rendered_mp4.read_bytes())
            except Exception:
                pass

            try:
                storage = get_video_storage()
                storage.upload_file(str(rendered_mp4), minio_key, content_type="video/mp4")
                code_file = run_dir / "scene.py"
                if code_file.exists():
                    storage.upload_file(str(code_file), code_key, content_type="text/plain")
            except Exception as exc:
                logger.warning("MinIO upload skipped (%s); local fallback active", exc)

            await video_repo.update(
                db,
                row,
                status="completed",
                minio_key=minio_key,
                code_minio_key=code_key,
                run_dir=str(run_dir.resolve()),
                progress_stage="completed",
                progress_message="Your animation is ready for review.",
            )
        else:
            err = f"Manim render failed: {compile_err or 'No output video produced.'}"
            await video_repo.update(
                db,
                row,
                status="failed",
                error_message=err,
                run_dir=str(run_dir.resolve()),
                progress_stage="failed",
                progress_message=err,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=err,
            )

        stream_url = f"/api/videos/{gen_id}/stream"
        return VideoRenderCustomResponse(
            video_generation_id=gen_id,
            status="completed",
            stream_url=stream_url,
            scene_name=effective_scene,
            quality=quality,
            code=effective_code,
        )


# ── OOP Class 6: Master Studio Facade ─────────────────────────────────────────

class ManimStudioService:
    """Master facade providing full-lifecycle Manim Studio capabilities."""

    def __init__(
        self,
        classifier: ManimTextClassifier | None = None,
        composer: ManimPlanComposer | None = None,
        synthesizer: ManimCodeSynthesizer | None = None,
        repairer: ManimCodeRepairer | None = None,
        renderer: ManimRenderEngine | None = None,
    ) -> None:
        self.classifier = classifier or ManimTextClassifier()
        self.composer = composer or ManimPlanComposer()
        self.synthesizer = synthesizer or ManimCodeSynthesizer()
        self.repairer = repairer or ManimCodeRepairer()
        self.renderer = renderer or ManimRenderEngine()

    def classify_heuristic(self, text: str) -> VideoClassifyResponse:
        return self.classifier.classify_heuristic(text)

    async def classify(
        self,
        text: str,
        *,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> VideoClassifyResponse:
        return await self.classifier.classify(
            text, model_name=model_name, base_url=base_url, api_key=api_key
        )

    def classify_sync(
        self,
        text: str,
        *,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> VideoClassifyResponse:
        return self.classifier.classify_sync(
            text, model_name=model_name, base_url=base_url, api_key=api_key
        )

    async def compose_plan(
        self,
        text: str,
        hints: str | None = None,
        *,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> VideoPlanResponse:
        return await self.composer.compose(
            text, hints=hints, model_name=model_name, base_url=base_url, api_key=api_key
        )

    async def compose_plan_stream(
        self,
        text: str,
        hints: str | None = None,
        *,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> AsyncGenerator[str, None]:
        async for chunk in self.composer.compose_stream(
            text, hints=hints, model_name=model_name, base_url=base_url, api_key=api_key
        ):
            yield chunk

    async def synthesize_code(
        self,
        plan: str,
        knowledge_text: str | None = None,
        scene_name: str | None = None,
        *,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        repair_error: str | None = None,
    ) -> VideoCodeResponse:
        return await self.synthesizer.synthesize(
            plan,
            knowledge_text=knowledge_text,
            scene_name=scene_name,
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            repair_error=repair_error,
        )

    async def synthesize_code_stream(
        self,
        plan: str,
        knowledge_text: str | None = None,
        scene_name: str | None = None,
        *,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> AsyncGenerator[str, None]:
        async for chunk in self.synthesizer.synthesize_stream(
            plan,
            knowledge_text=knowledge_text,
            scene_name=scene_name,
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
        ):
            yield chunk

    async def repair_code(
        self,
        code: str,
        error: str,
        scene_name: str | None = None,
        *,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> VideoCodeResponse:
        return await self.repairer.repair(
            code,
            error=error,
            scene_name=scene_name,
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
        )

    async def render_custom_code(
        self,
        code: str,
        scene_name: str | None,
        quality: Literal["l", "m", "h", "k"],
        user_id: UUID,
        db: AsyncSession,
        conversation_id: UUID | None = None,
        prompt: str | None = None,
        skip_preflight: bool = False,
    ) -> VideoRenderCustomResponse:
        return await self.renderer.render_custom_code(
            code=code,
            scene_name=scene_name,
            quality=quality,
            user_id=user_id,
            db=db,
            conversation_id=conversation_id,
            prompt=prompt,
            skip_preflight=skip_preflight,
        )


# Default Singleton Instance for Module-level Access
manim_studio_service = ManimStudioService()
manim_studio = manim_studio_service


# ── Backward-Compatible Module-Level Functions ────────────────────────────────

def _resolve_llm_config(
    api_key: str | None = None,
    base_url: str | None = None,
    model_name: str | None = None,
) -> tuple[str, str, str]:
    return hitl_agents._resolve_llm_config(
        api_key=api_key, base_url=base_url, model_name=model_name
    )


def classify_text_heuristic(text: str) -> VideoClassifyResponse:
    return manim_studio_service.classify_heuristic(text)


async def classify_text_for_manim(
    text: str,
    *,
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> VideoClassifyResponse:
    return await manim_studio_service.classify(
        text, model_name=model_name, base_url=base_url, api_key=api_key
    )


def classify_text_for_manim_sync(
    text: str,
    *,
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> VideoClassifyResponse:
    return manim_studio_service.classify_sync(
        text, model_name=model_name, base_url=base_url, api_key=api_key
    )


def _generate_fallback_plan(text: str, topic: str) -> str:
    return manim_studio_service.composer.generate_fallback_plan(text, topic)


def _generate_fallback_code(plan: str, knowledge_text: str | None = None) -> tuple[str, str]:
    return manim_studio_service.synthesizer.generate_fallback_code(plan, knowledge_text)


async def compose_plan_service(
    text: str,
    hints: str | None = None,
    *,
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> VideoPlanResponse:
    return await manim_studio_service.compose_plan(
        text, hints=hints, model_name=model_name, base_url=base_url, api_key=api_key
    )


async def compose_plan_stream_service(
    text: str,
    hints: str | None = None,
    *,
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> AsyncGenerator[str, None]:
    async for chunk in manim_studio_service.compose_plan_stream(
        text, hints=hints, model_name=model_name, base_url=base_url, api_key=api_key
    ):
        yield chunk


async def synthesize_code_service(
    plan: str,
    knowledge_text: str | None = None,
    scene_name: str | None = None,
    *,
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    repair_error: str | None = None,
) -> VideoCodeResponse:
    return await manim_studio_service.synthesize_code(
        plan,
        knowledge_text=knowledge_text,
        scene_name=scene_name,
        model_name=model_name,
        base_url=base_url,
        api_key=api_key,
        repair_error=repair_error,
    )


async def synthesize_code_stream_service(
    plan: str,
    knowledge_text: str | None = None,
    scene_name: str | None = None,
    *,
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> AsyncGenerator[str, None]:
    async for chunk in manim_studio_service.synthesize_code_stream(
        plan,
        knowledge_text=knowledge_text,
        scene_name=scene_name,
        model_name=model_name,
        base_url=base_url,
        api_key=api_key,
    ):
        yield chunk


async def repair_code_service(
    code: str,
    error: str,
    scene_name: str | None = None,
    *,
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> VideoCodeResponse:
    return await manim_studio_service.repair_code(
        code,
        error=error,
        scene_name=scene_name,
        model_name=model_name,
        base_url=base_url,
        api_key=api_key,
    )


def _execute_manim_render(
    code: str,
    scene_name: str,
    quality: Literal["l", "m", "h", "k"],
    workspace_dir: Path,
) -> tuple[Path | None, str]:
    return manim_studio_service.renderer.execute_render(
        code=code, scene_name=scene_name, quality=quality, workspace_dir=workspace_dir
    )


async def render_custom_code_service(
    code: str,
    scene_name: str | None,
    quality: Literal["l", "m", "h", "k"],
    user_id: UUID,
    db: AsyncSession,
    conversation_id: UUID | None = None,
    prompt: str | None = None,
    skip_preflight: bool = False,
) -> VideoRenderCustomResponse:
    return await manim_studio_service.render_custom_code(
        code=code,
        scene_name=scene_name,
        quality=quality,
        user_id=user_id,
        db=db,
        conversation_id=conversation_id,
        prompt=prompt,
        skip_preflight=skip_preflight,
    )
