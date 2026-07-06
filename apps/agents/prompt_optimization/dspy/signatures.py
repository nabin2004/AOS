"""
DSPy signatures for the AOS IR generation pipeline.
Each signature is the input/output contract for one LLM call.

Install DSPy: uv add dspy-ai
"""
import dspy


class ClassifyRequest(dspy.Signature):
    """Classify a learning request into a subject domain and clean topic name."""

    user_request: str = dspy.InputField(desc="natural language request from the user")
    subject: str = dspy.OutputField(desc='one of: "math", "cs", "ai", "unknown"')
    topic: str = dspy.OutputField(desc="2-6 word, title-cased topic name, no punctuation")


class PlanLecture(dspy.Signature):
    """Generate a lecture plan for an AOS educational animation."""

    topic: str = dspy.InputField(desc="lecture topic, e.g. 'Gradient Descent'")
    subject: str = dspy.InputField(desc='subject domain: "math", "cs", or "ai"')
    lecture_json: str = dspy.OutputField(desc="valid JSON matching the ir.Lecture schema")


class PlanStoryboard(dspy.Signature):
    """Generate a storyboard from a lecture plan."""

    topic: str = dspy.InputField()
    objectives: str = dspy.InputField(desc="learning objectives from the Lecture, newline-separated")
    storyboard_json: str = dspy.OutputField(desc="valid JSON matching the ir.Storyboard schema")


class BuildScene(dspy.Signature):
    """Generate a Manim scene for one storyboard step."""

    move: str = dspy.InputField(desc="pedagogical move: hook, define, example, etc.")
    goal: str = dspy.InputField(desc="what this scene should accomplish")
    topic: str = dspy.InputField()
    scene_json: str = dspy.OutputField(desc="valid JSON matching the ir.Scene schema")
