from pydantic_ai import Agent, ModelRetry
from dotenv import load_dotenv
from ir.manim_ir import Beat

load_dotenv()

NARRATION_PROMPT = """\
You write spoken narration for AOS Manim animation beats.

Given a list of Beat objects (with animation_segment filled, narration empty)
belonging to ONE scene, plus that scene's pedagogical context (the storyboard
step's move / goal / viewer question, when provided above the beats), return
the same beats with narration populated on each.

Narration is not a caption. Don't just describe what moved — say why it
matters. Every beat exists to teach one idea; the narration is the sentence
that idea would be, if the pedagogical goal above were spoken instead of drawn.

── NARRATION SEGMENT FIELDS ─────────────────────────────────────────────────
  text        — 15-40 words, present tense, direct address ("you", "we", "notice")
  est_seconds — leave 0.0 (auto-estimated from word count)
  emphasis    — 1-2 key phrases from `text` to stress (must be substrings of
                text, verbatim — e.g. "step size", not "the step size chosen")

Style:
  Written as if spoken live to the viewer.
  Good: "Notice how the gradient arrow always points uphill."
  Bad:  "The gradient arrow is seen pointing in the uphill direction."

── MATCH NARRATION TO WHAT THE BEAT'S OPS ACTUALLY DO ───────────────────────
  create / write / fade_in / grow / transform_from_copy (something new appears):
    introduce it and say what it is — "Here's the gradient vector."
  move / shift / rotate / scale (repositioning, same object):
    narrate the motion's meaning, not the geometry — "Watch it slide toward
    the minimum" rather than "It moves right."
  highlight / circumscribe (emphasis, no state change):
    this is the beat's point — say what to notice and why it matters, e.g.
    "This is the term that controls how big each step is."
  fade_out (removal / transition):
    bridge forward, don't just announce the exit — "We've seen the naive
    approach fail; here's the fix."
  If the storyboard context gave a viewer_question and this beat is the one
  that introduces the `reveal`-labeled answer, acknowledge the question before
  answering it: "You guessed the ball would overshoot — here's why."

── PACING: SIZE THE NARRATION TO THE BEAT'S OWN DURATION ────────────────────
Each beat JSON includes its own run_time(s) and hold_seconds. Compute the
beat's available seconds = sum(op.run_time) + hold_seconds, then target
roughly available_seconds * 2.7 words (~2.7 words/sec, calm pace), clamped to
the 15-40 word range. A beat with only 1.5s of run_time+hold should get a
short sentence near the low end, not a 40-word paragraph — a mismatch here is
exactly what makes narration feel rushed or an audio clip feel padded/empty.

Rules:
- One visual idea per beat — don't explain the whole lecture in one narration.
- Never leave a beat's narration near-empty just to move on; if a beat truly
  has nothing to say (e.g. a bare fade_out with no new idea), fold its meaning
  into an adjacent beat's narration rather than writing a throwaway line.
"""

narration_planner_agent = Agent(
    'openrouter:openai/gpt-4o-mini',
    name='Narration Planner Agent',
    description='Generates narration for Manim animation beats.',
    system_prompt=NARRATION_PROMPT,
    output_type=list[Beat],
    retries=4,
)


@narration_planner_agent.output_validator
def _require_narration_on_beats(beats: list[Beat]) -> list[Beat]:
    if not beats:
        return beats
    missing = [
        b.id
        for b in beats
        if b.narration is None or not b.narration.text.strip()
    ]
    if missing:
        raise ModelRetry(
            f"Beat(s) {missing} need narration.text populated (15-40 words each)."
        )

    bad_length = [
        f"{b.id} ({len(b.narration.text.split())} words)"
        for b in beats
        if not (10 <= len(b.narration.text.split()) <= 45)
    ]
    if bad_length:
        raise ModelRetry(
            f"Beat(s) {bad_length} are outside the 10-45 word range "
            "(target 15-40, sized to each beat's own run_time + hold_seconds). "
            "Rewrite them to fit."
        )

    bad_emphasis = [
        f"{b.id} (missing: {phrase!r})"
        for b in beats
        for phrase in b.narration.emphasis
        if phrase.lower() not in b.narration.text.lower()
    ]
    if bad_emphasis:
        raise ModelRetry(
            f"Emphasis phrase(s) not found verbatim in their beat's narration text: "
            f"{bad_emphasis}. Either quote the phrase exactly as it appears in "
            "`text`, or drop it from `emphasis`."
        )
    return beats
