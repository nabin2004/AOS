"""Root CLI entrypoint for AOS — delegates directly to apps/agents/cli.py.

Allows running from the repository root:
    uv run python cli.py animate "Comprehensive lecture on Lorenz attractor" --length 10m --fast --json --no-banner
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
AGENTS_DIR = REPO_ROOT / "apps" / "agents"

if str(AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(AGENTS_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(1, str(REPO_ROOT))

# Switch working directory to apps/agents so relative paths (workspace/, .env, etc.) resolve cleanly
os.chdir(str(AGENTS_DIR))

from cli import app

if __name__ == "__main__":
    app()
