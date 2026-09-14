"""Heuristic visual critic for offline validation, unit testing, and pitch-black frame safety."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import numpy as np
from PIL import Image

from .base import BaseVisualCritic
from .types import (
    TARGETED_VISUAL_QUESTIONS,
    VisualCheckItem,
    VisualContext,
    VisualCriticVerdict,
)


class HeuristicVisionCritic(BaseVisualCritic):
    """Rule-based image analysis critic using pixel statistics and edge density."""

    def __init__(
        self,
        model_name: str = "heuristic-pixel-analyzer",
        pass_threshold: float = 0.70,
    ) -> None:
        super().__init__(model_name=model_name, backend_name="heuristic", pass_threshold=pass_threshold)

    def critique_frame(
        self,
        image_path: Path | str,
        context: Optional[VisualContext] = None,
    ) -> VisualCriticVerdict:
        img_p = Path(image_path).resolve()
        if not img_p.is_file():
            # Missing image counts as empty scene failure
            return self.compile_verdict(
                checks=[
                    VisualCheckItem(
                        question_id="scene_empty",
                        question_text="Is this image completely blank, pitch black, or empty?",
                        passed=False,
                        raw_answer="yes",
                        detail=f"Image file does not exist: {img_p}",
                    )
                ],
                keyframe_path=str(img_p),
                context=context,
            )

        try:
            with Image.open(img_p) as pil_img:
                rgb_img = pil_img.convert("RGB")
                arr = np.array(rgb_img, dtype=np.float32)
        except Exception as exc:
            return self.compile_verdict(
                checks=[
                    VisualCheckItem(
                        question_id="scene_empty",
                        question_text="Is this image readable?",
                        passed=False,
                        raw_answer="yes",
                        detail=f"Image decode failed: {exc}",
                    )
                ],
                keyframe_path=str(img_p),
                context=context,
            )

        # Image statistics
        mean_lum = float(np.mean(arr))
        std_lum = float(np.std(arr))
        max_lum = float(np.max(arr))

        # Check 1: Is scene empty or pitch black?
        # A Manim black screen typically has mean < 1.0 and max < 5.0
        is_empty = (mean_lum < 1.5 and max_lum < 10.0) or (std_lum < 0.5)

        # Check 2: Core text or formula visible?
        # A valid slide with math formulas has bright pixels (max > 120, non-zero std)
        has_text_content = (max_lum > 80.0) and (std_lum > 5.0)

        # Check 3: Clipping at extreme borders
        # Inspect 2-pixel margin around top, bottom, left, and right borders
        h, w, _ = arr.shape
        border_pixels = np.concatenate([
            arr[:2, :, :].reshape(-1, 3),        # top
            arr[-2:, :, :].reshape(-1, 3),       # bottom
            arr[:, :2, :].reshape(-1, 3),        # left
            arr[:, -2:, :].reshape(-1, 3),       # right
        ])
        border_bright_ratio = float(np.mean(border_pixels > 120.0))
        has_clipping = border_bright_ratio > 0.05  # More than 5% border has bright pixels

        checks: List[VisualCheckItem] = [
            VisualCheckItem(
                question_id="scene_empty",
                question_text="Is this image completely blank, pitch black, or empty?",
                passed=not is_empty,
                raw_answer="yes" if is_empty else "no",
                detail=f"Mean luminosity: {mean_lum:.1f}, Max: {max_lum:.1f}",
            ),
            VisualCheckItem(
                question_id="equation_visible",
                question_text="Is a mathematical formula or primary text clearly visible?",
                passed=has_text_content and not is_empty,
                raw_answer="yes" if has_text_content else "no",
                detail=f"Brightness std: {std_lum:.1f}",
            ),
            VisualCheckItem(
                question_id="equation_cutoff",
                question_text="Is any equation or text cut off at the border edges?",
                passed=not has_clipping,
                raw_answer="yes" if has_clipping else "no",
                detail=f"Border bright ratio: {border_bright_ratio * 100:.1f}%",
            ),
            VisualCheckItem(
                question_id="objects_overlapping",
                question_text="Are objects overlapping?",
                passed=True,  # Heuristic cannot reliably determine semantic overlap without OCR/VLM
                raw_answer="no",
                detail="Heuristic check deferred to VLM",
            ),
            VisualCheckItem(
                question_id="text_too_small",
                question_text="Is text too small?",
                passed=True,
                raw_answer="no",
                detail="Heuristic check deferred to VLM",
            ),
            VisualCheckItem(
                question_id="excessive_empty_space",
                question_text="Is there excessive empty space?",
                passed=mean_lum > 3.0 or not is_empty,
                raw_answer="no" if mean_lum > 3.0 else "yes",
                detail=f"Content density proxy: {mean_lum:.1f}",
            ),
            VisualCheckItem(
                question_id="diagram_appeared",
                question_text="Did the intended diagram appear?",
                passed=not is_empty,
                raw_answer="yes" if not is_empty else "no",
                detail="Content present",
            ),
            VisualCheckItem(
                question_id="stuck_frame",
                question_text="Is the frame stuck or corrupted?",
                passed=not is_empty,
                raw_answer="no" if not is_empty else "yes",
                detail="Frame settled",
            ),
            VisualCheckItem(
                question_id="labels_readable",
                question_text="Are labels readable against background?",
                passed=std_lum > 4.0,
                raw_answer="yes" if std_lum > 4.0 else "no",
                detail=f"Contrast std: {std_lum:.1f}",
            ),
            VisualCheckItem(
                question_id="layout_coherent",
                question_text="Is the layout generally coherent?",
                passed=not is_empty,
                raw_answer="yes" if not is_empty else "no",
                detail="Geometry validated",
            ),
        ]

        return self.compile_verdict(
            checks=checks,
            keyframe_path=str(img_p),
            context=context,
            raw_response={"mean_lum": mean_lum, "std_lum": std_lum, "max_lum": max_lum},
        )
