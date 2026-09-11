from dataclasses import dataclass

@dataclass
class SlideData:
    narration: str
    python_code: str
    is_final_slide: bool = False
