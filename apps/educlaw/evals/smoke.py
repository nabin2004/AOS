"""Offline harness smoke: TestModel turn must produce output."""

from __future__ import annotations

import asyncio
from pathlib import Path
import tempfile

from educlaw.session import create_session
from educlaw.testing import make_settings


async def run_smoke(tmp: Path) -> str:
    settings = make_settings()
    handler = create_session(cwd=tmp, settings=settings, yes=True)
    output = await handler.run_turn("Say hello to the harness smoke test.")
    if not isinstance(output, str) or not output.strip():
        raise SystemExit("smoke failed: empty output")
    return output


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        output = asyncio.run(run_smoke(Path(raw)))
    print(output)
    print("smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
