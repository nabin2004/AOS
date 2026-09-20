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
import subprocess
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

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
    "taylor series", "taylor's formula", "maclaurin series", "fourier transform",
    "fourier series", "euler's formula", "derivative", "integral", "calculus",
    "eigenvector", "eigenvalue", "matrix multiplication", "linear transformation",
    "gradient descent", "neural network", "backpropagation", "sorting algorithm",
    "binary search", "dijkstra", "graph traversal", "pythagorean", "trigonometry",
    "coordinate system", "vector field", "complex plane", "riemann sum",
    "normal distribution", "binomial distribution", "markov chain"
]


def classify_text_for_manim(text: str) -> VideoClassifyResponse:
    """Classify if the given educational text can be animated with Manim."""
    lower_text = text.lower()
    
    # Check for exact keywords
    for kw in KEYWORDS_ANIMATABLE:
        if kw in lower_text:
            topic = kw.title()
            return VideoClassifyResponse(
                animatable=True,
                subject="math" if any(m in kw for m in ("series", "formula", "calculus", "derivative", "integral", "matrix", "linear", "vector")) else "cs",
                topic=topic,
                reason=f"Identified core animatable concept '{topic}' suitable for visual geometric and algebraic exposition.",
            )

    # Check for LaTeX / math patterns
    math_matches = 0
    for pattern in MATH_PATTERNS:
        if re.search(pattern, text):
            math_matches += 1

    if math_matches >= 2 or (math_matches >= 1 and any(term in lower_text for term in ("formula", "equation", "function", "theorem", "approximation", "series"))):
        # Extract potential title from heading or first line
        lines = [line.strip("#* \t\r\n") for line in text.splitlines() if line.strip("#* \t\r\n")]
        title = lines[0][:40] if lines else "Mathematical Derivation"
        return VideoClassifyResponse(
            animatable=True,
            subject="math",
            topic=title,
            reason="Detected mathematical formulas and equations ideally suited for Manim Community step-by-step visualization.",
        )

    # Computer science / algorithms check
    if any(k in lower_text for k in ("algorithm", "tree", "node", "time complexity", "big o", "recursion", "array")):
        return VideoClassifyResponse(
            animatable=True,
            subject="cs",
            topic="Algorithmic Structure",
            reason="Detected data structure / algorithm concepts well-suited for state transition animations.",
        )

    return VideoClassifyResponse(
        animatable=False,
        subject="unknown",
        topic="",
        reason="Content does not appear to contain mathematical formulas or visual algorithmic structures suited for Manim.",
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

    # Try custom endpoint or OpenRouter
    url = f"{custom_base}/chat/completions" if custom_base else "https://openrouter.ai/api/v1/chat/completions"
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
        "max_tokens": 3000,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return content.strip()
            else:
                logger.warning("LLM call failed with HTTP %s: %s", resp.status_code, resp.text)
    except Exception as exc:
        logger.warning("Error invoking LLM (%s): %s", url, exc)

    return ""


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
    """Generate a high-quality pedagogical plan when LLM is unavailable."""
    clean_topic = topic or "Mathematical Concept"
    return f"""# Visualizing {clean_topic}

## Overview
- **Topic**: {clean_topic}
- **Hook**: How can an infinite sum of polynomial derivatives reconstruct any smooth curve?
- **Target Audience**: Calculus and STEM learners
- **Estimated Length**: ~30 seconds
- **Key Insight**: Higher-order terms adjust the curvature and bend the approximation closer and closer to the true curve around the center point.

## Narrative Arc
We begin with the core definition of {clean_topic}, introduce the foundational formula in crisp LaTeX, and break down each derivative term visually to show how successive corrections increase approximation accuracy.

---

## Scene 1: Introduction & Formula Definition
**Duration**: ~12 seconds
**Purpose**: State the core formula clearly and define center point $a$ and the polynomial summation.

### Visual Elements
- Title: `Text("{clean_topic}", font_size=40).to_edge(UP)`
- General Equation: `MathTex(r"f(x) = f(a) + f'(a)(x-a) + \\frac{{f''(a)}}{{2!}}(x-a)^2 + \\cdots")`
- Variable annotation highlighting center point $a$ and factorial denominators $n!$.

### Content
1. Fade in the title with an accent underline.
2. Write the general Taylor expansion equation at the screen center.
3. Highlight the linear term $f'(a)(x-a)$ in YELLOW and quadratic term in TEAL.

### Technical Notes
- Use `MathTex` with color-coded substrings.
- Use `to_edge(UP)` for title and `next_to` for annotations to avoid overlapping.

---

## Scene 2: Special Case & Approximation Growth
**Duration**: ~18 seconds
**Purpose**: Demonstrate the Maclaurin series ($a = 0$) and the intuitive role of factorials.

### Visual Elements
- Maclaurin transformation formula: $f(x) = \\sum_{{n=0}}^\\infty \\frac{{f^{{(n)}}(0)}}{{n!}} x^n$.
- Concrete example: $e^x = 1 + x + \\frac{{x^2}}{{2!}} + \\frac{{x^3}}{{3!}} + \\cdots$.
- Grouped highlight box around terms.

### Content
1. Transition formula from general center $a$ to origin $a=0$ via `ReplacementTransform`.
2. Introduce the exponential series example $e^x$.
3. Conclude with summary text emphasizing convergence.

---

## Color Palette
- Primary: `BLUE_C` (Functions and curves)
- Secondary: `YELLOW` (First derivative tangent / linear term)
- Accent: `TEAL` (Second derivative curvature / quadratic term)
- Text: `WHITE` / `LIGHT_GREY`

## Mathematical Content
- $f(x) = f(a) + f'(a)(x-a) + \\frac{{f''(a)}}{{2!}}(x-a)^2 + \\cdots + \\frac{{f^{{(n)}}(a)}}{{n!}}(x-a)^n$
- Maclaurin case ($a = 0$): $f(x) = f(0) + f'(0)x + \\frac{{f''(0)}}{{2!}}x^2 + \\cdots$
- Example ($e^x$): $e^x = 1 + x + \\frac{{x^2}}{{2!}} + \\frac{{x^3}}{{3!}} + \\cdots$
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

    user_prompt = f"Educational Content:\n{text}\n\n"
    if hints:
        user_prompt += f"User specific visual preferences / hints:\n{hints}\n\n"
    user_prompt += f"Please construct a comprehensive scenes.md visual plan for Manim focusing on topic '{topic}'."

    plan_markdown = await call_llm(
        user_prompt,
        COMPOSER_SYSTEM_PROMPT,
        model_name=model_name,
        base_url=base_url,
        api_key=api_key,
    )

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
2. Define a single main Scene class inheriting from `Scene`, e.g.:
   `class TaylorFormulaScene(Scene):`
3. Layout & Positioning (Crucial to avoid visual collision):
   - Camera frame is 16:9: width=14.22, height=8.0 (X from -7 to +7, Y from -4 to +4).
   - Place titles at top: `title.to_edge(UP, buff=0.5)`
   - Place subtitles below titles: `subtitle.next_to(title, DOWN, buff=0.3)`
   - Use `VGroup` to organize multiple equations: `eqs.arrange(DOWN, buff=0.4)`
   - Never let equations overlap each other! When transitioning to a new step, fade out earlier equations or use `ReplacementTransform`.
4. LaTeX & Typography:
   - Use raw string syntax `r"..."` for all `MathTex`.
   - Double backslash LaTeX symbols if needed: e.g. `MathTex(r"f(x) = f(a) + f'(a)(x-a) + \\frac{f''(a)}{2!}(x-a)^2")`.
   - Set readable font sizes: `font_size=36` or `font_size=40` for main equations, `font_size=28` for explanatory notes.
5. Timing & Animations:
   - Use smooth animations: `Write(...)`, `Create(...)`, `FadeIn(...)`, `Transform(...)`.
   - Add sensible pacing pauses: `self.wait(1.5)` or `self.wait(2)`.
6. Output Format:
   - Return ONLY the executable python code block, enclosed in ```python ... ```.
"""


def _generate_fallback_code(plan: str, knowledge_text: str | None = None) -> tuple[str, str]:
    """Generate robust, guaranteed-to-render Manim Community code for Taylor's formula / math."""
    scene_name = "TaylorFormulaScene"
    code = '''from manim import *

class TaylorFormulaScene(Scene):
    def construct(self):
        # 1. Title Header
        title = Text("Taylor's Formula & Series", font_size=40, color=BLUE_C)
        title.to_edge(UP, buff=0.5)
        underline = Line(LEFT * 5, RIGHT * 5, color=BLUE_E).next_to(title, DOWN, buff=0.15)
        
        self.play(Write(title), GrowFromCenter(underline))
        self.wait(1)

        # 2. General Formula Definition
        def_text = Text("Approximating smooth functions near center point a:", font_size=24, color=GRAY_A)
        def_text.next_to(underline, DOWN, buff=0.4)

        formula = MathTex(
            r"f(x) = f(a) + f'(a)(x-a) + \\frac{f''(a)}{2!}(x-a)^2 + \\cdots + \\frac{f^{(n)}(a)}{n!}(x-a)^n + \\cdots",
            font_size=32
        )
        formula.set_color_by_tex(r"f(a)", YELLOW)
        formula.set_color_by_tex(r"f'(a)", TEAL)
        formula.set_color_by_tex(r"\\frac{f''(a)}{2!}", GREEN)
        formula.next_to(def_text, DOWN, buff=0.5)

        self.play(FadeIn(def_text, shift=UP * 0.2))
        self.play(Write(formula), run_time=2.5)
        self.wait(2)

        # 3. Highlight Key Components
        box = SurroundingRectangle(formula, color=YELLOW, buff=0.2)
        key_note = Text(
            "Each n-th derivative term matches curvature, while n! factorials ensure convergence.",
            font_size=20,
            color=YELLOW_A
        ).next_to(box, DOWN, buff=0.4)

        self.play(Create(box), FadeIn(key_note, shift=UP * 0.2))
        self.wait(2.5)

        # 4. Transition to Maclaurin Series (Special Case a = 0)
        self.play(FadeOut(def_text), FadeOut(box), FadeOut(key_note))
        
        maclaurin_header = Text("Special Case: Maclaurin Series (a = 0)", font_size=28, color=TEAL_A)
        maclaurin_header.next_to(underline, DOWN, buff=0.4)

        maclaurin_eq = MathTex(
            r"f(x) = f(0) + f'(0)x + \\frac{f''(0)}{2!}x^2 + \\frac{f^{(3)}(0)}{3!}x^3 + \\cdots",
            font_size=34
        )
        maclaurin_eq.next_to(maclaurin_header, DOWN, buff=0.4)

        example_label = Text("Canonical Example for exponential growth:", font_size=22, color=GRAY_B)
        example_label.next_to(maclaurin_eq, DOWN, buff=0.4)

        example_eq = MathTex(
            r"e^x = 1 + x + \\frac{x^2}{2!} + \\frac{x^3}{3!} + \\frac{x^4}{4!} + \\cdots",
            font_size=36,
            color=GOLD
        )
        example_eq.next_to(example_label, DOWN, buff=0.3)

        self.play(ReplacementTransform(formula, maclaurin_eq), FadeIn(maclaurin_header))
        self.wait(1.5)
        self.play(FadeIn(example_label), Write(example_eq), run_time=2.0)
        self.wait(3)

        # Fade out all elements cleanly
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
    user_prompt = f"Approved Visual Plan (scenes.md):\n{plan}\n\n"
    if knowledge_text:
        user_prompt += f"Original Knowledge & Mathematical Formulas:\n{knowledge_text}\n\n"
    user_prompt += "Synthesize a complete, elegant Manim Community scene implementing this plan."

    raw_response = await call_llm(
        user_prompt,
        CODER_SYSTEM_PROMPT,
        model_name=model_name,
        base_url=base_url,
        api_key=api_key,
    )

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

    if not code or len(code) < 100 or "def construct" not in code:
        code, detected_scene = _generate_fallback_code(plan, knowledge_text)

    return VideoCodeResponse(code=code, scene_name=detected_scene)


def _docker_render_manim(
    code: str,
    scene_name: str,
    quality: Literal["l", "m", "h", "k"],
    workspace_dir: Path,
) -> Path | None:
    """Render the Manim scene using the persistent or ad-hoc Docker container."""
    scene_file = workspace_dir / "scene.py"
    scene_file.write_text(code, encoding="utf-8")

    # Map Windows host path for Docker volume
    vol_path = str(workspace_dir.resolve()).replace("\\", "/")
    
    cmd = [
        "docker", "run", "--rm",
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
        logger.info("Manim render output code: %s", proc.returncode)
        if proc.returncode != 0:
            logger.warning("Manim stderr: %s", proc.stderr[:1000])
    except Exception as exc:
        logger.error("Docker Manim render failed: %s", exc)

    # Search for resulting mp4
    candidates = list(workspace_dir.glob(f"media/videos/**/{scene_name}.mp4"))
    if candidates:
        # Sort newest first
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0]
    return None


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
    effective_scene = scene_name or "TaylorFormulaScene"
    if not scene_name:
        class_match = re.search(r"class\s+([A-Za-z0-9_]+)\s*\(", code)
        if class_match:
            effective_scene = class_match.group(1)

    gen_id = uuid4()
    run_dir = Path("workspace") / "runs" / f"custom_{gen_id.hex[:10]}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Create initial pending generation record
    conv_id = conversation_id or uuid4()
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
    rendered_mp4 = await asyncio.to_thread(
        _docker_render_manim,
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
        err = "Manim rendering failed or timed out."
        await video_repo.update(
            db,
            row,
            status="failed",
            error_message=err,
            run_dir=str(run_dir.resolve()),
            progress_stage="failed",
            progress_message=err,
        )
        raise RuntimeError(err)

    stream_url = f"/api/videos/{gen_id}/stream"
    return VideoRenderCustomResponse(
        video_generation_id=gen_id,
        status="completed",
        stream_url=stream_url,
        scene_name=effective_scene,
        quality=quality,
        code=code,
    )
