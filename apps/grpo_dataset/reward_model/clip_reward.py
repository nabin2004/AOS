"""Live OpenCLIP video reward model for ManiBench GRPO.

Computes multi-modal visual alignment rewards by:
1. Extracting frames from rendered Manim .mp4 videos at ~2 FPS.
2. Generating normalized vision embeddings using OpenCLIP / HuggingFace CLIP.
3. Scoring temporal alignment against per-event `clip_query` strings within `expected_time_range`.
4. Calculating dynamic event rewards combining presence, peak similarity, and temporal window adherence.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import torch
except ImportError:
    torch = None

# Global cached model and processor to avoid reloading per rollout
_CLIP_MODEL = None
_CLIP_PREPROCESS = None
_CLIP_TOKENIZER = None
_CLIP_BACKEND = None  # "open_clip" or "transformers"
_DEVICE = None


def _get_device() -> str:
    global _DEVICE
    if _DEVICE is None:
        if torch is not None and torch.cuda.is_available():
            _DEVICE = "cuda"
        else:
            _DEVICE = "cpu"
    return _DEVICE


def load_clip_model(
    model_name: str = "ViT-B-32",
    pretrained: str = "openai",
    device: Optional[str] = None,
) -> Tuple[Any, Any, Any]:
    """Lazy singleton loader for CLIP model and preprocessor."""
    global _CLIP_MODEL, _CLIP_PREPROCESS, _CLIP_TOKENIZER, _CLIP_BACKEND

    if _CLIP_MODEL is not None:
        return _CLIP_MODEL, _CLIP_PREPROCESS, _CLIP_TOKENIZER

    target_device = device or _get_device()

    # Strategy 1: Try open_clip_torch
    try:
        import open_clip

        model, _, preprocess = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained, device=target_device
        )
        tokenizer = open_clip.get_tokenizer(model_name)
        model.eval()

        _CLIP_MODEL = model
        _CLIP_PREPROCESS = preprocess
        _CLIP_TOKENIZER = tokenizer
        _CLIP_BACKEND = "open_clip"
        return _CLIP_MODEL, _CLIP_PREPROCESS, _CLIP_TOKENIZER
    except Exception as e:
        pass

    # Strategy 2: Fallback to transformers.CLIPModel
    try:
        from transformers import CLIPModel, CLIPProcessor, CLIPTokenizerFast

        hf_model_id = "openai/clip-vit-base-patch32"
        model = CLIPModel.from_pretrained(hf_model_id).to(target_device)
        processor = CLIPProcessor.from_pretrained(hf_model_id)
        tokenizer = CLIPTokenizerFast.from_pretrained(hf_model_id)
        model.eval()

        _CLIP_MODEL = model
        _CLIP_PREPROCESS = processor
        _CLIP_TOKENIZER = tokenizer
        _CLIP_BACKEND = "transformers"
        return _CLIP_MODEL, _CLIP_PREPROCESS, _CLIP_TOKENIZER
    except Exception as err:
        raise RuntimeError(
            f"Failed to load CLIP via both open_clip and transformers: {err}"
        )


def extract_frames_from_video(
    video_path: Union[str, Path],
    fps: float = 2.0,
    max_frames: int = 120,
) -> List[Tuple[float, Any]]:
    """Extract frames from an MP4 video at a given sample rate.

    Returns:
        List of (timestamp_seconds, PIL.Image) tuples.
    """
    video_path = Path(video_path)
    if not video_path.is_file():
        return []

    if Image is None:
        raise ImportError("Pillow is required for frame processing.")

    frames: List[Tuple[float, Any]] = []

    # Method 1: Try OpenCV if installed
    try:
        import cv2

        cap = cv2.VideoCapture(str(video_path))
        if cap.isOpened():
            video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            step = max(1, int(video_fps / fps))
            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret or len(frames) >= max_frames:
                    break
                if frame_idx % step == 0:
                    timestamp = frame_idx / video_fps
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(rgb_frame)
                    frames.append((timestamp, pil_img))
                frame_idx += 1
            cap.release()
            if frames:
                return frames
    except Exception:
        pass

    # Method 2: Fallback to FFmpeg CLI subprocess
    with tempfile.TemporaryDirectory() as tmpdir:
        out_pattern = Path(tmpdir) / "frame_%04d.png"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            f"fps={fps}",
            "-q:v",
            "2",
            str(out_pattern),
        ]
        try:
            res = subprocess.run(
                cmd, capture_output=True, timeout=30, text=True
            )
            if res.returncode == 0:
                extracted_files = sorted(Path(tmpdir).glob("frame_*.png"))
                for idx, fpath in enumerate(extracted_files[:max_frames]):
                    timestamp = idx / fps
                    with Image.open(fpath) as img:
                        frames.append((timestamp, img.convert("RGB")))
                return frames
        except Exception:
            pass

    return frames


@dataclass
class ClipAlignmentResult:
    score: float
    per_event: Dict[str, float]
    details: Dict[str, Any]


def clip_alignment_score(
    visual_events: Dict[str, Any],
    window_to_similarity: Dict[str, float],
) -> ClipAlignmentResult:
    """Calculates weighted alignment score given pre-computed event similarities."""
    total = 0.0
    denom = 0.0
    per_event: Dict[str, float] = {}

    for event in visual_events.get("events", []):
        event_id = event["event_id"]
        weight = float(event.get("weight", 0.0))
        sim = float(window_to_similarity.get(event_id, 0.0))
        sim = max(0.0, min(1.0, sim))

        per_event[event_id] = sim
        total += weight * sim
        denom += weight

    final_score = (total / denom) if denom > 0 else 0.0
    return ClipAlignmentResult(
        score=final_score,
        per_event=per_event,
        details={"window_similarities": window_to_similarity},
    )


def compute_video_clip_reward(
    video_path: Union[str, Path],
    visual_events: Union[Dict[str, Any], str, Path],
    fps: float = 2.0,
    device: Optional[str] = None,
) -> ClipAlignmentResult:
    """Full live OpenCLIP reward computation on a rendered Manim video.

    1. Parses `visual_events.json` events and queries.
    2. Extracts sampled video frames at `fps`.
    3. Runs CLIP to encode queries and frames.
    4. Computes cosine similarities and isolates the window [t_start, t_end] for each event.
    5. Returns overall weighted alignment reward and per-event breakdowns.
    """
    if isinstance(visual_events, (str, Path)):
        ve_path = Path(visual_events)
        if ve_path.is_file():
            visual_events = json.loads(ve_path.read_text(encoding="utf-8"))
        else:
            visual_events = {"events": []}

    events = visual_events.get("events", [])
    if not events:
        return ClipAlignmentResult(score=1.0, per_event={}, details={"warning": "No events specified"})

    frames = extract_frames_from_video(video_path, fps=fps)
    if not frames:
        # Video had 0 valid frames or failed to extract
        return ClipAlignmentResult(
            score=0.0,
            per_event={e.get("event_id", f"ev_{i}"): 0.0 for i, e in enumerate(events)},
            details={"error": "No frames extracted from video"},
        )

    model, preprocess, tokenizer = load_clip_model(device=device)
    target_device = _get_device() if device is None else device

    # 1. Encode all frames
    frame_timestamps = [t for t, _ in frames]
    pil_images = [img for _, img in frames]

    with torch.no_grad():
        if _CLIP_BACKEND == "open_clip":
            img_tensors = torch.stack([preprocess(img) for img in pil_images]).to(target_device)
            image_features = model.encode_image(img_tensors)
            image_features /= image_features.norm(dim=-1, keepdim=True)
        else:
            inputs = preprocess(images=pil_images, return_tensors="pt").to(target_device)
            image_features = model.get_image_features(**inputs)
            image_features /= image_features.norm(dim=-1, keepdim=True)

    window_similarities: Dict[str, float] = {}
    event_details: Dict[str, Any] = {}

    for event in events:
        event_id = event["event_id"]
        clip_query = event.get("clip_query", "").strip()
        time_range = event.get("expected_time_range", [0.0, 999.0])
        t_start, t_end = float(time_range[0]), float(time_range[1])

        if not clip_query:
            window_similarities[event_id] = 0.5
            continue

        # Encode text query
        with torch.no_grad():
            if _CLIP_BACKEND == "open_clip":
                text_tokens = tokenizer([clip_query]).to(target_device)
                text_features = model.encode_text(text_tokens)
                text_features /= text_features.norm(dim=-1, keepdim=True)
            else:
                text_inputs = tokenizer([clip_query], padding=True, return_tensors="pt").to(target_device)
                text_features = model.get_text_features(**text_inputs)
                text_features /= text_features.norm(dim=-1, keepdim=True)

            # Cosine similarity for all frames: shape [N_frames]
            sims = (image_features @ text_features.T).squeeze(-1).cpu().tolist()
            if isinstance(sims, float):
                sims = [sims]

        # Isolate frames within expected time window
        window_sims = [
            sim for t, sim in zip(frame_timestamps, sims)
            if t_start <= t <= t_end
        ]

        if not window_sims:
            # Event window not reached in the video
            event_score = 0.0
            peak_sim = 0.0
            avg_sim = 0.0
        else:
            # Rescale standard CLIP cosine similarities (~0.15 - 0.35 baseline for ViT-B-32) to [0.0, 1.0]
            # Zero-shot CLIP typically produces similarity in range [0.10, 0.40] for text-image pairs
            raw_peak = max(window_sims)
            raw_avg = sum(window_sims) / len(window_sims)

            # Normalized similarity mapping:
            # raw >= 0.30 -> ~1.0; raw <= 0.12 -> 0.0
            scaled_peak = max(0.0, min(1.0, (raw_peak - 0.12) / 0.18))
            scaled_avg = max(0.0, min(1.0, (raw_avg - 0.12) / 0.18))

            # Temporal event score: 70% peak frame match + 30% sustained presence
            event_score = round(0.70 * scaled_peak + 0.30 * scaled_avg, 4)
            peak_sim = raw_peak
            avg_sim = raw_avg

        window_similarities[event_id] = event_score
        event_details[event_id] = {
            "score": event_score,
            "raw_peak": round(peak_sim, 4),
            "raw_avg": round(avg_sim, 4),
            "window_frames_count": len(window_sims),
        }

    res = clip_alignment_score(visual_events, window_similarities)
    res.details = {
        "event_evaluations": event_details,
        "total_frames_extracted": len(frames),
        "video_duration_sampled": max(frame_timestamps) if frame_timestamps else 0.0,
    }
    return res
