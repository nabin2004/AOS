from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import torch
from PIL import Image

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reward_model.clip_reward import load_clip_model, _CLIP_BACKEND, _get_device


def embed_frames_directory(frames_dir: Path, out_path: Path, model_name: str = "ViT-B-32") -> None:
    if not frames_dir.exists():
        raise FileNotFoundError(f"Frame directory not found: {frames_dir}")

    frame_paths = sorted(
        list(frames_dir.glob("*.png")) + list(frames_dir.glob("*.jpg")) + list(frames_dir.glob("*.jpeg"))
    )
    if not frame_paths:
        print(f"Warning: No frames found in {frames_dir}. Writing empty embedding array.")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(out_path), np.empty((0, 512), dtype=np.float32))
        return

    model, preprocess, _ = load_clip_model(model_name=model_name)
    device = _get_device()

    pil_images = [Image.open(p).convert("RGB") for p in frame_paths]

    with torch.no_grad():
        if _CLIP_BACKEND == "open_clip":
            img_tensors = torch.stack([preprocess(img) for img in pil_images]).to(device)
            embeddings = model.encode_image(img_tensors)
        else:
            inputs = preprocess(images=pil_images, return_tensors="pt").to(device)
            embeddings = model.get_image_features(**inputs)

        embeddings /= embeddings.norm(dim=-1, keepdim=True)
        embeddings_np = embeddings.cpu().numpy().astype(np.float32)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(out_path), embeddings_np)
    print(f"Saved {len(frame_paths)} frame embeddings (shape: {embeddings_np.shape}) to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract frame embeddings from a local frame directory using OpenCLIP and save .npy output."
    )
    parser.add_argument("--frames", required=True, help="Directory of extracted frames")
    parser.add_argument("--out", required=True, help="Output .npy path")
    parser.add_argument("--model", default="ViT-B-32", help="OpenCLIP model architecture")
    args = parser.parse_args()

    embed_frames_directory(Path(args.frames), Path(args.out), model_name=args.model)


if __name__ == "__main__":
    main()
