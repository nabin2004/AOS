"""
DSPy programs: multi-step LLM pipelines for AOS IR generation.
"""
import dspy

from .signatures import BuildScene, ClassifyRequest, PlanLecture, PlanStoryboard


class ClassifierProgram(dspy.Module):
    """Single-step: user request → subject + topic."""

    def __init__(self):
        self.predict = dspy.Predict(ClassifyRequest)

    def forward(self, user_request: str):
        return self.predict(user_request=user_request)


class LecturePlannerProgram(dspy.Module):
    """Two-step: classify → lecture plan."""

    def __init__(self):
        self.classify = dspy.Predict(ClassifyRequest)
        self.plan = dspy.Predict(PlanLecture)

    def forward(self, user_request: str):
        cls = self.classify(user_request=user_request)
        lecture = self.plan(topic=cls.topic, subject=cls.subject)
        return dspy.Prediction(
            subject=cls.subject,
            topic=cls.topic,
            lecture_json=lecture.lecture_json,
        )


class StoryboardProgram(dspy.Module):
    """Three-step: classify → lecture → storyboard."""

    def __init__(self):
        self.classify = dspy.Predict(ClassifyRequest)
        self.plan_lecture = dspy.Predict(PlanLecture)
        self.plan_storyboard = dspy.Predict(PlanStoryboard)

    def forward(self, user_request: str):
        cls = self.classify(user_request=user_request)
        lecture = self.plan_lecture(topic=cls.topic, subject=cls.subject)
        storyboard = self.plan_storyboard(
            topic=cls.topic,
            objectives=lecture.lecture_json,
        )
        return dspy.Prediction(
            topic=cls.topic,
            lecture_json=lecture.lecture_json,
            storyboard_json=storyboard.storyboard_json,
        )


class SceneBuilderProgram(dspy.Module):
    """Build one scene from a storyboard step."""

    def __init__(self):
        self.build = dspy.Predict(BuildScene)

    def forward(self, move: str, goal: str, topic: str):
        return self.build(move=move, goal=goal, topic=topic)
