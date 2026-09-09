"""Gemma / PaliGemma Visual-Language Model (VLM) Judge for GRPO.

Disaggregated multi-modal evaluator running strictly on GPU 1 (cuda:1):
- Evaluates spatial alignment, mathematical correctness, layout clarity, and label placement.
- Operates in 4-bit NF4 quantization (~2.2-2.5 GB VRAM footprint on 16 GB card).
- Uses 448px resolution (paligemma2-3b-mix-448) for high visual acuity on LaTeX notation.
- Employs single-forward-pass direct logit scoring over rating tokens (1..5) to achieve ~15-25ms latency with 100% deterministic, continuous scoring without autoregressive decode hangs.
- Supports Cascading Reward Filter (Ensemble):
    Stage 1: OpenCLIP fast filter (< 0.15 similarity drops immediately).
    Stage 2: PaliGemma Expert Grader on candidate frames passing threshold.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import torch
except ImportError:
    torch = None

# Global cached judge instance (singleton per process on reward device)
_GLOBAL_GEMMA_JUDGE: Optional["GemmaVisualJudge"] = None

DEFAULT_VLM_MODEL = "google/paligemma2-3b-mix-448"
DEFAULT_VLM_THRESHOLD = 0.15


def parse_score_from_response(text: str) -> float:
    """Robust regex extraction of scalar score [0.0, 1.0] from short VLM output."""
    if not text:
        return 0.5

    clean = text.strip()

    # 1. Fraction format: e.g. "8/10", "4/5", "9/10"
    frac_match = re.search(r"\b([0-9]|10)\s*/\s*(10|5)\b", clean)
    if frac_match:
        try:
            num = float(frac_match.group(1))
            denom = float(frac_match.group(2))
            if denom > 0:
                return max(0.0, min(1.0, round(num / denom, 4)))
        except (ValueError, ZeroDivisionError):
            pass

    # 2. Keyed or direct decimal: "SCORE: 0.85", "Score: 1.0", "0.75", "1.0", "0"
    score_match = re.search(
        r"(?:score|rating|grade)?\s*[:=]?\s*([0-1](?:\.\d+)?)\b",
        clean,
        re.IGNORECASE,
    )
    if score_match:
        try:
            val = float(score_match.group(1))
            return max(0.0, min(1.0, round(val, 4)))
        except ValueError:
            pass

    # 3. Integer on 1-10 or 1-5 scale
    int_match = re.search(r"\b([0-9]|10)\b", clean)
    if int_match:
        try:
            val = float(int_match.group(1))
            if val <= 1.0:
                return val
            if val <= 5.0:
                return round(val / 5.0, 4)
            if val <= 10.0:
                return round(val / 10.0, 4)
        except ValueError:
            pass

    # 4. Keyword heuristics fallback
    lowered = clean.lower()
    if any(w in lowered for w in ("yes", "correct", "good", "clean", "accurate", "pass")):
        return 0.9
    if any(w in lowered for w in ("no", "incorrect", "bad", "blank", "chaotic", "fail")):
        return 0.1

    return 0.5


class GemmaVisualJudge:
    """4-bit Gemma / PaliGemma VLM evaluator isolated to GPU 1."""

    def __init__(
        self,
        model_id: Optional[str] = None,
        device: Optional[str] = None,
        load_in_4bit: bool = True,
        max_new_tokens: int = 4,
    ) -> None:
        self.model_id = model_id or os.environ.get("AOS_VLM_MODEL", DEFAULT_VLM_MODEL)
        self.device_str = device or os.environ.get("AOS_REWARD_DEVICE", "cuda:1")
        self.load_in_4bit = load_in_4bit
        self.max_new_tokens = max_new_tokens

        self.rating_tokens = ["1", "2", "3", "4", "5"]
        self.rating_token_ids: Optional[list[int]] = None

        self.model = None
        self.processor = None
        self._is_loaded = False

    def load(self) -> None:
        """Loads the VLM model onto the dedicated reward GPU."""
        if self._is_loaded:
            return

        if torch is None:
            raise RuntimeError("PyTorch is required for GemmaVisualJudge.")

        target_device = self.device_str
        if not torch.cuda.is_available():
            target_device = "cpu"
        elif target_device.startswith("cuda:") and int(target_device.split(":")[1]) >= torch.cuda.device_count():
            target_device = "cuda:0"

        # Determine device map for bitsandbytes / accelerate
        if target_device.startswith("cuda:"):
            cuda_idx = int(target_device.split(":")[1])
            device_map = {"": cuda_idx}
        elif target_device == "cuda":
            device_map = {"": 0}
        else:
            device_map = {"": "cpu"}

        from transformers import AutoProcessor, BitsAndBytesConfig

        token = os.environ.get("HF_TOKEN")

        use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
        compute_dtype = torch.bfloat16 if use_bf16 else torch.float16

        quant_config = None
        if self.load_in_4bit and target_device != "cpu":
            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=compute_dtype,
                bnb_4bit_use_double_quant=True,
            )

        print(
            f"[VLM Judge] Loading {self.model_id} on {target_device} (4-bit={self.load_in_4bit})...",
            file=sys.stderr,
            flush=True,
        )

        # 1. Load processor
        self.processor = AutoProcessor.from_pretrained(
            self.model_id,
            token=token,
            trust_remote_code=True,
        )

        # 2. Load model (prefer PaliGemmaForConditionalGeneration, fallback to Vision2Seq or AutoModel)
        try:
            from transformers import PaliGemmaForConditionalGeneration

            self.model = PaliGemmaForConditionalGeneration.from_pretrained(
                self.model_id,
                device_map=device_map,
                quantization_config=quant_config,
                torch_dtype=compute_dtype,
                token=token,
                trust_remote_code=True,
            )
        except Exception:
            try:
                from transformers import AutoModelForVision2Seq

                self.model = AutoModelForVision2Seq.from_pretrained(
                    self.model_id,
                    device_map=device_map,
                    quantization_config=quant_config,
                    torch_dtype=compute_dtype,
                    token=token,
                    trust_remote_code=True,
                )
            except Exception:
                from transformers import AutoModelForCausalLM

                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_id,
                    device_map=device_map,
                    quantization_config=quant_config,
                    torch_dtype=compute_dtype,
                    token=token,
                    trust_remote_code=True,
                )

        self.model.eval()

        # Pre-cache rating token IDs for fast direct logit scoring
        try:
            tokenizer = getattr(self.processor, "tokenizer", self.processor)
            self.rating_token_ids = [
                tokenizer.encode(t, add_special_tokens=False)[-1]
                for t in self.rating_tokens
            ]
        except Exception as e:
            print(f"[VLM Judge] Note: Could not pre-cache rating token IDs: {e}", file=sys.stderr)
            self.rating_token_ids = None

        self._is_loaded = True
        print(f"✔ [VLM Judge] Successfully initialized {self.model_id} on {target_device}.", file=sys.stderr, flush=True)

    def evaluate_frame(
        self,
        image: Union[Any, str, Path],
        prompt: str,
    ) -> float:
        """Evaluates an individual image frame against the animation prompt."""
        if not self._is_loaded:
            self.load()

        if Image is None:
            return 0.5

        if isinstance(image, (str, Path)):
            img_path = Path(image)
            if not img_path.is_file():
                return 0.0
            pil_img = Image.open(img_path).convert("RGB")
        elif isinstance(image, Image.Image):
            pil_img = image.convert("RGB")
        else:
            return 0.5

        # Clean prompt
        clean_prompt = prompt.split("Output a complete Scene class in a ```python fence.")[-1].strip()
        if not clean_prompt:
            clean_prompt = prompt[:200]
        else:
            clean_prompt = clean_prompt[:250]

        eval_prompt = (
            f"Rate the visual clarity, mathematical notation, and layout of this animation frame "
            f"for '{clean_prompt}' from 1 to 5:"
        )

        try:
            target_device = self.device_str if torch.cuda.is_available() else "cpu"
            if target_device.startswith("cuda:") and int(target_device.split(":")[1]) >= torch.cuda.device_count():
                target_device = "cuda:0"

            inputs = self.processor(
                text=eval_prompt,
                images=pil_img,
                return_tensors="pt",
            )
            inputs = {k: v.to(target_device) if hasattr(v, "to") else v for k, v in inputs.items()}

            # 1. Direct logit evaluation (Single forward pass, ~15-25ms latency, deterministic)
            if self.rating_token_ids is None and self.processor is not None:
                try:
                    tokenizer = getattr(self.processor, "tokenizer", self.processor)
                    self.rating_token_ids = [
                        tokenizer.encode(t, add_special_tokens=False)[-1]
                        for t in self.rating_tokens
                    ]
                except Exception:
                    pass

            if self.rating_token_ids and hasattr(self.model, "__call__"):
                with torch.inference_mode():
                    outputs = self.model(**inputs)
                    if hasattr(outputs, "logits"):
                        # Extract logits at the final prompt token position
                        last_logits = outputs.logits[:, -1, :]  # [batch_size, vocab_size]
                        candidate_logits = last_logits[0, self.rating_token_ids]  # [5]
                        probs = torch.softmax(candidate_logits, dim=-1)
                        # Continuous expectation mapped from Likert 1..5 to [0.0, 1.0]:
                        # 1 -> 0.0, 2 -> 0.25, 3 -> 0.50, 4 -> 0.75, 5 -> 1.0
                        weights = torch.tensor([0.0, 0.25, 0.50, 0.75, 1.0], device=candidate_logits.device)
                        score = torch.sum(probs * weights).item()
                        return max(0.0, min(1.0, round(score, 4)))

            # 2. Fallback to autoregressive generation if logit extraction is unavailable
            with torch.inference_mode():
                generated_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=self.max_new_tokens,
                    do_sample=False,
                )

            input_len = inputs["input_ids"].shape[1]
            output_tokens = generated_ids[0, input_len:]
            output_text = self.processor.decode(output_tokens, skip_special_tokens=True).strip()

            score = parse_score_from_response(output_text)
            return score
        except Exception as e:
            print(f"Warning: Gemma VLM evaluation encountered error: {e}", file=sys.stderr)
            return 0.5

    def evaluate_video(
        self,
        video_path: Union[str, Path],
        prompt: str,
        peak_frame: Optional[Any] = None,
    ) -> float:
        """Evaluates a rendered video, using either pre-extracted peak frame or mid/end frame."""
        if peak_frame is not None:
            return self.evaluate_frame(peak_frame, prompt)

        try:
            from reward_model.clip_reward import extract_frames_from_video

            frames = extract_frames_from_video(video_path, fps=2.0)
            if not frames:
                return 0.0
            # Default to the frame near the end (80% point) where animations are settled
            target_idx = min(len(frames) - 1, max(0, int(len(frames) * 0.8)))
            _, selected_img = frames[target_idx]
            return self.evaluate_frame(selected_img, prompt)
        except Exception:
            return 0.0


def get_gemma_judge(
    model_id: Optional[str] = None,
    device: Optional[str] = None,
) -> GemmaVisualJudge:
    """Returns singleton GemmaVisualJudge instance."""
    global _GLOBAL_GEMMA_JUDGE
    if _GLOBAL_GEMMA_JUDGE is None:
        _GLOBAL_GEMMA_JUDGE = GemmaVisualJudge(model_id=model_id, device=device)
    return _GLOBAL_GEMMA_JUDGE


def evaluate_cascading_ensemble(
    video_path: Union[str, Path],
    prompt: str,
    threshold: float = DEFAULT_VLM_THRESHOLD,
    device: Optional[str] = None,
    model_id: Optional[str] = None,
) -> Tuple[float, Dict[str, Any]]:
    """Cascading Reward Filter:
    1. Fast Filter (OpenCLIP): Sub-second check. If clip_score < threshold, drop immediately and skip Gemma.
    2. Expert Grader (Gemma VLM): Evaluates mathematical layout on peak frame passing threshold.
    3. Blended Score: 0.30 * clip_score + 0.70 * gemma_score.
    """
    try:
        from reward_model.clip_reward import compute_prompt_image_clip_reward_with_frame

        clip_score, peak_frame = compute_prompt_image_clip_reward_with_frame(
            video_path=video_path,
            prompt=prompt,
            fps=2.0,
            device=device,
        )
    except Exception as e:
        print(f"Warning: OpenCLIP filter encountered error: {e}", file=sys.stderr)
        clip_score, peak_frame = 0.0, None

    # Step 1: Filter threshold check
    if clip_score < threshold or peak_frame is None:
        return clip_score, {
            "status": "clip_filter_cutoff",
            "clip_score": clip_score,
            "gemma_score": None,
            "blended": clip_score,
        }

    # Step 2: Expert grader on peak frame
    judge = get_gemma_judge(model_id=model_id, device=device)
    gemma_score = judge.evaluate_frame(peak_frame, prompt)

    # Step 3: Ensemble blend
    blended = round(0.30 * clip_score + 0.70 * gemma_score, 4)
    return blended, {
        "status": "ensemble_evaluated",
        "clip_score": clip_score,
        "gemma_score": gemma_score,
        "blended": blended,
    }
