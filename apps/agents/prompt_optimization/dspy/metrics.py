"""
DSPy metrics for evaluating AOS IR generation quality.
Each metric returns a float in [0, 1].
"""
from ir.manim_ir import Lecture, Scene, Storyboard


def subject_exact_match(example, prediction, trace=None) -> float:
    return float(example.subject.lower() == prediction.subject.lower())


def topic_nonempty(example, prediction, trace=None) -> float:
    return float(bool(prediction.topic.strip()))


def classification_score(example, prediction, trace=None) -> float:
    return (subject_exact_match(example, prediction) + topic_nonempty(example, prediction)) / 2


def lecture_valid(example, prediction, trace=None) -> float:
    try:
        obj = Lecture.model_validate_json(prediction.lecture_json)
        checks = [
            bool(obj.topic),
            bool(obj.opener),
            len(obj.objectives) >= 2,
            len(obj.learning_outcomes) >= 2,
        ]
        return sum(checks) / len(checks)
    except Exception:
        return 0.0


def storyboard_valid(example, prediction, trace=None) -> float:
    try:
        obj = Storyboard.model_validate_json(prediction.storyboard_json)
        checks = [
            bool(obj.goal),
            len(obj.steps) >= 3,
            obj.steps[0].move.value == "hook",
            obj.steps[-1].move.value == "summarize",
        ]
        return sum(checks) / len(checks)
    except Exception:
        return 0.0


def scene_valid(example, prediction, trace=None) -> float:
    try:
        Scene.model_validate_json(prediction.scene_json)
        return 1.0
    except Exception:
        return 0.0
