from pydantic_ai import Agent, Tool
from dotenv import load_dotenv
from pydantic_ai_harness import CodeMode
from tools import compile_manim_code, manim_write
from tools.manim_docs import manim_doc_rag
from tools.voiceover import voiceover_tools
import logfire
import logfire

logfire.configure()
logfire.instrument_pydantic_ai()

load_dotenv()

CODE_PROMPT = """Write Manim code for the given plan.

Use the coder workspace tools with a single output_dir (default: workspace/coder):
- manim_write(code, scene_name, output_dir) — writes scene.py and updates manifest.json
- compile_manim_code(code, scene_name, output_dir) — renders in the same folder, saves logs/compile.log
- synthesize_narration(text, voice, output_dir) — preview narration wav in output_dir/audio/

For voiceover scenes, use Manim Voiceover with our local TTS service:

from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService

class MyScene(VoiceoverScene):
    def construct(self):
        self.set_speech_service(
            AOSSpeechService(voice="alba", cache_dir="voiceover_cache")
        )
        with self.voiceover(text="...") as tracker:
            self.play(Create(Circle()), run_time=tracker.duration)

Always reuse the same output_dir and scene_name across write/compile/narration calls.
Tool responses are JSON with ok, paths, and status — read manifest.json for full history."""


coder_agent = Agent(
    "openrouter:moonshotai/kimi-k2.5",
    name="Code Agent",
    description="Writes Manim from LectureIR beats and synthesizes narration audio.",
    system_prompt=CODE_PROMPT,
    retries=2,
    capabilities=[CodeMode()],
    tools=[
        Tool(compile_manim_code),
        Tool(manim_write),
        *[Tool(f) for f in manim_doc_rag()],
        *[Tool(f) for f in voiceover_tools()],
    ],
)
