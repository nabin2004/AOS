"""Renderer-in-the-Loop (RITL) ManimAgent Self-Correction Pipeline.

Executes Manim scripts against ManimCE 0.19.0 rendering engine. On compilation/runtime error,
extracts traceback logs, retrieves RITL-DOC API documentation, and runs up to 3 self-correction iterations.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

from error_feedback import summarize_diagnostic_output
from ritl_doc_retriever import generate_ritl_doc_prompt_injection

logger = logging.getLogger(__name__)


@dataclass
class RITLExecutionResult:
    success: bool
    iterations: int
    final_code: str
    video_path: Optional[str] = None
    error_log: Optional[str] = None


class RITLManimAgent:
    """Renderer-in-the-Loop Agent for compiling and self-correcting Manim scripts."""

    def __init__(self, max_loops: int = 3, media_dir: str = "./media"):
        self.max_loops = max_loops
        self.media_dir = Path(media_dir)
        self.media_dir.mkdir(parents=True, exist_ok=True)

    def render_script(self, script_code: str, scene_class_name: str = "MainScene") -> Tuple[bool, str, Optional[str]]:
        """Attempts to render Manim script via CLI subprocess."""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp.write(script_code)
            tmp_path = tmp.name

        try:
            cmd = [
                "uv",
                "run",
                "manim",
                "render",
                "-ql",
                "--media_dir",
                str(self.media_dir),
                tmp_path,
                scene_class_name,
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if res.returncode == 0:
                # Find rendered video file
                video_files = list(self.media_dir.glob("**/*.mp4"))
                latest_video = str(video_files[-1]) if video_files else None
                return True, "", latest_video
            else:
                raw_err = res.stderr or res.stdout
                return False, raw_err, None
        except Exception as ex:
            return False, str(ex), None
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def run_self_correction_loop(
        self,
        initial_script: str,
        scene_class_name: str = "MainScene",
        llm_fix_callback: Optional[Any] = None,
    ) -> RITLExecutionResult:
        """Runs RITL self-correction loop up to max_loops attempts."""
        current_script = initial_script
        last_error = ""

        for loop in range(1, self.max_loops + 1):
            logger.info(f"RITL Execution Loop {loop}/{self.max_loops}...")
            success, raw_error, video_path = self.render_script(current_script, scene_class_name)

            if success:
                logger.info(f"RITL rendering succeeded on iteration {loop}!")
                return RITLExecutionResult(
                    success=True,
                    iterations=loop,
                    final_code=current_script,
                    video_path=video_path,
                )

            # Step 1: Extract traceback (last 10 lines / collapsed diagnostic summary)
            tb_summary = summarize_diagnostic_output(raw_error, max_chars=1000, max_errors=3)
            last_error = tb_summary

            # Step 2: RITL-DOC API Document Retrieval
            doc_context = generate_ritl_doc_prompt_injection(current_script, tb_summary)

            # Step 3: Format correction prompt
            correction_prompt = (
                f"### Manim Script Render Failure (Iteration {loop}/{self.max_loops})\n\n"
                f"**Error Traceback Summary:**\n```\n{tb_summary}\n```\n\n"
                f"{doc_context}\n\n"
                f"**Failing Script Code:**\n```python\n{current_script}\n```\n\n"
                f"Please fix all syntax and API keyword errors and return the complete corrected Python code."
            )

            logger.warning(f"RITL Loop {loop} failed with error:\n{tb_summary[:200]}...")

            if llm_fix_callback:
                current_script = llm_fix_callback(correction_prompt)
            else:
                # Mock heuristic correction for testing/demonstration if no LLM callback provided
                break

        return RITLExecutionResult(
            success=False,
            iterations=self.max_loops,
            final_code=current_script,
            error_log=last_error,
        )
