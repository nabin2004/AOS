from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract frame embeddings from a local frame directory and save .npy output."
    )
    parser.add_argument("--frames", required=True, help="Directory of extracted frames")
    parser.add_argument("--out", required=True, help="Output .npy path")
    args = parser.parse_args()

    frames_dir = Path(args.frames)
    out_path = Path(args.out)

    if not frames_dir.exists():
        raise FileNotFoundError(f"Frame directory not found: {frames_dir}")

    # Placeholder implementation: this scaffold is intentionally lightweight.
    # Integrate OpenCLIP and real frame sampling in the next iteration.
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(b"")
    print(f"Created placeholder embeddings file at {out_path}")


if __name__ == "__main__":
    main()
