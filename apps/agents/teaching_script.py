"""Teaching-script planner: spoken pedagogy before Manim coding."""

from __future__ import annotations

import json
import re
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_ai import Agent, ModelRetry

from llm_config import model_for_agent, settings_for
from tools.voiceover_quality import is_filler_narration

load_dotenv()

TEACHING_SCRIPT_PROMPT = """\
You write the spoken teaching script for one AOS Manim animation.

Given a topic, subject, lecture plan, and target duration/pacing,
produce a TeachingScript. You decide WHAT the teacher says and WHY.
A later coding agent will implement Manim. Do not write Python.

Narration is the teacher. Visuals are the demonstration.
Never generate narration whose sole purpose is to announce that an object
is appearing.

Pacing, Calmness & Depth (CRITICAL):
- Speak with calm, patient clarity like 3Blue1Brown or a master lecturer.
- Never compress complex ideas into a single rushed sentence.
- Allow ideas to breathe: each beat should have 3 to 5 full sentences (40–70 words) explaining the physical, algebraic, and geometric intuition behind every equation, variable, and dynamic transformation.
- For dynamic systems (e.g. Lorenz attractor): explain the physical motivation (atmospheric convection rolls), the 3 variables, why deterministic equations create non-repeating bounded trajectories, and the essence of the butterfly effect.
- Clear screen between acts: do not crowd everything together.

Visual Design Language (use rich, specific descriptions — the coder reads these):
- For 3D topics (attractors, surfaces, orbital mechanics, wave packets):
  write "Introduce the [object] in 3D, rotating slowly" or "Show the trajectory from above as the camera orbits" — this triggers camera rotation.
- For equations being derived step-by-step:
  write "Step-by-step derivation: [eq] becomes [eq]" — this triggers equation morphing animations.
- For moving quantities (angle theta, time t, variable x):
  write "A moving dot traces the path as theta increases from 0 to 2π" — this triggers updater animations.
- For dramatic reveals of key terms:
  write "Highlight the key term [term]" or "Emphasize [concept]" — this triggers Indicate+Flash pulses.
- For comparisons:
  write "Compare [A] and [B] side by side" — this triggers a split-screen layout.
- For particle/field topics (EM field, wave propagation, quantum probability):
  write "A field of particles shows the distribution" — this triggers animated particle fields.
- For any path/trajectory being traced over time:
  write "Trace the path of the point as it moves" — this triggers TracedPath.
- For lists appearing gradually:
  write "Each property appears one by one" — this triggers a slow-reveal LaggedStart.
- For overview moments:
  write "Pull back to show the full picture" or "Zoom out to see the complete structure" — this triggers camera zoom-out.

Rules:
- Every beat answers: what should the student learn from this visual?
- Never copy on-screen titles, Tex, or bullet text into narration.
- Never use filler: "Let's look at this on the board", "Here we have…",
  "As you can see", "Let's explore this", "Isn't that amazing?"
- Interpret relationships; do not read equations or bullets verbatim.
- Write for the ear: spoken English with natural rhythm and contractions.
- Speak math: "e to the i x", "d x over d t equals sigma times y minus x".
- Last beat is a conceptual takeaway, not empty praise.
- bookmark_marks: only for sequential teaching highlights.
- scene_class_name: PascalCase ending with Scene (e.g. LorenzAttractorScene).

Expected output structure:
{
  "scene_class_name": "EulersFormulaScene",
  "throughline": "Euler's formula connects exponential growth to circular rotation in the complex plane.",
  "beats": [
    {
      "id": "b1",
      "takeaway": "Euler's formula unites exponential growth and circular trigonometry.",
      "visual": "Title and the master formula: e^{i theta} = cos(theta) + i sin(theta)",
      "narration": "Euler's formula reveals a profound bridge connecting exponential growth to trigonometry in the complex plane."
    },
    {
      "id": "b2",
      "takeaway": "In the complex plane, multiplying by i rotates numbers by 90 degrees.",
      "visual": "Draw complex coordinate plane with Re(z) and Im(z) axes.",
      "narration": "In the complex plane, horizontal is the real axis and vertical is the imaginary axis. Multiplying by i rotates any vector by 90 degrees."
    },
    {
      "id": "b3",
      "takeaway": "The unit circle defines points at distance 1 with coordinates (cos theta, sin theta).",
      "visual": "A moving dot traces the unit circle path as theta increases from 0 to 2 pi.",
      "narration": "On the unit circle, an angle theta traces a point whose coordinates are cosine theta and sine theta."
    },
    {
      "id": "b4",
      "takeaway": "Continuous imaginary growth produces steady rotation at speed 1.",
      "visual": "Rotating vector along the unit circle, highlighting the key relationship e to i theta.",
      "narration": "Because multiplying by i is perpendicular to position, e to the i theta produces continuous circular motion."
    },
    {
      "id": "b5",
      "takeaway": "Euler's identity unites 5 fundamental constants.",
      "visual": "Pull back to show the full picture: theta = pi yielding e^{i pi} + 1 = 0.",
      "narration": "When theta equals pi, we reach minus 1, giving Euler's identity: e to the i pi plus 1 equals zero."
    }
  ]
}
"""



class TeachingBeat(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = "b1"
    takeaway: str = Field(default="Key conceptual understanding", description="What the student should understand.")
    visual: str = Field(default="Visualization on screen", description="What appears or is highlighted on screen.")
    narration: str = Field(description="Spoken line, TTS-safe, teaching not caption.")
    bookmark_marks: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _sanitize_beat(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"id": "b1", "takeaway": data, "visual": "Illustration of concept", "narration": data}
        if isinstance(data, dict):
            narration = (
                data.get("narration")
                or data.get("text")
                or data.get("line")
                or data.get("spoken")
                or data.get("content")
                or ""
            )
            if not narration and "visual" in data:
                narration = str(data["visual"])
            data["narration"] = str(narration).strip()
            if not data.get("id"):
                data["id"] = "b1"
            if not data.get("takeaway"):
                data["takeaway"] = data["narration"][:120] if data["narration"] else "Conceptual intuition"
            if not data.get("visual"):
                data["visual"] = f"Visual illustration: {data['takeaway'][:80]}"
        return data


class TeachingScript(BaseModel):
    model_config = ConfigDict(extra="ignore")

    scene_class_name: str = "MainScene"
    throughline: str = Field(default="Intuitive pedagogical walkthrough.", description="One-sentence arc of the lesson.")
    beats: list[TeachingBeat]

    @model_validator(mode="before")
    @classmethod
    def _unwrap_and_normalize(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Unwrap nested keys often emitted by LLMs
        for wrap_key in ("script", "teaching_script", "data", "result", "payload"):
            if wrap_key in data and isinstance(data[wrap_key], dict):
                inner = dict(data[wrap_key])
                for k, v in data.items():
                    if k != wrap_key and k not in inner:
                        inner[k] = v
                data = inner

        # If model emitted 'lines' instead of 'beats'
        if "beats" not in data and "lines" in data:
            raw_lines = data.get("lines")
            if isinstance(raw_lines, list):
                beats = []
                for i, line in enumerate(raw_lines, 1):
                    if isinstance(line, str):
                        beats.append({
                            "id": f"b{i}",
                            "takeaway": f"Beat {i} core concept",
                            "visual": f"Demonstration of {line[:40]}",
                            "narration": line,
                        })
                    elif isinstance(line, dict):
                        beats.append(line)
                data["beats"] = beats

        # Ensure throughline is present
        if not data.get("throughline"):
            beats_list = data.get("beats") or []
            if beats_list and isinstance(beats_list, list) and len(beats_list) > 0:
                first = beats_list[0]
                first_text = first.get("narration") if isinstance(first, dict) else str(first)
                data["throughline"] = f"Visual explanation: {first_text[:120]}"
            else:
                data["throughline"] = "Intuitive visual exploration of fundamental principles."

        # Ensure scene_class_name
        name = data.get("scene_class_name") or ""
        if not name:
            data["scene_class_name"] = "MainTeachingScene"
        else:
            clean_name = re.sub(r"[^A-Za-z0-9]", "", name)
            if not clean_name:
                clean_name = "MainTeachingScene"
            elif not clean_name.endswith("Scene"):
                clean_name = f"{clean_name}Scene"
            data["scene_class_name"] = clean_name

        return data


teaching_script_agent = Agent(
    model_for_agent("planner"),
    name="Teaching Script Agent",
    description="Plans spoken teaching beats before Manim is written.",
    system_prompt=TEACHING_SCRIPT_PROMPT,
    output_type=TeachingScript,
    model_settings=settings_for("planner"),
    retries=4,
)


@teaching_script_agent.output_validator
def _require_teaching_beats(script: TeachingScript) -> TeachingScript:
    n = len(script.beats)
    if n < 3:
        raise ModelRetry(
            f"TeachingScript needs at least 3 beats, got {n}. "
            "Add beats to guide the student through the concept step-by-step."
        )
    return script


def teaching_script_to_payload(script: TeachingScript | dict[str, Any] | None) -> dict[str, Any] | None:
    if script is None:
        return None
    if isinstance(script, dict):
        return script
    return script.model_dump(mode="json")


def teaching_script_user_prompt(
    topic: str,
    subject: str,
    lecture: Any,
    *,
    length: str = "medium",
    cinematic: bool = False,
) -> str:
    from cinematic_director import is_cinematic_mode

    if hasattr(lecture, "model_dump"):
        plan = lecture.model_dump(mode="json")
    elif isinstance(lecture, dict):
        plan = lecture
    else:
        plan = {"raw": str(lecture)}

    is_long = length in ("long", "10m", "10min", "10", "15m", "15min", "15")
    is_medium = length in ("medium", "5m", "5min", "5", "default")
    cinematic_active = cinematic or is_cinematic_mode(topic)

    if is_long:
        pacing_guide = (
            "Target duration: 10–15 minutes (Comprehensive In-Depth Masterclass).\n"
            "- Generate 12–16 comprehensive, sequentially progressive teaching beats grouped conceptually into 4–5 Chapters.\n"
            "- Every beat MUST be calm, patient, and thorough: 3–5 full sentences (50–80 words) per beat.\n"
            "- Take time to thoroughly explain the physical intuition, mathematical mechanism, and geometric behavior.\n"
            "- Allow cognitive pauses between major concepts."
        )
    elif is_medium:
        pacing_guide = (
            "Target duration: 3–5 minutes (Calm, In-Depth Explainer).\n"
            "- Generate 8–12 distinct teaching beats.\n"
            "- Every beat MUST be calm and explanatory: 3–5 full sentences (40–70 words) per beat.\n"
            "- Take time to explain what each symbol means physically before moving to the next concept.\n"
            "- Maintain clean screen transitions between 2D math and 3D simulations."
        )
    else:
        pacing_guide = (
            "Target duration: 1–2 minutes (High-Impact Micro-Lesson).\n"
            "- Generate 4–6 clear, focused beats.\n"
            "- Fast attention-grabbing hook, single core equation, immediate 3D visual payoff, and clean takeaway.\n"
            "- Each beat contains 2–3 sentences of clear conceptual intuition."
        )

    cinematic_block = ""
    if cinematic_active:
        cinematic_block = (
            "\nCinematic Director Aesthetics:\n"
            "- Visuals must specify 3D sweeping camera movements (e.g. 'Camera orbits slowly around the 3D attractor').\n"
            "- Visuals must include velocity-based color grading and trajectory tracing.\n"
            "- Narration must evoke profound mathematical beauty and physical intuition.\n"
        )

    return (
        f"Topic: {topic}\n"
        f"Subject: {subject}\n"
        f"Pacing & Duration Guidelines:\n{pacing_guide}{cinematic_block}\n\n"
        f"Lecture plan:\n{json.dumps(plan, indent=2)}"
    )
