"""Human-In-The-Loop (HITL) Pydantic AI Agents for Manim Studio.

Class-based, object-oriented architecture providing typed, self-correcting agents for:
1. Classifier: Analyzes educational text for Manim animatability.
2. Composer: Generates scenes.md visual plans from educational text.
3. Coder: Synthesizes clean Manim Community Edition code with syntax validation.
4. Repair: In-place code repair leveraging error classification and RAG tools.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import json
import logging
import os
from pathlib import Path
import re
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from app.agents.error_classifier import ClassifiedError, classify_error, get_repair_guidance
from app.agents.openai_compatible_client import (
    build_openai_provider,
    normalize_endpoint_url,
)
from app.core.config import settings
from app.schemas.video_generation import VideoClassifyResponse
from app.services.manim_code import preflight_manim_code, repair_manim_code
from app.skills import (
    get_composer_skills,
    get_coder_skills,
    get_repair_skills,
)

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

CLASSIFIER_SYSTEM_PROMPT = """\
You are an expert pedagogical director and Manim visual animatability classifier for AOS.
Your task is to analyze educational text and determine if it can and should be visualized/animated using Manim (Mathematical Animation Engine).

Evaluate the content and return structured output matching the schema:
1. `animatable` (boolean):
   - True: The text contains mathematical formulas, theorems, calculus, linear algebra, geometry, algorithms, data structures, machine learning concepts, physics dynamics, or step-by-step conceptual derivations that strongly benefit from dynamic 2D/3D programmatic animation.
   - False: The content is primarily biographical, historical narrative, general prose, conversational dialogue, or non-visual text unsuitable for Manim.
2. `subject` (string):
   - "math": Calculus, linear algebra, geometry, probability, statistics, trigonometry, analysis, discrete math.
   - "cs": Algorithms, data structures, graph theory, automata, networking, systems, complexity theory.
   - "ai": Machine learning, deep learning, backpropagation, optimization, neural networks, transformers, RL.
   - "physics": Mechanics, electromagnetism, optics, waves, quantum representations.
   - "unknown": Out of domain or non-animatable content.
3. `topic` (string):
   - A clean, concise 2-6 word title-cased topic name (e.g. "Taylor Series Approximation", "Binary Search Algorithm", "Fourier Transform").
   - Do NOT include conversational prefixes like "Introduction to", "Explain", "How does", or trailing punctuation.
   - If non-animatable, leave as empty string or a general subject label.
4. `reason` (string):
   - A concise 1-2 sentence explanation detailing why the content is or is not suited for Manim, highlighting visual elements (e.g., equations, geometric plots, node diagrams).
"""

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


# ── OOP Class: LLM Config & Model Resolver ───────────────────────────────────

class HitlLLMResolver:
    """Resolves LLM endpoints, API keys, and model names with fallback strategies."""

    DEFAULT_FALLBACK_MODEL = "nex-agi/nex-n2.5-pro:free"
    DEFAULT_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

    def resolve(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model_name: str | None = None,
    ) -> tuple[str, str, str]:
        """Resolve key, endpoint url, and model name using environment fallbacks."""
        key = (api_key or "").strip()
        if not key:
            key = (
                getattr(settings, "OPENROUTER_API_KEY", "")
                or os.getenv("OPENROUTER_API_KEY", "").strip()
                or os.getenv("AOS_OPENAI_API_KEY", "").strip()
                or getattr(settings, "OPENAI_API_KEY", "")
                or os.getenv("OPENAI_API_KEY", "").strip()
            )
        if not key:
            # Scan .env files in priority order.  Check AOS_ENV_FILE override
            # first so any deployment layout can opt out of positional guessing.
            env_file_override = os.getenv("AOS_ENV_FILE", "").strip()
            env_candidates: list[Path] = []
            if env_file_override:
                env_candidates.append(Path(env_file_override))
            env_candidates.extend([
                Path(__file__).resolve().parents[6] / "apps" / "agents" / ".env",
                Path(__file__).resolve().parents[5] / "apps" / "agents" / ".env",
                Path("/app/apps/agents/.env"),
                Path(__file__).resolve().parents[3] / "agents" / ".env",
                Path("../agents/.env"),
            ])
            for candidate in env_candidates:
                if candidate.exists():
                    try:
                        for line in candidate.read_text(encoding="utf-8").splitlines():
                            line_str = line.strip()
                            if line_str.startswith("OPENROUTER_API_KEY="):
                                key = line_str.split("=", 1)[1].strip().strip('"').strip("'")
                                break
                            elif line_str.startswith("AOS_OPENAI_API_KEY="):
                                key = line_str.split("=", 1)[1].strip().strip('"').strip("'")
                        if key:
                            break
                    except Exception:
                        pass
        if not key:
            raise ValueError(
                "No API key found. Set OPENROUTER_API_KEY, AOS_OPENAI_API_KEY, or OPENAI_API_KEY "
                "in the environment, in app settings, or point AOS_ENV_FILE to a .env file "
                "containing one of those keys."
            )

        custom_base = normalize_endpoint_url(base_url)
        if not custom_base:
            env_base = (
                getattr(settings, "AOS_OPENAI_BASE_URL", "")
                or os.getenv("AOS_OPENAI_BASE_URL", "")
                or getattr(settings, "OPENAI_BASE_URL", "")
                or os.getenv("OPENAI_BASE_URL", "")
            )
            if env_base and "modal.direct" not in env_base:
                custom_base = normalize_endpoint_url(env_base)

        model = (model_name or "").strip()
        if not model:
            model = (
                getattr(settings, "AI_MODEL", "")
                or os.getenv("AOS_OPENAI_MODEL", "")
                or os.getenv("AI_MODEL", "")
                or getattr(settings, "AOS_STUDIO_DEFAULT_MODEL", "")
                or os.getenv("AOS_STUDIO_DEFAULT_MODEL", "")
                or getattr(settings, "OPENAI_MODEL_NAME", "")
                or os.getenv("OPENAI_MODEL_NAME", "")
            )

        if not model or model == "nabin2004/AOS-qwen3-8b-grpo":
            model = self.DEFAULT_FALLBACK_MODEL

        if custom_base:
            if custom_base.endswith("/chat/completions"):
                url = custom_base
            else:
                url = f"{custom_base.rstrip('/')}/chat/completions"
        else:
            url = self.DEFAULT_OPENROUTER_URL

        return key, url, model

    def build_model(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> OpenRouterModel | OpenAIChatModel:
        """Construct a concrete Pydantic AI Model instance."""
        key, url, primary_model = self.resolve(
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


# ── OOP Class: Code Extractor & Normalizer ────────────────────────────────────

class HitlCodeExtractor:
    """Extracts, validates, and normalizes Python Manim code from model responses."""

    CODE_BLOCK_PATTERN = re.compile(r"```(?:python|py)?\s*([\s\S]+?)\s*```", re.IGNORECASE)
    # Match a Scene subclass regardless of where the known Scene base appears
    # in the inheritance list (first position, second, etc.).  The original
    # pattern only anchored on the *first* base, so ``class Foo(Mixin, Scene):``
    # would not match.
    SCENE_CLASS_PATTERN = re.compile(
        r"class\s+([A-Za-z0-9_]+)\s*\("
        r"(?:[A-Za-z0-9_,\s]*?)"
        r"(?:ThreeDScene|MovingCameraScene|VoiceoverScene|ZoomedScene|LinearTransformationScene|Scene)"
        r"(?:[A-Za-z0-9_,\s]*?)\)"
    )

    def extract(self, raw_response: str, default_scene: str = "GeneratedScene") -> tuple[str, str]:
        """Extract clean Python Manim code and detect the primary Scene class name.

        Handles markdown fences, bare code, and various Scene inheritance forms.
        Returns (code, scene_name).
        """
        raw = (raw_response or "").strip()
        code = ""

        match = self.CODE_BLOCK_PATTERN.search(raw)
        if match:
            code = match.group(1).strip()
        elif "class " in raw and "def construct" in raw:
            code = raw

        if code and "from manim import *" not in code:
            code = f"from manim import *\n\n{code}"

        detected_scene = default_scene
        class_match = self.SCENE_CLASS_PATTERN.search(code)
        if class_match:
            detected_scene = class_match.group(1)

        return code, detected_scene


    extract_code = extract

# ── OOP Class: Native Agent Tools ─────────────────────────────────────────────

class HitlAgentTools:
    """Reusable tools attached to HITL Pydantic AI agents."""

    @staticmethod
    def validate_syntax(code: str) -> dict[str, Any]:
        """Validate Manim Community Python source for syntax and static compatibility errors."""
        preflight = preflight_manim_code(code)
        return {
            "valid": preflight.valid,
            "errors": list(preflight.errors),
        }

    @staticmethod
    async def validate_syntax_tool(ctx: RunContext[Any], code: str) -> dict[str, Any]:
        """Tool wrapper for Pydantic AI agents to validate syntax."""
        return HitlAgentTools.validate_syntax(code)

    @staticmethod
    async def search_manim_docs_tool(ctx: RunContext[Any], query: str) -> str:
        """Search ManimCE documentation and community examples for API usage and repair hints."""
        try:
            from app.agents.tools.rag_tool import search_knowledge_base

            results = await search_knowledge_base(
                query=query,
                kb_collection_names=[settings.rag.collection_name],
                top_k=4,
            )
            return results or "No additional documentation found."
        except Exception as exc:
            logger.debug("search_manim_docs_tool retrieval skipped: %s", exc)
            return "Documentation search unavailable in current environment."


# ── OOP Class: HITL Agent Factory ─────────────────────────────────────────────

class HitlAgentFactory:
    """Factory responsible for instantiating and configuring specialized HITL agents."""

    def __init__(
        self,
        resolver: HitlLLMResolver | None = None,
        tools: HitlAgentTools | None = None,
    ) -> None:
        self.resolver = resolver or HitlLLMResolver()
        self.tools = tools or HitlAgentTools()

    def create_classifier_agent(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        *,
        capabilities: list[Any] | None = None,
    ) -> Agent[None, VideoClassifyResponse]:
        """Create the Pydantic AI agent for classifying text animatability for Manim."""
        model = self.resolver.build_model(model_name, base_url, api_key)
        return Agent(
            model=model,
            system_prompt=CLASSIFIER_SYSTEM_PROMPT,
            name="hitl_classifier_agent",
            output_type=VideoClassifyResponse,
            capabilities=capabilities,
            retries=2,
        )

    def create_composer_agent(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        *,
        capabilities: list[Any] | None = None,
    ) -> Agent[HitlPlanDeps | None, str]:
        """Create the Pydantic AI agent for composing scenes.md plans with the manim-composer skill."""
        model = self.resolver.build_model(model_name, base_url, api_key)
        caps = [get_composer_skills()] if capabilities is None else capabilities
        return Agent(
            model=model,
            system_prompt=COMPOSER_SYSTEM_PROMPT,
            name="hitl_composer_agent",
            deps_type=HitlPlanDeps | None,
            capabilities=caps,
        )

    def create_coder_agent(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        *,
        capabilities: list[Any] | None = None,
    ) -> Agent[HitlCoderDeps | None, str]:
        """Create the Pydantic AI agent for synthesizing Manim code with manimce-best-practices skill."""
        model = self.resolver.build_model(model_name, base_url, api_key)
        caps = [get_coder_skills()] if capabilities is None else capabilities
        agent = Agent(
            model=model,
            system_prompt=CODER_SYSTEM_PROMPT,
            name="hitl_coder_agent",
            deps_type=HitlCoderDeps | None,
            capabilities=caps,
            retries=2,
        )
        agent.tool(self.tools.validate_syntax_tool)
        return agent

    def create_repair_agent(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        *,
        capabilities: list[Any] | None = None,
    ) -> Agent[HitlRepairDeps | None, str]:
        """Create the Pydantic AI agent for repairing existing Manim code with best practices & render skills."""
        model = self.resolver.build_model(model_name, base_url, api_key)
        caps = [get_repair_skills()] if capabilities is None else capabilities
        agent = Agent(
            model=model,
            system_prompt=REPAIR_SYSTEM_PROMPT,
            name="hitl_repair_agent",
            deps_type=HitlRepairDeps | None,
            capabilities=caps,
            retries=2,
        )
        agent.tool(self.tools.validate_syntax_tool)
        agent.tool(self.tools.search_manim_docs_tool)
        return agent


# ── OOP Class: Self-Correcting Repair Execution Runner ────────────────────────

class HitlRepairRunner:
    """Manages the iterative execution and self-correction loop of the repair agent."""

    def __init__(
        self,
        extractor: HitlCodeExtractor | None = None,
        tools: HitlAgentTools | None = None,
    ) -> None:
        self.extractor = extractor or HitlCodeExtractor()
        self.tools = tools or HitlAgentTools()

    async def run(
        self,
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

            raw_output = getattr(result, "output", getattr(result, "data", ""))
            code, scene_name = self.extractor.extract(
                raw_output, default_scene=(deps.scene_name if deps else "GeneratedScene")
            )

            if not code or "def construct" not in code:
                logger.warning("Repair pass %d returned incomplete code", attempt + 1)
                if attempt == max_attempts - 1:
                    return code, scene_name
                current_prompt = (
                    "Your output did not include a valid Manim Scene with `def construct(self):`. "
                    "Please provide the full Python script."
                )
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


# ── OOP Class: Unified HITL Agent Service ─────────────────────────────────────

class HitlAgentService:
    """Orchestration facade bringing together resolver, extractor, factory, and repair runner."""

    def __init__(
        self,
        resolver: HitlLLMResolver | None = None,
        extractor: HitlCodeExtractor | None = None,
        tools: HitlAgentTools | None = None,
        factory: HitlAgentFactory | None = None,
        repair_runner: HitlRepairRunner | None = None,
    ) -> None:
        self.resolver = resolver or HitlLLMResolver()
        self.extractor = extractor or HitlCodeExtractor()
        self.tools = tools or HitlAgentTools()
        self.factory = factory or HitlAgentFactory(resolver=self.resolver, tools=self.tools)
        self.repair_runner = repair_runner or HitlRepairRunner(extractor=self.extractor)

    def resolve_config(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model_name: str | None = None,
    ) -> tuple[str, str, str]:
        return self.resolver.resolve(api_key=api_key, base_url=base_url, model_name=model_name)

    def build_model(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> OpenRouterModel | OpenAIChatModel:
        return self.resolver.build_model(model_name=model_name, base_url=base_url, api_key=api_key)

    def extract_code(self, raw_response: str, default_scene: str = "GeneratedScene") -> tuple[str, str]:
        return self.extractor.extract(raw_response, default_scene=default_scene)

    def get_classifier_agent(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        *,
        capabilities: list[Any] | None = None,
    ) -> Agent[None, VideoClassifyResponse]:
        return self.factory.create_classifier_agent(
            model_name=model_name, base_url=base_url, api_key=api_key, capabilities=capabilities
        )

    def get_composer_agent(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        *,
        capabilities: list[Any] | None = None,
    ) -> Agent[HitlPlanDeps | None, str]:
        return self.factory.create_composer_agent(
            model_name=model_name, base_url=base_url, api_key=api_key, capabilities=capabilities
        )

    def get_coder_agent(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        *,
        capabilities: list[Any] | None = None,
    ) -> Agent[HitlCoderDeps | None, str]:
        return self.factory.create_coder_agent(
            model_name=model_name, base_url=base_url, api_key=api_key, capabilities=capabilities
        )

    def get_repair_agent(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        *,
        capabilities: list[Any] | None = None,
    ) -> Agent[HitlRepairDeps | None, str]:
        return self.factory.create_repair_agent(
            model_name=model_name, base_url=base_url, api_key=api_key, capabilities=capabilities
        )

    async def run_repair(
        self,
        agent: Agent[HitlRepairDeps | None, str],
        prompt: str,
        deps: HitlRepairDeps | None = None,
        max_attempts: int = 2,
        timeout: float = 90.0,
    ) -> tuple[str, str]:
        return await self.repair_runner.run(
            agent=agent, prompt=prompt, deps=deps, max_attempts=max_attempts, timeout=timeout
        )


# Default Singleton Instance for Module-level Access
hitl_agent_service = HitlAgentService()


# ── Backward-Compatible Module Level Functions ────────────────────────────────

def _resolve_llm_config(
    api_key: str | None = None,
    base_url: str | None = None,
    model_name: str | None = None,
) -> tuple[str, str, str]:
    return hitl_agent_service.resolve_config(api_key=api_key, base_url=base_url, model_name=model_name)


def build_hitl_model(
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> OpenRouterModel | OpenAIChatModel:
    return hitl_agent_service.build_model(model_name=model_name, base_url=base_url, api_key=api_key)


def extract_manim_code(raw_response: str, default_scene: str = "GeneratedScene") -> tuple[str, str]:
    return hitl_agent_service.extract_code(raw_response, default_scene=default_scene)


validate_syntax_tool = HitlAgentTools.validate_syntax_tool
search_manim_docs_tool = HitlAgentTools.search_manim_docs_tool


def get_classifier_agent(
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    *,
    capabilities: list[Any] | None = None,
) -> Agent[None, VideoClassifyResponse]:
    return hitl_agent_service.get_classifier_agent(
        model_name=model_name, base_url=base_url, api_key=api_key, capabilities=capabilities
    )


def get_composer_agent(
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    *,
    capabilities: list[Any] | None = None,
) -> Agent[HitlPlanDeps | None, str]:
    return hitl_agent_service.get_composer_agent(
        model_name=model_name, base_url=base_url, api_key=api_key, capabilities=capabilities
    )


def get_coder_agent(
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    *,
    capabilities: list[Any] | None = None,
) -> Agent[HitlCoderDeps | None, str]:
    return hitl_agent_service.get_coder_agent(
        model_name=model_name, base_url=base_url, api_key=api_key, capabilities=capabilities
    )


def get_repair_agent(
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    *,
    capabilities: list[Any] | None = None,
) -> Agent[HitlRepairDeps | None, str]:
    return hitl_agent_service.get_repair_agent(
        model_name=model_name, base_url=base_url, api_key=api_key, capabilities=capabilities
    )


async def run_repair_with_self_correction(
    agent: Agent[HitlRepairDeps | None, str],
    prompt: str,
    deps: HitlRepairDeps | None = None,
    max_attempts: int = 2,
    timeout: float = 90.0,
) -> tuple[str, str]:
    return await hitl_agent_service.run_repair(
        agent=agent, prompt=prompt, deps=deps, max_attempts=max_attempts, timeout=timeout
    )
