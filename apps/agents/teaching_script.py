"""Teaching-script planner: spoken pedagogy before Manim coding."""

from __future__ import annotations

import json
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_ai import Agent, ModelRetry

from llm_config import model_for_agent, settings_for
from tools.voiceover_quality import is_filler_narration

load_dotenv()

TEACHING_SCRIPT_PROMPT = """\
You write the spoken teaching script for one AOS Manim animation.

Given a topic, subject, and lecture plan (objectives, opener, formulas),
produce a TeachingScript. You decide WHAT the teacher says and WHY.
A later coding agent will implement Manim. Do not write Python.

Narration is the teacher. Visuals are the demonstration.
Never generate narration whose sole purpose is to announce that an object
is appearing.

Rules:
- Every beat answers: what should the student learn from this visual?
- Never copy on-screen titles, Tex, or bullet text into narration.
- Never use filler: "Let's look at this on the board", "Here we have…",
  "As you can see", "Let's explore this", "Isn't that amazing?"
- Interpret relationships; do not read equations or bullets verbatim.
- Write for the ear: short sentences, contractions (it's, that's, we're).
- Speak math: "e to the i x", "cosine of x", "sine of x",
  "e to the i pi, plus one, equals zero".
- Last beat is a conceptual takeaway, not empty praise.
- 6–10 beats. Follow: what are we looking at → what it means → why it
  matters → what changes → what to notice → takeaway.
- bookmark_marks: only for sequential teaching highlights (introduce,
  highlight a part, consequence). Not every FadeIn/scale/color.
- scene_class_name: PascalCase, preferably ending with Scene.

Good narration:
"Euler's formula shows that a complex exponential can be written using
cosine and sine."

Bad narration:
"Let's look at this equation." / "Here we have Euler's Formula."
"""


class TeachingBeat(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    takeaway: str = Field(description="What the student should understand.")
    visual: str = Field(description="What appears or is highlighted on screen.")
    narration: str = Field(description="Spoken line, TTS-safe, teaching not caption.")
    bookmark_marks: list[str] = Field(default_factory=list)

    @field_validator("narration")
    @classmethod
    def _narration_not_filler(cls, value: str) -> str:
        text = (value or "").strip()
        if is_filler_narration(text):
            raise ValueError("narration is filler; explain the learning point instead")
        return text


class TeachingScript(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene_class_name: str
    throughline: str = Field(description="One-sentence arc of the lesson.")
    beats: list[TeachingBeat]


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
    if not (6 <= n <= 10):
        raise ModelRetry(
            f"TeachingScript needs 6–10 beats, got {n}. "
            "Split or merge so each beat teaches one idea."
        )
    filler_ids = [
        b.id for b in script.beats if is_filler_narration(b.narration)
    ]
    if filler_ids:
        raise ModelRetry(
            f"Beat(s) {filler_ids} use filler narration. "
            "Explain the learning point; do not announce objects."
        )
    last = script.beats[-1].narration.lower()
    praise = ("amazing", "beautiful", "magical", "pretty cool", "wonderful")
    if any(p in last for p in praise) and "takeaway" not in last and "key" not in last:
        raise ModelRetry(
            "The last beat must state a conceptual takeaway, not empty praise."
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
) -> str:
    if hasattr(lecture, "model_dump"):
        plan = lecture.model_dump(mode="json")
    elif isinstance(lecture, dict):
        plan = lecture
    else:
        plan = {"raw": str(lecture)}
    return (
        f"Topic: {topic}\n"
        f"Subject: {subject}\n"
        f"Lecture plan:\n{json.dumps(plan, indent=2)}"
    )
