from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a candidate script in a sandbox subprocess.")
    parser.add_argument("--script", required=True, help="Path to candidate python script")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout seconds")
    args = parser.parse_args()

    script_path = Path(args.script)
    if not script_path.exists():
        raise FileNotFoundError(f"Script does not exist: {script_path}")

    proc = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        timeout=args.timeout,
    )

    print(proc.stdout)
    if proc.returncode != 0:
        print(proc.stderr)
        raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
