from pydantic_ai import Agent, Tool
from dotenv import load_dotenv
from codemode_retry import install_codemode_retry_patch
from llm_config import is_ollama, model_for, model_for_agent, settings_for
from pydantic_ai_harness import CodeMode
from tools import compile_manim_code, manim_write
from tools.manim_read import manim_read
from tools.manim_docs import manim_doc_rag
from tools.voiceover import voiceover_tools

from observability import configure_logfire

configure_logfire()

load_dotenv()
install_codemode_retry_patch()

# Compact prompt for Ollama/GGUF E2B — same shape as diagnosis-passing Infer probe.
# Keep this short; do not paste full Manim scenes (E2B copies bare imports into run_code).
CODE_PROMPT_LOCAL = """You are a Manim coding agent. Call tools ONLY via run_code (CodeMode).
If the user pins output_dir, pass that exact path to every manim_write / compile_manim_code call.

Inside run_code, orchestrate workspace tools with await:
  await manim_write(code='''...''', scene_name='ClassName')
  await compile_manim_code(code='''...''', scene_name='ClassName')
Never write `from manim import *` directly in run_code — put Manim source inside a string passed to manim_write.

STRING RULES (CRITICAL):
- Multi-line Manim source MUST use triple quotes ('''...''' or \"\"\"...\"\"\"). Never use "..." or '...' spanning multiple lines — that is invalid Python.
- Never call run_code from inside code passed to run_code, manim_write, or compile_manim_code.

Narration (required):
- Scene MUST subclass VoiceoverScene, call set_speech_service(AOSSpeechService(...)),
  and wrap beats in with self.voiceover(text="...") as tracker: with run_time=tracker.duration.
- Plain Scene / silent self.play without voiceover will fail compile.

Workflow: manim_write → compile_manim_code → fix (at most 3 compile attempts) → stop.
"""

CODE_PROMPT = """Write Manim code for the given lecture plan.

output_dir rules:
- If the user message pins an output_dir, use THAT exact path for every tool call — never switch.
- If no output_dir is given, OMIT the output_dir argument (tools default to workspace/coder).
- NEVER invent paths like /workspace, /tmp, or arbitrary absolute roots.
- Relative names like "output" resolve under workspace/ — prefer omitting output_dir instead.

Tools (call via CodeMode run_code):
- manim_write(code, scene_name, output_dir?) — writes the scene .py and updates manifest.json
- compile_manim_code(code, scene_name, output_dir?) — renders in the same folder, saves logs/compile.log
- manim_read(output_dir?) — read back the current scene source
- search_manim_docs / search_manim_signatures — look up Manim APIs when stuck
- synthesize_narration(text, voice, output_dir?) — preview narration wav in output_dir/audio/

CodeMode contract (CRITICAL — run_code is a sandbox, not a Manim file):
- Inside run_code, ONLY orchestrate tools with await (manim_write, compile_manim_code, ...).
- Put `from manim import *`, scene classes, and construct() INSIDE the code= string passed to
  manim_write / compile_manim_code. Never put those at the top level of run_code.
- Correct skeleton (copy this shape):

code = '''
from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService

class MyScene(VoiceoverScene):
    def construct(self):
        self.set_speech_service(
            AOSSpeechService(voice="alba", cache_dir="voiceover_cache")
        )
        with self.voiceover(text="Watch these two values — 5 and 2 are out of order, so we swap.") as tracker:
            self.play(Swap(a, b), run_time=tracker.duration)
'''
await manim_write(code=code, scene_name='MyScene')
await compile_manim_code(code=code, scene_name='MyScene')

- Wrong (will fail type-check): starting run_code with `from manim import *` or a class Scene(...).
- STRING RULES (CRITICAL):
  - Multi-line Manim source MUST use triple quotes ('''...''' or \"\"\"...\"\"\"). Never use "..." or '...' spanning multiple lines — that is invalid Python.
  - Never call run_code from inside code passed to run_code, manim_write, or compile_manim_code.
- For voiceover scenes, use EXACTLY the imports inside the nested code= string above
  (not manim_voiceover.services.*).

scene_name rules:
- Pick one scene_name and keep it for the whole run.
- scene_name MUST match the Python class name exactly
  (e.g. scene_name="EigenvectorExplanation" with class EigenvectorExplanation).
- Prefer PascalCase class names that end with Scene or a clear topic name.

Canvas & layout (critical — keep the board readable):
- Default to a flat 2D teaching board: subclass Scene or VoiceoverScene, NOT ThreeDScene,
  unless the concept truly needs depth (surfaces, 3D trajectories, Lorenz, etc.).
- For chess lessons, prefer: `from manim_chess import ChessBoard, BoardTheme`
  (2D SVG pieces via python-chess). Do not use ThreeDScene for chess boards.
- For AI / deep learning lessons, prefer: `from manim_ai import get_concept, list_concepts, LinearLayer, Network`
  and VoiceoverScene + `<bookmark mark='…'/>` / wait_until_bookmark (see manim_ai.reveal_with_bookmarks).
- For maths lessons, prefer: `from manim_math import get_concept, list_concepts`.
- For high-school mechanics, prefer: `from manim_physics import get_concept, list_concepts`.
- For algorithms / data structures, prefer: `from manim_dsa import get_concept, list_concepts`.
- Shared drawing primitives live in `manim_viz` (arrays, graphs, vectors, particles, plots).
- For 2D board / list / equation scenes: do NOT call set_camera_orientation,
  begin_ambient_camera_rotation, or other 3D camera moves. No slanted "fake 3D" views.
- Keep all content inside the frame: roughly |x| ≤ 6.5, |y| ≤ 3.5. Leave margins.
  Never let a SurroundingRectangle, VGroup, or Text clip past the edge.
- Bullet / takeaway lists: if more than ~4 items OR a boxed group would be tall/wide,
  use TWO COLUMNS (VGroup of left/right columns, arrange(RIGHT, buff=...)), then box
  each column or the combined group. Never one tall single-column box that overflows.
- Prefer arrange / arrange_in_grid over hand-tuned absolute positions that drift off-canvas.
- Scale text down (font_size or .scale_to_fit_width / .scale_to_fit_height) rather than
  letting groups spill past the frame.

Workflow (do not loop forever):
1. manim_write the full scene.
2. compile_manim_code. If it fails, read the log excerpt / message, fix, rewrite, recompile.
3. At most 3 compile attempts total. After a successful compile (ok=true), stop coding.
4. Optionally synthesize_narration for a short preview, then STOP.

Stop criteria:
- STOP as soon as compile returns ok=true (and optional narration is done).
- Do NOT restart the scene from scratch repeatedly.
- Do NOT keep calling tools after success.
- If compile still fails after 3 attempts, stop and summarize what failed.
- If message/log mentions standalone.cls or LaTeX Error: do NOT thrash on string escaping.
  Treat it as an environment failure (or fall back to Text once), then STOP.

Math:
- Prefer MathTex / Tex for equations when TeX works.
- Use raw strings: MathTex(r"A\\mathbf{v} = \\lambda \\mathbf{v}").

Narration (do NOT go quiet during visuals):
- Prefer VoiceoverScene for teaching lectures. Silent self.play(...) stretches with no
  voiceover are a bug — every meaningful beat needs a short spoken line.
- Wrap each visual beat in with self.voiceover(text="...") as tracker: and use
  run_time=tracker.duration (or match hold to the tracker) so speech and motion stay in sync.
- During process demos (sorting, searches, graph walks, iterations): narrate WHAT is
  happening on screen in the moment, second person / present tense.
  Bad: long silence while bars swap.
  Good: "Watch 5 and 2 — they're out of order, so we swap them." / "Now 5 bubbles past 3."
- Call out concrete values, comparisons, and outcomes as they appear; do not only narrate
  the intro and the final takeaway.
- Keep lines short (about one sentence per beat) for process demos. Prefer many small
  voiceovers over one long monologue at the start.

Equation pacing (do NOT race past math):
- For dense equations / multi-step algebra: one concept per voiceover beat — do not rush
  to the next topic while the learner is still reading the formula.
- Pattern: introduce the equation → hold/Write/FadeIn while naming each term → only then
  animate the next algebraic step.
- Prefer a longer explanatory line (or self.wait after MathTex appears) so speech covers
  the formula while it stays on screen.
- Avoid chaining many Transform/ReplacementTransform equation steps under one short sentence.

Tool responses are JSON with ok, paths, and status — read them carefully.
"""

SFT_BATCH_ADDENDUM = """
SFT batch mode:
- Do NOT call synthesize_narration.
- Stop immediately after compile_manim_code returns ok=true.
"""


def coder_system_prompt() -> str:
    """Full cloud prompt, or compact local prompt when the coder is Ollama/GGUF."""
    if is_ollama(model_for("coder")):
        return CODE_PROMPT_LOCAL
    return CODE_PROMPT


def coder_prompt_variant() -> str:
    return "local" if is_ollama(model_for("coder")) else "full"


coder_agent = Agent(
    model_for_agent("coder"),
    name="Code Agent",
    description="Writes Manim from a lecture plan, compiles, and optionally synthesizes narration audio.",
    system_prompt=coder_system_prompt(),
    model_settings=settings_for("coder"),
    retries=2,
    capabilities=[CodeMode(max_retries=3)],
    tools=[
        Tool(compile_manim_code),
        Tool(manim_read),
        Tool(manim_write),
        *[Tool(f) for f in manim_doc_rag()],
        *[Tool(f) for f in voiceover_tools()],
    ],
)
