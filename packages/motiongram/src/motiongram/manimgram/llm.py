"""LLM integration utilities for constrained decoding and schema export."""

from __future__ import annotations

import json
from typing import Any

from motiongram.manimgram.schema import ManimGramScene

MANIMGRAM_SYSTEM_PROMPT = """You are an expert mathematical animator and director using ManimGram.
Your role is to act as Storyboard Artist. You MUST output a valid ManimGram YAML/JSON specification.

CORE PRINCIPLES:
1. Do not output raw Python code. Output ONLY the ManimGram DSL.
2. Every visual entity must have a unique 'id' and valid 'type'
   (e.g. Matrix, MathTex, Text, Circle, Square, Axes, ThreeDAxes, Surface).
3. Use semantic selectors for submobjects instead of guessing raw indices:
   - For Matrix: 'entry[row,col]', 'row[r]', 'col[c]', 'brackets'
   - For MathTex: 'term[latex_snippet]', 'part[idx]'
   - For Axes: 'x_axis', 'y_axis', 'point[x,y]'
4. Use relative positioning in 'layout' (e.g. 'next_to', 'to_edge', 'shift').
5. In 'timeline', use declarative animation actions:
   - 'Create', 'Write', 'FadeIn', 'FadeOut', 'Transform', 'ReplacementTransform'
   - 'TransformMatchingTex' for equation morphing
   - 'RoutedTransform' for fine-grained subobject morphing (e.g., matrix entry to a label)
   - 'Wait' for pacing

VOICEOVER & BOOKMARKS:
When creating narrated educational scenes:
1. Set 'scene.type: VoiceoverScene' with 'config: {voice: "alba", cache_dir: "voiceover_cache"}'.
2. Use one 'voiceover_block' per visual beat. Put its Write/Create/FadeIn actions in
   'actions'; the compiler reveals them first and starts the narration afterward.
3. The compiler fades the previous visual before a new Write/Create/FadeIn, then
   clears the beat after its narration when another timeline item follows. Do not
   add WaitUntilBookmark actions or bookmark tags for ordinary narration.
4. Set 'params: {keep_previous: true}' on a reveal action only when its object
   should intentionally remain beside the previous object (for example, parts of
   one diagram). Otherwise each reveal replaces the previous visual.
5. Keep narration conversational, concise, and focused on the visible idea.
"""

FEW_SHOT_EXAMPLES = [
    {
        "prompt": "Explain tanh by showing its formula, then a concise takeaway, narrating each visual after it appears.",
        "yaml": """scene:
  class_name: TanhExplainerScene
  type: VoiceoverScene
  background_color: "#141414"
  config:
    voice: alba

mobjects:
  - id: formula
    type: MathTex
    props:
      tex: '\\tanh(x) = \\frac{e^x - e^{-x}}{e^x + e^{-x}}'
      color: WHITE
    layout:
      center: true

  - id: graph_label
    type: Text
    props:
      text: "tanh(x) stays between -1 and 1"
      color: YELLOW
    layout:
      center: true

timeline:
  - type: voiceover_block
    text: "This formula defines tanh as a ratio of exponentials."
    actions:
      - action: Write
        target: formula

  - type: voiceover_block
    text: "Its output smoothly approaches negative one and positive one."
    actions:
      - action: Write
        target: graph_label
"""
    },
    {
        "prompt": (
            "Show a 2x2 matrix A and morph the top-left element into the letter B above the matrix."
        ),
        "yaml": """scene:
  class_name: MatrixMorphScene
  type: Scene
  background_color: "#1C1C1C"

mobjects:
  - id: matA
    type: Matrix
    props:
      matrix: [[1, 2], [3, 4]]
      bracket_color: BLUE
    layout:
      shift: [-2, 0, 0]

  - id: labelB
    type: Text
    props:
      text: "B"
      color: YELLOW
    layout:
      next_to:
        target: matA
        direction: UP
        buff: 0.8
    state:
      opacity: 0

timeline:
  - action: Create
    target: matA
    run_time: 1.0

  - action: Wait
    run_time: 0.5

  - action: RoutedTransform
    source: matA
    target: labelB
    run_time: 1.5
    routes:
      - from: "entry[0,0]"
        to: "labelB"
        animation: ReplacementTransform
"""
    },
    {
        "prompt": "Show the quadratic equation x^2 - 4 = 0 and factor it into (x-2)(x+2) = 0.",
        "yaml": """scene:
  class_name: FactorEquationScene
  type: Scene
  background_color: "#141414"

mobjects:
  - id: eq1
    type: MathTex
    props:
      tex: "x^2 - 4 = 0"
      color: WHITE
    layout:
      center: true

  - id: eq2
    type: MathTex
    props:
      tex: "(x - 2)(x + 2) = 0"
      color: WHITE
    layout:
      center: true
    state:
      opacity: 0

timeline:
  - action: Write
    target: eq1
    run_time: 1.2

  - action: Wait
    run_time: 0.5

  - action: TransformMatchingTex
    source: eq1
    target: eq2
    run_time: 1.5
"""
    }
]


def get_json_schema() -> dict[str, Any]:
    """Return JSON Schema for ManimGramScene (for OpenAI/Qwen structured outputs/Instructor)."""
    return ManimGramScene.model_json_schema()


def get_json_schema_str(indent: int = 2) -> str:
    """Return formatted JSON Schema string."""
    return json.dumps(get_json_schema(), indent=indent)


def get_system_prompt() -> str:
    """Return the base system prompt for LLM storyboard generation."""
    return MANIMGRAM_SYSTEM_PROMPT


def get_few_shot_examples() -> list[dict[str, str]]:
    """Return verified few-shot prompt/DSL pairs."""
    return FEW_SHOT_EXAMPLES


def format_repair_prompt(invalid_dsl: str, errors: str | list[str]) -> str:
    """Format an error diagnostic and invalid spec into an actionable prompt for LLM."""
    if isinstance(errors, list):
        error_text = "\n".join(f"- {err}" for err in errors)
    else:
        error_text = str(errors)

    header = "The previous ManimGram YAML/JSON specification encountered error(s):"
    return f"""{header}

==============================
ERROR DIAGNOSTIC
==============================
{error_text}

==============================
FAILED SPECIFICATION
==============================
{invalid_dsl}

==============================
INSTRUCTIONS
==============================
1. Review the error diagnostic above.
2. Fix all schema validation issues (e.g. invalid mobject types, duplicate IDs,
   missing target IDs, unresolvable submobject selectors).
3. Output ONLY the corrected, fully valid ManimGram YAML specification.
   Do not include markdown code block explanations or commentary.
"""


def validate_and_generate_repair(dsl_text: str) -> tuple[bool, str]:
    """Validate YAML/JSON DSL text. Return (True, 'Valid') or (False, repair_prompt)."""
    import yaml
    from pydantic import ValidationError

    try:
        data = yaml.safe_load(dsl_text)
        if not isinstance(data, dict):
            return False, format_repair_prompt(
                dsl_text, "Root element must be a YAML mapping/dictionary."
            )
        ManimGramScene.model_validate(data)
        return True, "Specification is valid."
    except (ValidationError, Exception) as e:
        return False, format_repair_prompt(dsl_text, str(e))
