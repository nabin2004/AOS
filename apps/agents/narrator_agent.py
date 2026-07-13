from pydantic import BaseModel, Field, model_validator
from pydantic_ai import Agent
from typing import List, Optional, Literal, Union
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

class SegmentType(str, Enum):
    PLAY = "play"
    BEAT = "beat"

class BaseSegment(BaseModel):
    type: SegmentType
    duration: float = Field(gt=0, description="Duration in seconds")
    movements_needed: Optional[List[str]] = Field(
        None, description="List of movements needed for this segment"
    )

class PlaySegment(BaseSegment):
    type: Literal[SegmentType.PLAY] = SegmentType.PLAY
    animation_instruction: Optional[str] = None
    # maybe background music, etc.

class BeatSegment(BaseSegment):
    type: Literal[SegmentType.BEAT] = SegmentType.BEAT
    narration_text: str
    audio_path: Optional[str] = None

Segment = Union[PlaySegment, BeatSegment]

class NarrationPlan(BaseModel):
    """
    Pydantic model for a narration agent consisting of alternating play and beat segments.
    """
    title: str
    segments: List[Segment] = Field(..., min_length=1)

    @model_validator(mode='after')
    def validate_alternation(self):
        for i in range(len(self.segments)-1):
            if self.segments[i].type == self.segments[i+1].type:
                raise ValueError("Segments must alternate between play and beat.")
        return self


narrator_agent = Agent(
    'openrouter:openai/gpt-4o-mini',
    name='Narrator Agent',
    system_prompt="You generate a JSON narration plan with alternating plays and beats.",
    output_type=NarrationPlan,
    retries=2,
)