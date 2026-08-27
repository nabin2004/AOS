from pathlib import Path

import pytest

from evals.smoke import run_smoke


@pytest.mark.asyncio
async def test_evals_smoke(tmp_path: Path) -> None:
    output = await run_smoke(tmp_path)
    assert output.strip()
