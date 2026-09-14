"""Abstract base class and shared utilities for visual critics."""

from __future__ import annotations

import abc
import subprocess
from pathlib import Path
from typing import List, Optional

from .types import (
    TARGETED_VISUAL_QUESTIONS,
    VisualCheckItem,
    VisualContext,
    VisualCriticVerdict,
    VisualQuestionDef,
)


class BaseVisualCritic(abc.ABC):
    """Abstract visual critic interface."""

    def __init__(
        self,
        model_name: str,
        backend_name: str,
        pass_threshold: float = 0.70,
    ) -> None:
        self.model_name = model_name
        self.backend_name = backend_name
        self.pass_threshold = pass_threshold

    @property
    def name(self) -> str:
        return f"{self.backend_name}:{self.model_name}"

    @abc.abstractmethod
    def critique_frame(
        self,
        image_path: Path | str,
        context: Optional[VisualContext] = None,
    ) -> VisualCriticVerdict:
        """Critiques a single image keyframe using the 10-question interrogation protocol."""
        pass

    def critique_video(
        self,
        video_path: Path | str,
        context: Optional[VisualContext] = None,
        output_frame_path: Optional[Path | str] = None,
    ) -> VisualCriticVerdict:
        """Extracts the final settled keyframe from a video and critiques it."""
        frame = self.extract_keyframe(video_path, output_frame_path)
        return self.critique_frame(frame, context)

    def extract_keyframe(
        self,
        video_path: Path | str,
        output_path: Optional[Path | str] = None,
        from_end_seconds: float = 0.2,
    ) -> Path:
        """Extracts the final settled frame from an MP4 video using ffmpeg."""
        in_vid = Path(video_path).resolve()
        if not in_vid.is_file():
            raise FileNotFoundError(f"Video file not found for keyframe extraction: {in_vid}")

        if output_path:
            out_img = Path(output_path).resolve()
        else:
            out_img = in_vid.parent / f"{in_vid.stem}_keyframe.png"

        out_img.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg",
            "-y",
            "-sseof",
            f"-{from_end_seconds}",
            "-i",
            str(in_vid),
            "-frames:v",
            "1",
            "-update",
            "1",
            str(out_img),
        ]

        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
            if res.returncode != 0 or not out_img.is_file() or out_img.stat().st_size == 0:
                # Fallback: extract at timestamp 00:00:01
                cmd_fallback = [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    "00:00:01",
                    "-i",
                    str(in_vid),
                    "-frames:v",
                    "1",
                    "-update",
                    "1",
                    str(out_img),
                ]
                subprocess.run(cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        except Exception:
            pass

        return out_img

    def compile_verdict(
        self,
        checks: List[VisualCheckItem],
        keyframe_path: Optional[str] = None,
        context: Optional[VisualContext] = None,
        raw_response: Optional[dict] = None,
    ) -> VisualCriticVerdict:
        """Aggregates individual visual check results into a final scored verdict."""
        q_map: dict[str, VisualQuestionDef] = {q.id: q for q in TARGETED_VISUAL_QUESTIONS}

        score = 1.0
        has_critical_failure = False
        detected_issues: List[str] = []
        suggested_fixes: List[str] = []

        for chk in checks:
            q_def = q_map.get(chk.question_id)
            if not chk.passed:
                if q_def:
                    score -= q_def.penalty
                    if q_def.is_critical:
                        has_critical_failure = True
                    desc = q_def.defect_desc
                    if chk.detail:
                        desc = f"{desc} ({chk.detail})"
                    detected_issues.append(desc)
                    if q_def.suggested_fix not in suggested_fixes:
                        suggested_fixes.append(q_def.suggested_fix)
                else:
                    score -= 0.2
                    detected_issues.append(f"Visual check '{chk.question_id}' failed.")

        score = max(0.0, min(1.0, round(score, 2)))
        passed = (not has_critical_failure) and (score >= self.pass_threshold)

        feedback_prompt = self.build_repair_feedback(detected_issues, suggested_fixes, context)

        return VisualCriticVerdict(
            passed=passed,
            score=score,
            critic_model=self.model_name,
            backend=self.backend_name,
            checks=checks,
            detected_issues=detected_issues,
            suggested_fixes=suggested_fixes,
            feedback_for_code_repair=feedback_prompt,
            raw_response=raw_response or {},
            keyframe_path=str(keyframe_path) if keyframe_path else None,
        )

    def build_repair_feedback(
        self,
        detected_issues: List[str],
        suggested_fixes: List[str],
        context: Optional[VisualContext] = None,
    ) -> str:
        """Formats actionable feedback for the Manim code repair prompt."""
        if not detected_issues:
            return "Visual quality control passed. No repairs needed."

        lines = [
            "### VISUAL CRITIC FEEDBACK & REPAIR REQUIREMENTS:",
            "The previous rendered keyframe contained the following visual defects:",
        ]
        for idx, issue in enumerate(detected_issues, 1):
            lines.append(f"{idx}. {issue}")

        if suggested_fixes:
            lines.append("\nRequired Adjustments in Manim Code:")
            for idx, fix in enumerate(suggested_fixes, 1):
                lines.append(f"- {fix}")

        if context and context.latex_formula:
            lines.append(f"\nEnsure the main formula is centered and fully visible within [-6, 6]: {context.latex_formula}")

        lines.append(
            "\nOutput ONLY clean, executable Python Manim statements that fix these defects without clipping or overlap."
        )
        return "\n".join(lines)
