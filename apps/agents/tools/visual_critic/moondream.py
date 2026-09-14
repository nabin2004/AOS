"""Moondream 0.5B / 2B Visual Critic for targeted visual interrogation."""

from __future__ import annotations

import base64
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image

from .base import BaseVisualCritic
from .heuristic import HeuristicVisionCritic
from .types import (
    TARGETED_VISUAL_QUESTIONS,
    VisualCheckItem,
    VisualContext,
    VisualCriticVerdict,
    VisualQuestionDef,
)


class MoondreamCritic(BaseVisualCritic):
    """Visual Critic driven by Moondream 0.5B / Moondream 2.

    Implements a 10-point targeted interrogation protocol:
    Rather than asking a 0.5B model complex mathematical questions, it asks
    tightly-constrained binary visual questions (empty scene, cutoff, overlap, etc.)
    which fit its visual querying and object grounding strengths.
    """

    _cached_model = None
    _cached_tokenizer = None
    _cached_device = None

    def __init__(
        self,
        model_name: str = "vikhyatk/moondream-0_5b",
        device: str = "auto",
        pass_threshold: float = 0.70,
        use_ollama: bool = False,
        ollama_base_url: Optional[str] = None,
    ) -> None:
        super().__init__(model_name=model_name, backend_name="moondream", pass_threshold=pass_threshold)
        self.device = device
        self.use_ollama = use_ollama
        self.ollama_base_url = ollama_base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._fallback_critic = HeuristicVisionCritic()

    def _ensure_local_model(self):
        """Lazy-loads and caches the Moondream model and tokenizer."""
        if MoondreamCritic._cached_model is not None:
            return MoondreamCritic._cached_model, MoondreamCritic._cached_tokenizer, MoondreamCritic._cached_device

        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        if self.device == "auto":
            target_device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            target_device = self.device

        dtype = torch.float16 if target_device == "cuda" else torch.float32

        print(f"[MoondreamCritic] Loading {self.model_name} on {target_device} ({dtype})...", file=sys.stderr)
        tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            trust_remote_code=True,
            torch_dtype=dtype,
        ).to(target_device)
        model.eval()

        MoondreamCritic._cached_model = model
        MoondreamCritic._cached_tokenizer = tokenizer
        MoondreamCritic._cached_device = target_device
        return model, tokenizer, target_device

    def _query_local_moondream(self, image: Image.Image, question: str) -> str:
        """Queries local Moondream model with an image and text question."""
        model, tokenizer, device = self._ensure_local_model()

        # Moondream 0.5B / 2 API
        if hasattr(model, "query"):
            res = model.query(image, question)
            if isinstance(res, dict) and "answer" in res:
                return str(res["answer"]).strip()
            return str(res).strip()

        # HuggingFace standard answer_question pattern
        if hasattr(model, "answer_question"):
            enc_image = model.encode_image(image)
            return model.answer_question(enc_image, question, tokenizer=tokenizer).strip()

        # Generic fallback
        return ""

    def _query_ollama_moondream(self, image_path: Path, question: str) -> str:
        """Queries Moondream via Ollama API."""
        import httpx

        with open(image_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "model": "moondream",
            "prompt": question,
            "images": [b64_data],
            "stream": False,
            "options": {"temperature": 0.0},
        }

        url = f"{self.ollama_base_url.rstrip('/')}/api/generate"
        resp = httpx.post(url, json=payload, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()

    def _ask_question(self, image_path: Path, pil_img: Image.Image, question: str) -> str:
        """Dispatches question to local model or Ollama endpoint."""
        if self.use_ollama:
            try:
                return self._query_ollama_moondream(image_path, question)
            except Exception as exc:
                print(f"[MoondreamCritic] Ollama query failed: {exc}, trying local...", file=sys.stderr)

        return self._query_local_moondream(pil_img, question)

    def critique_frame(
        self,
        image_path: Path | str,
        context: Optional[VisualContext] = None,
    ) -> VisualCriticVerdict:
        img_p = Path(image_path).resolve()
        if not img_p.is_file():
            return self._fallback_critic.critique_frame(image_path, context)

        # Quick heuristic pre-flight: catch pitch black screen immediately
        h_verdict = self._fallback_critic.critique_frame(img_p, context)
        if not h_verdict.passed:
            # If the screen is completely pitch black (mean luminance < 1.5), fail immediately
            for chk in h_verdict.checks:
                if chk.question_id == "scene_empty" and not chk.passed:
                    return self.compile_verdict(
                        checks=h_verdict.checks,
                        keyframe_path=str(img_p),
                        context=context,
                        raw_response={"reason": "Pre-flight heuristic caught empty/black canvas"},
                    )

        try:
            with Image.open(img_p) as raw_img:
                pil_img = raw_img.convert("RGB")

            checks: List[VisualCheckItem] = []
            raw_answers: Dict[str, str] = {}

            # Execute the 10 Targeted Visual Questions
            for q_def in TARGETED_VISUAL_QUESTIONS:
                # Targeted prompt expecting concise answer
                query_prompt = f"{q_def.question} Answer strictly with 'Yes' or 'No'."
                try:
                    ans = self._ask_question(img_p, pil_img, query_prompt)
                except Exception as q_exc:
                    print(f"[MoondreamCritic] Question '{q_def.id}' error: {q_exc}", file=sys.stderr)
                    ans = "unknown"

                raw_answers[q_def.id] = ans
                ans_lower = ans.lower().strip()

                # Determine pass/fail based on bad_answer definition
                is_bad = False
                if q_def.bad_answer == "yes":
                    is_bad = "yes" in ans_lower and "no" not in ans_lower
                elif q_def.bad_answer == "no":
                    is_bad = "no" in ans_lower and "yes" not in ans_lower

                passed = not is_bad
                checks.append(
                    VisualCheckItem(
                        question_id=q_def.id,
                        question_text=q_def.question,
                        passed=passed,
                        raw_answer=ans,
                        detail=f"Answer: {ans}",
                    )
                )

            return self.compile_verdict(
                checks=checks,
                keyframe_path=str(img_p),
                context=context,
                raw_response=raw_answers,
            )

        except Exception as exc:
            print(f"[MoondreamCritic] Execution error ({exc}). Falling back to heuristic critic.", file=sys.stderr)
            verdict = self._fallback_critic.critique_frame(img_p, context)
            verdict.critic_model = f"{self.model_name} (fallback:{verdict.critic_model})"
            return verdict
