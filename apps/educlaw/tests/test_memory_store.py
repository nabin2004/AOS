from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from educlaw.memory.store import DagestanMemory, IngestUnavailable


@pytest.mark.asyncio
async def test_stub_retrieve_strategy_curate(tmp_path: Path) -> None:
    memory = DagestanMemory(tmp_path / "graph.json", stub=True)
    retrieved = await memory.retrieve("user goals")
    assert isinstance(retrieved, (str, list))
    strategy = await memory.strategy()
    assert strategy is not None
    report = await memory.curate()
    assert report is not None


@pytest.mark.asyncio
async def test_stub_ingest_does_not_need_network(tmp_path: Path) -> None:
    memory = DagestanMemory(tmp_path / "graph.json", stub=True)
    nodes, edges = await memory.ingest("User likes Manim and wants a pendulum scene.", source="test")
    assert isinstance(nodes, int)
    assert isinstance(edges, int)


@pytest.mark.asyncio
async def test_ingest_unavailable_without_client(tmp_path: Path) -> None:
    memory = DagestanMemory(tmp_path / "graph.json", stub=False, llm_client=None)
    with pytest.raises(IngestUnavailable):
        await memory.ingest("hello")


@pytest.mark.asyncio
async def test_ingest_path_uses_underlying_client(tmp_path: Path) -> None:
    fake = MagicMock()
    fake.ingest.return_value = (2, 1)
    fake.node_count = 2
    fake.edge_count = 1
    with patch("educlaw.memory.store.Dagestan", return_value=fake):
        memory = DagestanMemory(tmp_path / "graph.json", llm_client=lambda s, u: "{}")
        nodes, edges = await memory.ingest([{"role": "user", "content": "hi"}], source="s1")
    assert (nodes, edges) == (2, 1)
    fake.ingest.assert_called_once()
