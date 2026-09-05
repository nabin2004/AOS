"""Dagestan temporal-graph adapter."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    from dagestan import Dagestan
except ImportError:
    class Dagestan:  # type: ignore[no-redef]
        def __init__(self, db_path: str = "", **kwargs: Any) -> None:
            self.db_path = db_path
            self.node_count = 0
            self.edge_count = 0
            self.nodes: list[dict[str, Any]] = []
            self.edges: list[dict[str, Any]] = []
        def ingest(self, conversation: Any, source: str = "") -> tuple[int, int]:
            return (0, 0)
        def retrieve(self, query: str, top_k: int = 10, as_text: bool = True) -> str | list[Any]:
            return "" if as_text else []
        def curate(self) -> Any:
            return {"curated": True}
        def strategy(self, top_k: int = 15, as_text: bool = True) -> str | dict[str, Any]:
            return "" if as_text else {}

from dotenv import load_dotenv

load_dotenv()  

LLMClient = Callable[[str, str], str]

_PATH_LOCKS: dict[str, threading.Lock] = {}
_PATH_LOCKS_GUARD = threading.Lock()


class IngestUnavailable(RuntimeError):
    """Raised when ingest needs an LLM and none is configured."""


def _lock_for(path: str) -> threading.Lock:
    with _PATH_LOCKS_GUARD:
        return _PATH_LOCKS.setdefault(path, threading.Lock())


def make_extraction_client(model: str) -> LLMClient:
    """Sync callable Dagestan can use, backed by the same Pydantic AI model string."""
    from pydantic_ai import Agent
    from educlaw.agent.factory import resolve_educlaw_model

    resolved = resolve_educlaw_model(model)
    extractor = Agent(resolved, name="educlaw-memory-extract")

    def client(system_prompt: str, user_prompt: str) -> str:
        result = extractor.run_sync(user_prompt, instructions=system_prompt)
        return str(result.output)

    return client


class DagestanMemory:
    """Per-workspace Dagestan graph with a file lock (upstream is not thread-safe)."""

    def __init__(
        self,
        db_path: Path,
        *,
        llm_client: LLMClient | None = None,
        stub: bool = False,
        auto_save: bool = True,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.stub = stub
        self._can_ingest = stub or llm_client is not None
        kwargs: dict[str, Any] = {
            "db_path": str(self.db_path),
            "auto_save": auto_save,
        }
        if stub:
            kwargs["provider"] = "stub"
        elif llm_client is not None:
            kwargs["llm_client"] = llm_client
        self._mem = Dagestan(**kwargs)
        self._lock = _lock_for(str(self.db_path.resolve()))

    @property
    def node_count(self) -> int:
        return self._mem.node_count

    @property
    def edge_count(self) -> int:
        return self._mem.edge_count

    def _sync_ingest(self, conversation: str | list[dict[str, str]], source: str) -> tuple[int, int]:
        if not self._can_ingest:
            raise IngestUnavailable(
                "Dagestan ingest needs an LLM client or EDUCLAW_MEMORY_STUB=1. "
                "Retrieve/curate/strategy still work on the existing graph."
            )
        with self._lock:
            return self._mem.ingest(conversation, source=source)

    def _sync_retrieve(self, query: str, top_k: int, as_text: bool) -> str | list[Any]:
        with self._lock:
            return self._mem.retrieve(query, top_k=top_k, as_text=as_text)

    def _sync_curate(self) -> Any:
        with self._lock:
            return self._mem.curate()

    def _sync_strategy(self, top_k: int, as_text: bool) -> str | dict[str, Any]:
        with self._lock:
            return self._mem.strategy(top_k=top_k, as_text=as_text)

    async def ingest(
        self,
        conversation: str | list[dict[str, str]],
        source: str = "",
    ) -> tuple[int, int]:
        return await asyncio.to_thread(self._sync_ingest, conversation, source)

    async def retrieve(self, query: str, top_k: int = 10, as_text: bool = True) -> str | list[Any]:
        return await asyncio.to_thread(self._sync_retrieve, query, top_k, as_text)

    async def curate(self) -> Any:
        return await asyncio.to_thread(self._sync_curate)

    async def strategy(self, top_k: int = 15, as_text: bool = True) -> str | dict[str, Any]:
        return await asyncio.to_thread(self._sync_strategy, top_k, as_text)
