from .classification import Classification, CLASSIFICATION_PROMPT
from .lecture import LECTURE_PROMPT as lecture_instruction
from .storyboard import storyboard_instruction
from .scene import scene_instruction
from .beat import beat_instruction

__all__ = [
    "Classification",
    "CLASSIFICATION_PROMPT",
    "lecture_instruction",
    "storyboard_instruction",
    "scene_instruction",
    "beat_instruction",
]
