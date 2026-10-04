"""Visual code generators package."""

from motiongram.sci.visuals.base import VisualComponent
from motiongram.sci.visuals.dl_visuals import DeepLearningVisualCodeGenerator
from motiongram.sci.visuals.inset import InsetCodeGenerator
from motiongram.sci.visuals.trajectory import TrajectoryCodeGenerator

__all__ = [
    "VisualComponent",
    "TrajectoryCodeGenerator",
    "InsetCodeGenerator",
    "DeepLearningVisualCodeGenerator",
]
