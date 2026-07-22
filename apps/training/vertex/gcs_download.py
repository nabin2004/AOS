#!/usr/bin/env python3
"""Small CLI wrapper around env.py GCS helpers for container entrypoints."""

from __future__ import annotations

import sys
from pathlib import Path

VERTEX_ROOT = Path(__file__).resolve().parent
if str(VERTEX_ROOT) not in sys.path:
    sys.path.insert(0, str(VERTEX_ROOT))

from env import download_gcs_file, download_gcs_prefix  # noqa: E402


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "Usage: gcs_download.py file gs://bucket/object /local/path\n"
            "       gcs_download.py prefix gs://bucket/prefix/ /local/dir/",
            file=sys.stderr,
        )
        return 1

    mode, gcs_uri, dest = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    if mode == "file":
        download_gcs_file(gcs_uri, dest)
    elif mode == "prefix":
        download_gcs_prefix(gcs_uri, dest)
    else:
        print(f"Unknown mode: {mode}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
