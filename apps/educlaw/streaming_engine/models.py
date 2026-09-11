"""Data models for EduClaw asynchronous streaming pipeline."""

from __future__ import annotations


class SlideData:
    """Represents a discrete slide with narration, Manim Community visual code, and final flag."""

    def __init__(
        self,
        slide_num: int,
        narration: str,
        python_code: str,
        is_final_slide: bool = False,
        is_final: bool | None = None,
    ):
        self.slide_num = slide_num
        self.narration = narration
        self.python_code = python_code
        final_val = is_final if is_final is not None else is_final_slide
        self.is_final_slide: bool = final_val
        self.is_final: bool = final_val

    def __repr__(self) -> str:
        return (
            f"SlideData(slide_num={self.slide_num}, narration={self.narration[:30]!r}..., "
            f"is_final={self.is_final})"
        )
