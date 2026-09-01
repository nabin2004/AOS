"""ManiBench Evaluation Callback for Hugging Face Trainer.

Evaluates fine-tuned LLM on ManiBench prompts after each epoch,
calculates Executability, VCER, Alignment, Coverage, and Overall metrics,
and logs results directly to Weights & Biases (W&B).
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

import torch
from transformers import TrainerCallback, TrainerControl, TrainerState, TrainingArguments

logger = logging.getLogger(__name__)

MANIBENCH_PATH = Path(__file__).resolve().parent.parent / "ManiBench"
if str(MANIBENCH_PATH) not in sys.path:
    sys.path.insert(0, str(MANIBENCH_PATH))

try:
    from evaluation.metrics import (
        compute_alignment,
        compute_coverage,
        compute_executability,
        detect_version_conflicts,
    )
    _MANIBENCH_AVAILABLE = True
except Exception as _exc:
    logger.warning(f"ManiBench metrics import failed: {_exc}")
    _MANIBENCH_AVAILABLE = False


def _extract_code_fence(text: str) -> str:
    match = re.search(r"```(?:python)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


class ManiBenchEvalCallback(TrainerCallback):
    """Hugging Face TrainerCallback for epoch-end ManiBench evaluation."""

    def __init__(
        self,
        render: bool = False,
        timeout: int = 20,
        max_samples: int | None = None,
        prompts_path: Path | None = None,
    ) -> None:
        super().__init__()
        self.render = render
        self.timeout = timeout
        self.max_samples = max_samples
        self.dataset_path = prompts_path or (MANIBENCH_PATH / "ManiBench_Pilot_Dataset.json")
        self.problems: list[dict[str, Any]] = self._load_problems()

    def _load_problems(self) -> list[dict[str, Any]]:
        if not self.dataset_path.is_file():
            logger.warning(f"ManiBench dataset file not found at {self.dataset_path}")
            return []
        try:
            with open(self.dataset_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            problems = data.get("problems") or data.get("pilot_problems") or []
            if self.max_samples and self.max_samples > 0:
                problems = problems[: self.max_samples]
            return problems
        except Exception as exc:
            logger.warning(f"Failed to load ManiBench dataset: {exc}")
            return []

    def on_epoch_end(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        model: Any = None,
        tokenizer: Any = None,
        **kwargs: Any,
    ) -> None:
        if not _MANIBENCH_AVAILABLE or not self.problems or model is None or tokenizer is None:
            return

        print(f"\n==> Running ManiBench evaluation (Epoch {state.epoch:.1f})...")

        # Set evaluation mode
        was_training = model.training
        model.eval()
        device = next(model.parameters()).device

        exec_scores: list[float] = []
        vcer_scores: list[float] = []
        align_scores: list[float] = []
        cover_scores: list[float] = []
        overall_scores: list[float] = []

        prompt_prefix = (
            "Write valid Manim Community Edition (CE) Python code.\n"
            "Use `from manim import *`. Output a complete Scene class in a ```python fence.\n\n"
        )

        for problem in self.problems:
            full_prompt = prompt_prefix + (problem.get("full_prompt") or problem.get("prompt") or "")
            messages = [{"role": "user", "content": full_prompt}]

            try:
                if hasattr(tokenizer, "apply_chat_template"):
                    input_text = tokenizer.apply_chat_template(
                        messages, tokenize=False, add_generation_prompt=True
                    )
                else:
                    input_text = full_prompt

                inputs = tokenizer(input_text, return_tensors="pt").to(device)

                with torch.no_grad():
                    outputs = model.generate(
                        **inputs,
                        max_new_tokens=1024,
                        do_sample=False,
                        temperature=0.0,
                        pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                    )

                generated_text = tokenizer.decode(
                    outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True
                )
                code = _extract_code_fence(generated_text)

                # Compute Metrics
                exec_res = compute_executability(
                    code, timeout=self.timeout, skip_render=not self.render
                )
                exec_val = float(exec_res.get("executability", 0))

                vc_res = detect_version_conflicts(code)
                vcer_val = float(vc_res.get("version_conflict_rate", 0.0))

                align_res = compute_alignment(
                    code, problem.get("required_visual_events", [])
                )
                align_val = float(align_res.get("alignment_score", 0.0))

                cover_res = compute_coverage(
                    code, problem.get("coverage_requirements", {})
                )
                cover_val = float(cover_res.get("coverage_score", 0.0))

                overall_val = (
                    0.50 * exec_val
                    + 0.25 * align_val
                    + 0.15 * (1.0 - vcer_val)
                    + 0.10 * cover_val
                )

                exec_scores.append(exec_val)
                vcer_scores.append(vcer_val)
                align_scores.append(align_val)
                cover_scores.append(cover_val)
                overall_scores.append(overall_val)

            except Exception as exc:
                logger.warning(f"Error evaluating ManiBench problem {problem.get('id')}: {exc}")
                exec_scores.append(0.0)
                vcer_scores.append(1.0)
                align_scores.append(0.0)
                cover_scores.append(0.0)
                overall_scores.append(0.0)

        n = len(self.problems)
        metrics = {
            "eval/manibench_executability": sum(exec_scores) / n if n else 0.0,
            "eval/manibench_vcer": sum(vcer_scores) / n if n else 0.0,
            "eval/manibench_alignment": sum(align_scores) / n if n else 0.0,
            "eval/manibench_coverage": sum(cover_scores) / n if n else 0.0,
            "eval/manibench_overall": sum(overall_scores) / n if n else 0.0,
        }

        print(
            f"--> ManiBench Eval Results (Epoch {state.epoch:.1f}):\n"
            f"    Executability: {metrics['eval/manibench_executability'] * 100:.1f}%\n"
            f"    VCER:          {metrics['eval/manibench_vcer'] * 100:.1f}%\n"
            f"    Alignment:     {metrics['eval/manibench_alignment'] * 100:.1f}%\n"
            f"    Coverage:      {metrics['eval/manibench_coverage'] * 100:.1f}%\n"
            f"    Overall Score: {metrics['eval/manibench_overall'] * 100:.1f}%\n"
        )

        state.log_history.append(metrics)
        control.should_log = True

        if was_training:
            model.train()
