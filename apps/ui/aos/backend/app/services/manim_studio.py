"""Interactive Manim Studio Service: Multi-stage human-in-the-loop pipeline.

Provides:
1. Classification: Checks if an explanation or knowledge text is animatable with Manim.
2. Plan Generation: Uses the manim-composer skill to generate structured scenes.md visual plans.
3. Code Generation: Uses the manimce-best-practices skill to synthesize valid Manim Community code.
4. Render Execution: Compiles and renders the Manim scene with user-selected quality (-ql, -qm, -qh, -qk).
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.openai_compatible_client import (
    build_openai_provider,
    normalize_endpoint_url,
)
from app.core.config import settings
from app.db.models.video_generation import VideoGeneration
from app.repositories import video_generation as video_repo
from app.schemas.video_generation import (
    VideoClassifyResponse,
    VideoCodeResponse,
    VideoPlanResponse,
    VideoRenderCustomResponse,
)
from app.services.video_storage import get_video_storage, video_object_key, code_object_key

logger = logging.getLogger(__name__)

# ── LLM generation limits ────────────────────────────────────────────────────
# Max output tokens the LLM is allowed to produce.
# NOTE: Small local models (e.g. Qwen3-8B via Ollama) have a total context
# window of ~8k-32k tokens (input + output combined).  Requesting 8k output
# on top of a 2k-3k prompt will cause the model to reject the request or
# silently produce garbage.  Keep this ≤ 3000 for local model compatibility;
# cloud models (OpenRouter) handle larger values fine.
MANIM_MAX_OUTPUT_TOKENS: int = 3_000

# Hard cap on the number of characters we forward as "knowledge_text" or
# "plan" context.  4 000 chars ≈ ~1 000 tokens — keeps the combined prompt
# well under the typical context window while leaving room for output.
MANIM_MAX_CONTEXT_CHARS: int = 4_000

# How many times to retry on transient HTTP errors (429 rate-limit, 503
# overload) before giving up.  Each attempt waits 2^attempt seconds.
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


def classify_text_for_manim(text: str) -> VideoClassifyResponse:
    """Classify if the given educational text can be animated with Manim.

    Falls back to extracting the topic from the first heading / first line
    when no keyword matches, so the LLM always gets a meaningful topic.
    """
    lower_text = text.lower()

    # Check for exact keywords
    for kw in KEYWORDS_ANIMATABLE:
        if kw in lower_text:
            topic = kw.title()
            is_math = any(m in kw for m in (
                "series", "formula", "calculus", "derivative", "integral",
                "matrix", "linear", "vector", "exponential", "logarithm",
                "probability", "distribution", "euler", "fourier",
            ))
            return VideoClassifyResponse(
                animatable=True,
                subject="math" if is_math else "cs",
                topic=topic,
                reason=f"Identified core animatable concept '{topic}'.",
            )

    # Check for LaTeX / math patterns
    math_matches = 0
    for pattern in MATH_PATTERNS:
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

    # Last resort: extract the first meaningful line as topic so we never
    # return an empty topic and fall into a generic fallback.
    lines = [line.strip("#* \t\r\n") for line in text.splitlines() if line.strip("#* \t\r\n")]
    if lines:
        title = lines[0][:60]
        return VideoClassifyResponse(
            animatable=True,
            subject="math",
            topic=title,
            reason="Extracted topic from content — treating as animatable educational material.",
        )

    return VideoClassifyResponse(
        animatable=False,
        subject="unknown",
        topic="",
        reason="Content does not appear to contain visual material suited for Manim.",
    )


async def call_llm(
    prompt: str,
    system_prompt: str,
    *,
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> str:
    """Call LLM provider (OpenRouter or user custom BYOK endpoint)."""
    import httpx

    custom_base = normalize_endpoint_url(base_url)
    key = (api_key or "").strip() or settings.OPENROUTER_API_KEY
    model = (model_name or "").strip() or settings.AI_MODEL or "openai/gpt-4o-mini"

    # Build the completions URL, being careful not to double-append the path
    # when custom_base already ends with /chat/completions.
    if custom_base:
        if custom_base.endswith("/chat/completions"):
            url = custom_base
        else:
            url = f"{custom_base.rstrip('/')}/chat/completions"
    else:
        url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if not custom_base:
        headers["HTTP-Referer"] = "https://aos.local"
        headers["X-Title"] = "AOS Manim Studio"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": MANIM_MAX_OUTPUT_TOKENS,
    }

    last_exc: Exception | None = None
    for attempt in range(LLM_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, headers=headers, json=payload)

            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices") or []
                if not choices:
                    raise RuntimeError("LLM returned no choices in response")
                content = choices[0]["message"]["content"]
                # Warn if the model stopped early due to token budget exhaustion
                finish_reason = choices[0].get("finish_reason", "stop")
                if finish_reason == "length":
                    logger.warning(
                        "LLM output was truncated (finish_reason=length). "
                        "Response may be incomplete. Consider raising MANIM_MAX_OUTPUT_TOKENS."
                    )
                return content.strip()

            # Retryable server-side errors
            if resp.status_code in (429, 500, 502, 503, 504):
                wait = 2 ** attempt
                logger.warning(
                    "LLM HTTP %s (attempt %d/%d); retrying in %ds — %s",
                    resp.status_code, attempt + 1, LLM_MAX_RETRIES, wait,
                    resp.text[:200],
                )
                await asyncio.sleep(wait)
                continue

            # Non-retryable client error (4xx except 429)
            error_body = resp.text[:500]
            logger.error("LLM call failed (non-retryable) HTTP %s: %s", resp.status_code, error_body)
            raise RuntimeError(f"LLM HTTP {resp.status_code}: {error_body}")

        except RuntimeError:
            raise
        except Exception as exc:
            last_exc = exc
            wait = 2 ** attempt
            logger.warning(
                "LLM network error (attempt %d/%d): %s; retrying in %ds",
                attempt + 1, LLM_MAX_RETRIES, exc, wait,
            )
            await asyncio.sleep(wait)

    raise RuntimeError(f"LLM call failed after {LLM_MAX_RETRIES} attempts: {last_exc}")


COMPOSER_SYSTEM_PROMPT = """\
You are an expert pedagogical animation director and Manim composer (following the manim-composer skill).
Your job is to transform educational knowledge into a comprehensive, scene-by-scene animation plan formatted as Markdown (scenes.md).

Requirements:
1. Target Audience: High-school/undergraduate learner seeking conceptual intuition and mathematical rigor.
2. Structure:
   # [Video Title]
   ## Overview
   - **Topic**: [Core concept]
   - **Hook**: [Opening question or surprising insight]
   - **Target Audience**: [Prerequisites]
   - **Estimated Length**: [e.g. 30-45 seconds]
   - **Key Insight**: [The "aha moment"]
   ## Narrative Arc
   [2-3 sentences explaining the visual progression]
   ---
   ## Scene 1: [Scene Name]
   **Duration**: ~10-15 seconds
   **Purpose**: [What is introduced]
   ### Visual Elements
   - [Mobjects, equations, coordinate axes]
   ### Content
   [Step-by-step description of visual transformations]
   ### Narration Notes
   [Key teaching ideas]
   ### Technical Notes
   - [Manim classes: MathTex, VGroup, Write, Transform, FadeIn]
   ---
   ## Scene 2: [Scene Name]
   ...
   ---
   ## Transitions & Flow
   [How scenes seamlessly flow into each other, cleaning up screen]
   ## Color Palette
   - Primary: BLUE_C
   - Secondary: YELLOW
   - Accent: TEAL
   - Background: #0f172a (Dark)
   ## Mathematical Content
   [List of precise LaTeX formulas to render]

Keep the output directly as clean Markdown with clear headings and bullet points.
"""


def _generate_fallback_plan(text: str, topic: str) -> str:
    """Generate a topic-aware pedagogical plan when LLM is unavailable."""
    clean_topic = topic or "Mathematical Concept"
    # Extract a short description hint from the first non-empty line of the source text
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


async def compose_plan_service(
    text: str,
    hints: str | None = None,
    *,
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> VideoPlanResponse:
    """Generate a structured scenes.md visual plan using manim-composer skills."""
    classification = classify_text_for_manim(text)
    topic = classification.topic or "Mathematical Concept"

    # Guard: truncate unbounded knowledge text so it doesn't overflow context window
    capped_text = text[:MANIM_MAX_CONTEXT_CHARS]
    if len(text) > MANIM_MAX_CONTEXT_CHARS:
        capped_text += "\n\n[... content truncated for context window ...]"
        logger.info(
            "compose_plan: knowledge_text truncated from %d to %d chars",
            len(text), MANIM_MAX_CONTEXT_CHARS,
        )

    user_prompt = f"Educational Content:\n{capped_text}\n\n"
    if hints:
        user_prompt += f"User specific visual preferences / hints:\n{hints}\n\n"
    user_prompt += f"Please construct a comprehensive scenes.md visual plan for Manim focusing on topic '{topic}'."

    try:
        plan_markdown = await call_llm(
            user_prompt,
            COMPOSER_SYSTEM_PROMPT,
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
        )
    except RuntimeError as exc:
        logger.warning("Plan LLM call failed (%s); using topic-aware fallback plan.", exc)
        plan_markdown = ""

    if not plan_markdown or len(plan_markdown.strip()) < 100:
        plan_markdown = _generate_fallback_plan(text, topic)

    return VideoPlanResponse(
        plan=plan_markdown,
        title=f"Visual Plan: {topic}",
        topic=topic,
    )


CODER_SYSTEM_PROMPT = """\
You are an expert Manim Community Edition coding agent (strictly following the manimce-best-practices skill).
Your job is to synthesize complete, bug-free, beautifully styled Python code using `from manim import *`.

CRITICAL MANIM RULES:
1. ONLY import from manim: `from manim import *`. Do not import nonexistent packages.
2. Name your Scene class after the topic in the plan (e.g. `class ExponentialEScene(Scene):`).
   NEVER name it TaylorFormulaScene unless the topic is literally Taylor's Formula.
3. Layout & Positioning (Crucial to avoid visual collision):
   - Camera frame is 16:9: width=14.22, height=8.0 (X from -7 to +7, Y from -4 to +4).
   - Place titles at top: `title.to_edge(UP, buff=0.5)`
   - Place subtitles below titles: `subtitle.next_to(title, DOWN, buff=0.3)`
   - Use `VGroup` to organize multiple equations: `eqs.arrange(DOWN, buff=0.4)`
   - Never let equations overlap each other! When transitioning to a new step, fade out earlier equations or use `ReplacementTransform`.
4. LaTeX & Typography:
   - Use raw string syntax `r"..."` for all `MathTex`.
   - Double backslash LaTeX symbols: e.g. `MathTex(r"e = \\lim_{n \\to \\infty}\\left(1+\\frac{1}{n}\\right)^n")`.
   - Set readable font sizes: `font_size=36` or `font_size=40` for main equations, `font_size=28` for explanatory notes.
5. Timing & Animations:
   - Use smooth animations: `Write(...)`, `Create(...)`, `FadeIn(...)`, `Transform(...)`.
   - Add sensible pacing pauses: `self.wait(1.5)` or `self.wait(2)`.
6. Output Format:
   - Return ONLY the executable python code block, enclosed in ```python ... ```.
   - The code must be self-contained and render with `manim -ql scene.py <ClassName>`.
"""


def _generate_fallback_code(plan: str, knowledge_text: str | None = None) -> tuple[str, str]:
    """Generate a topic-aware minimal Manim scene when LLM code generation fails."""
    # Derive topic from the plan header or knowledge text
    topic = "Mathematical Concept"
    if plan:
        header_match = re.search(r"^#\s+(.+)$", plan, re.MULTILINE)
        if header_match:
            topic = header_match.group(1).strip().replace("Visualizing ", "")
    elif knowledge_text:
        first = [l.strip() for l in knowledge_text.splitlines() if l.strip()]
        if first:
            topic = first[0][:60]

    # Build a safe class name from the topic
    safe_name = re.sub(r"[^A-Za-z0-9]", "", topic.title().replace(" ", ""))
    if not safe_name or not safe_name[0].isalpha():
        safe_name = "TopicScene"
    scene_name = f"{safe_name}Scene"

    # Escape the topic for use in Python string literals
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


async def synthesize_code_service(
    plan: str,
    knowledge_text: str | None = None,
    scene_name: str | None = None,
    *,
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> VideoCodeResponse:
    """Generate Manim Community Edition code from the approved visual plan."""
    # Guard: cap plan size — it can be huge if the composer returned a long markdown
    capped_plan = plan[:MANIM_MAX_CONTEXT_CHARS]
    if len(plan) > MANIM_MAX_CONTEXT_CHARS:
        capped_plan += "\n\n[... plan truncated for context window ...]"
        logger.info("synthesize_code: plan truncated from %d to %d chars", len(plan), MANIM_MAX_CONTEXT_CHARS)

    # Guard: cap knowledge_text separately (combined budget = 2 × MANIM_MAX_CONTEXT_CHARS)
    capped_knowledge: str | None = None
    if knowledge_text:
        capped_knowledge = knowledge_text[:MANIM_MAX_CONTEXT_CHARS]
        if len(knowledge_text) > MANIM_MAX_CONTEXT_CHARS:
            capped_knowledge += "\n\n[... knowledge truncated for context window ...]"
            logger.info(
                "synthesize_code: knowledge_text truncated from %d to %d chars",
                len(knowledge_text), MANIM_MAX_CONTEXT_CHARS,
            )

    user_prompt = f"Approved Visual Plan (scenes.md):\n{capped_plan}\n\n"
    if capped_knowledge:
        user_prompt += f"Original Knowledge & Mathematical Formulas:\n{capped_knowledge}\n\n"
    user_prompt += "Synthesize a complete, elegant Manim Community scene implementing this plan."

    llm_error: str | None = None
    try:
        raw_response = await call_llm(
            user_prompt,
            CODER_SYSTEM_PROMPT,
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
        )
    except RuntimeError as exc:
        llm_error = str(exc)
        raw_response = ""
        logger.warning("Code synthesis LLM call failed: %s", llm_error)

    code = ""
    detected_scene = scene_name or "GeneratedScene"

    if raw_response:
        code_match = re.search(r"```python\s*([\s\S]+?)\s*```", raw_response)
        if code_match:
            code = code_match.group(1).strip()
        elif "class " in raw_response and "Scene" in raw_response:
            code = raw_response.strip()

    if code:
        class_match = re.search(r"class\s+([A-Za-z0-9_]+)\s*\((?:ThreeDScene|Scene|MovingCameraScene)", code)
        if class_match:
            detected_scene = class_match.group(1)

    # Only fall back if we truly got no usable code (not just short responses)
    if not code or "def construct" not in code:
        if llm_error:
            # Surface the real error to the frontend so the user knows what happened
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Code generation failed: {llm_error}",
            )
        code, detected_scene = _generate_fallback_code(plan, knowledge_text)

    return VideoCodeResponse(code=code, scene_name=detected_scene)


def _execute_manim_render(
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
    # Check venv manim if in container
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
        # Fallback to docker if available on host
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
        # Sort newest first
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0], ""
    return None, error_log or "Animation video file was not generated by Manim."


async def render_custom_code_service(
    code: str,
    scene_name: str | None,
    quality: Literal["l", "m", "h", "k"],
    user_id: UUID,
    db: AsyncSession,
    conversation_id: UUID | None = None,
    prompt: str | None = None,
) -> VideoRenderCustomResponse:
    """Compile and render user-approved Manim code, upload to MinIO/storage, and return playback info."""
    # Derive effective scene name from the code itself first, then the
    # explicit parameter, falling back to a generic name.  Never hard-code
    # TaylorFormulaScene as the default.
    effective_scene = "GeneratedScene"
    class_match = re.search(r"class\s+([A-Za-z0-9_]+)\s*\(", code or "")
    if class_match:
        effective_scene = class_match.group(1)
    elif scene_name:
        effective_scene = scene_name

    gen_id = uuid4()
    # Create run dir in OS temp directory to avoid triggering Uvicorn WatchFiles reloader
    temp_base = Path(tempfile.gettempdir()) / "aos_renders"
    temp_base.mkdir(parents=True, exist_ok=True)
    run_dir = temp_base / f"custom_{gen_id.hex[:10]}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Ensure a valid conversation exists for this user to satisfy foreign key constraint
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

    # Execute rendering in threadpool to keep async loop responsive
    rendered_mp4, compile_err = await asyncio.to_thread(
        _execute_manim_render,
        code,
        effective_scene,
        quality,
        run_dir,
    )

    minio_key = f"videos/{user_id}/{conv_id}/{gen_id}.mp4"
    code_key = f"videos/{user_id}/{conv_id}/{gen_id}.py"

    if rendered_mp4 and rendered_mp4.exists():
        # Copy to run_dir root as final.mp4 for fallback local stream
        final_local = run_dir / "final.mp4"
        try:
            final_local.write_bytes(rendered_mp4.read_bytes())
        except Exception:
            pass

        # Upload to MinIO storage if available
        try:
            storage = get_video_storage()
            storage.upload_file(str(rendered_mp4), minio_key, content_type="video/mp4")
            
            # Also upload code
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
        # Failed to render
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
        code=code,
    )

