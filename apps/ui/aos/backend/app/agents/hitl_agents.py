"""Human-In-The-Loop (HITL) Pydantic AI Agents for Manim Studio.

Provides robust, typed, self-correcting agents for:
1. Composer Agent: Generates scenes.md visual plans from educational text.
2. Coder Agent: Synthesizes clean Manim Community Edition code with syntax validation.
3. Repair Agent: In-place code repair leveraging error classification and RAG tools.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import json
import logging
import re
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from app.agents.error_classifier import ClassifiedError, classify_error, get_repair_guidance
from app.agents.openai_compatible_client import build_openai_provider
from app.services.manim_code import preflight_manim_code, repair_manim_code

logger = logging.getLogger(__name__)


# ── Dependency Contexts ───────────────────────────────────────────────────────

@dataclass
class HitlPlanDeps:
    """Runtime dependencies for the Composer Agent."""
    topic: str
    hints: str | None = None
    source_text: str | None = None


@dataclass
class HitlCoderDeps:
    """Runtime dependencies for the Coder Agent."""
    plan: str
    knowledge_text: str | None = None
    scene_name: str | None = None


@dataclass
class HitlRepairDeps:
    """Runtime dependencies for the Repair Agent."""
    error: str
    current_code: str
    scene_name: str | None = None
    classified_error: ClassifiedError | None = None
    diagnostic_bundle: dict[str, Any] = field(default_factory=dict)


# ── System Prompts ────────────────────────────────────────────────────────────

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

REPAIR_SYSTEM_PROMPT = """\
You are a senior Manim Community Edition repair engineer.
Your job is to repair an existing Manim scene in place against compiler and runtime tracebacks.

CRITICAL REPAIR RULES:
1. Fix the reported error in place. Do NOT redesign or discard existing narration, timing, VoiceoverScene, or structure.
2. Return ONLY the complete corrected Python code inside a ```python ... ``` block.
3. Make the smallest targeted change that completely resolves the diagnostic traceback.
4. Mobject Indexing Safeguards:
   - Never assume index existence (e.g., `formula[5]` or `eq[2]`).
   - If an index fails, inspect the construction. Split MathTex/Tex into explicit substring arguments, use `isolate=[...]`, or reference stable sub-elements via `get_part_by_tex`.
5. LaTeX Safety:
   - Use raw string literals `r"..."` for all `MathTex` / `Tex`.
   - Never use external LaTeX packages that are absent from the standard Manim environment.
6. Method Compatibility:
   - Use only official Manim Community Edition (v0.18+) APIs. Never use legacy ManimCairo or ManimGL methods.
7. Address all static validation findings in the diagnostic bundle in a single pass.
"""


# ── Code Extraction & Normalization ──────────────────────────────────────────

def extract_manim_code(raw_response: str, default_scene: str = "GeneratedScene") -> tuple[str, str]:
    """Extract clean Python Manim code and detect the primary Scene class name.

    Handles markdown fences, bare code, and various Scene inheritance forms.
    Returns (code, scene_name).
    """
    raw = (raw_response or "").strip()
    code = ""

    # Try fenced code block: ```python ... ``` or ```py ... ``` or generic ``` ... ```
    match = re.search(r"```(?:python|py)?\s*([\s\S]+?)\s*```", raw, re.IGNORECASE)
    if match:
        code = match.group(1).strip()
    elif "class " in raw and "def construct" in raw:
        code = raw

    # Ensure essential imports exist if missing
    if code and "from manim import *" not in code:
        code = f"from manim import *\n\n{code}"

    # Detect scene class name
    detected_scene = default_scene
    class_match = re.search(
        r"class\s+([A-Za-z0-9_]+)\s*\((?:ThreeDScene|MovingCameraScene|VoiceoverScene|ZoomedScene|LinearTransformationScene|Scene)",
        code,
    )
    if class_match:
        detected_scene = class_match.group(1)

    return code, detected_scene


# ── Native Tools ──────────────────────────────────────────────────────────────

async def validate_syntax_tool(ctx: RunContext[Any], code: str) -> dict[str, Any]:
    """Validate Manim Community Python source for syntax and static compatibility errors."""
    preflight = preflight_manim_code(code)
    return {
        "valid": preflight.valid,
        "errors": list(preflight.errors),
        "scene_classes": list(preflight.scene_classes),
    }


async def search_manim_docs_tool(ctx: RunContext[Any], query: str) -> str:
    """Search ManimCE documentation and community examples for API usage and repair hints."""
    try:
        from app.agents.tools.rag_tool import search_knowledge_base
        from app.core.config import settings

        results = await search_knowledge_base(
            query=query,
            kb_collection_names=[settings.rag.collection_name],
            top_k=4,
        )
        return results or "No additional documentation found."
    except Exception as exc:
        logger.debug("search_manim_docs_tool retrieval skipped: %s", exc)
        return "Documentation search unavailable in current environment."


# ── Model Builder ─────────────────────────────────────────────────────────────

def _resolve_llm_config(
    api_key: str | None = None,
    base_url: str | None = None,
    model_name: str | None = None,
) -> tuple[str, str, str]:
    """Resolve key, endpoint url, and model name using env fallbacks."""
    import os
    from app.core.config import settings

    key = (
        api_key
        or getattr(settings, "OPENROUTER_API_KEY", None)
        or os.getenv("OPENROUTER_API_KEY")
        or getattr(settings, "OPENAI_API_KEY", None)
        or os.getenv("OPENAI_API_KEY")
        or "sk-local"
    )

    custom_base = (
        base_url
        or getattr(settings, "OPENROUTER_BASE_URL", None)
        or os.getenv("OPENROUTER_BASE_URL")
        or getattr(settings, "OPENAI_BASE_URL", None)
        or os.getenv("OPENAI_BASE_URL")
    )

    model = (
        model_name
        or getattr(settings, "AOS_STUDIO_DEFAULT_MODEL", None)
        or os.getenv("AOS_STUDIO_DEFAULT_MODEL")
        or getattr(settings, "OPENAI_MODEL_NAME", None)
        or os.getenv("OPENAI_MODEL_NAME")
    )

    if not model or model == "nabin2004/AOS-qwen3-8b-grpo":
        model = "nex-agi/nex-n2.5-pro:free"

    if custom_base:
        if custom_base.endswith("/chat/completions"):
            url = custom_base
        else:
            url = f"{custom_base.rstrip('/')}/chat/completions"
    else:
        url = "https://openrouter.ai/api/v1/chat/completions"

    return key, url, model


def build_hitl_model(
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
):
    """Build a Pydantic AI model using the HITL fallback resolver logic."""
    key, url, primary_model = _resolve_llm_config(
        api_key=api_key, base_url=base_url, model_name=model_name
    )

    if "openrouter.ai" in url:
        return OpenRouterModel(
            primary_model,
            provider=OpenRouterProvider(api_key=key),
        )
    else:
        base = url
        if base.endswith("/chat/completions"):
            base = base[:-17]
        return OpenAIChatModel(
            primary_model,
            provider=build_openai_provider(base, key or "sk-local"),
        )


# ── Agent Factory Functions ───────────────────────────────────────────────────

def get_composer_agent(
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> Agent[HitlPlanDeps | None, str]:
    """Get the Pydantic AI agent for composing scenes.md plans."""
    model = build_hitl_model(model_name, base_url, api_key)
    return Agent(
        model=model,
        system_prompt=COMPOSER_SYSTEM_PROMPT,
        name="hitl_composer_agent",
        deps_type=HitlPlanDeps | None,
    )


def get_coder_agent(
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> Agent[HitlCoderDeps | None, str]:
    """Get the Pydantic AI agent for synthesizing Manim code."""
    model = build_hitl_model(model_name, base_url, api_key)
    agent = Agent(
        model=model,
        system_prompt=CODER_SYSTEM_PROMPT,
        name="hitl_coder_agent",
        deps_type=HitlCoderDeps | None,
        retries=2,
    )
    agent.tool(validate_syntax_tool)
    return agent


def get_repair_agent(
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> Agent[HitlRepairDeps | None, str]:
    """Get the Pydantic AI agent for repairing existing Manim code."""
    model = build_hitl_model(model_name, base_url, api_key)
    agent = Agent(
        model=model,
        system_prompt=REPAIR_SYSTEM_PROMPT,
        name="hitl_repair_agent",
        deps_type=HitlRepairDeps | None,
        retries=2,
    )
    agent.tool(validate_syntax_tool)
    agent.tool(search_manim_docs_tool)
    return agent


# ── Self-Correcting Execution Runners ──────────────────────────────────────────

async def run_repair_with_self_correction(
    agent: Agent[HitlRepairDeps | None, str],
    prompt: str,
    deps: HitlRepairDeps | None = None,
    max_attempts: int = 2,
    timeout: float = 90.0,
) -> tuple[str, str]:
    """Run the repair agent with preflight validation and automated self-correction loop.

    Returns (repaired_code, detected_scene).
    """
    current_prompt = prompt
    message_history = None

    for attempt in range(max_attempts):
        logger.info("Executing repair agent pass %d/%d", attempt + 1, max_attempts)
        if message_history:
            result = await asyncio.wait_for(
                agent.run(current_prompt, message_history=message_history, deps=deps),
                timeout=timeout,
            )
        else:
            result = await asyncio.wait_for(
                agent.run(current_prompt, deps=deps),
                timeout=timeout,
            )

        raw_output = result.data
        code, scene_name = extract_manim_code(
            raw_output, default_scene=(deps.scene_name if deps else "GeneratedScene")
        )

        if not code or "def construct" not in code:
            logger.warning("Repair pass %d returned incomplete code", attempt + 1)
            if attempt == max_attempts - 1:
                return code, scene_name
            current_prompt = "Your output did not include a valid Manim Scene with `def construct(self):`. Please provide the full Python script."
            message_history = result.all_messages()
            continue

        # Apply deterministic repairs first
        code = repair_manim_code(code).code
        preflight = preflight_manim_code(code)

        if preflight.valid:
            logger.info("Repair pass %d succeeded with valid preflight", attempt + 1)
            return code, scene_name

        # If invalid and we have attempts remaining, feed findings back
        if attempt < max_attempts - 1:
            logger.info("Preflight errors found (%s); requesting agent self-correction", list(preflight.errors))
            current_prompt = (
                f"The repaired code still has static syntax/validation errors:\n"
                f"{json.dumps(list(preflight.errors), indent=2)}\n\n"
                "Please fix these specific errors and return the complete corrected code in a ```python ... ``` block."
            )
            message_history = result.all_messages()
        else:
            logger.warning("Preflight errors remain after %d attempts: %s", max_attempts, list(preflight.errors))
            return code, scene_name

    return code, scene_name
