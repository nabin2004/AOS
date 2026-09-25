"""Manim Knowledge Base & Documentation Search Service.

Provides instant, offline, deterministic semantic search over the Manim Community Edition
API documentation and signatures (backed by apps/mcpservers/manim_kb.md and BM25Okapi).
"""

from __future__ import annotations

import hashlib
import logging
import os
import pickle
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

MODULE_RE = re.compile(r"- \*\*Module:\*\* `([^`]+)`")
CONSTRUCTOR_RE = re.compile(r"- \*\*Constructor:\*\* `([^`]+)`")
SIGNATURE_RE = re.compile(r"- \*\*Signature:\*\* `([^`]+)`")
METHOD_RE = re.compile(r"^\s*-\s+`([^`]+)`")
H2_RE = re.compile(r"^## (.+)$")
H3_RE = re.compile(r"^### (.+)$")


@dataclass
class KbChunk:
    id: str
    chunk_type: str  # "entry" or "signature"
    section: str
    name: str
    parent: str
    module: str
    signature: str
    text: str


def _section_label(section: str) -> str:
    return section.split("(")[0].strip()


def _parse_module(text: str) -> str:
    m = MODULE_RE.search(text)
    return m.group(1) if m else ""


def _extract_signatures(
    entry_text: str,
    section: str,
    parent: str,
    module: str,
) -> list[KbChunk]:
    sigs: list[KbChunk] = []
    seen: set[str] = set()

    for match in CONSTRUCTOR_RE.finditer(entry_text):
        sig = match.group(1)
        if sig in seen:
            continue
        seen.add(sig)
        sigs.append(
            KbChunk(
                id=f"sig:{parent}.__init__",
                chunk_type="signature",
                section=_section_label(section),
                name="__init__",
                parent=parent,
                module=module,
                signature=sig,
                text=f"{parent}.__init__: {sig} | Class: {parent} | Module: {module}",
            )
        )

    for match in SIGNATURE_RE.finditer(entry_text):
        sig = match.group(1)
        if sig in seen:
            continue
        seen.add(sig)
        func_name = sig.split("(")[0].strip()
        sigs.append(
            KbChunk(
                id=f"sig:{parent}.{func_name}",
                chunk_type="signature",
                section=_section_label(section),
                name=func_name,
                parent=parent,
                module=module,
                signature=sig,
                text=f"{parent}.{func_name}: {sig} | Class: {parent} | Module: {module}",
            )
        )

    for line in entry_text.splitlines():
        if "_(from " in line:
            continue
        match = METHOD_RE.match(line)
        if not match:
            continue
        sig = match.group(1)
        if "(" not in sig:
            continue
        func_name = sig.split("(")[0].strip()
        if func_name in ("__init__", parent) or sig in seen:
            continue
        seen.add(sig)
        sigs.append(
            KbChunk(
                id=f"sig:{parent}.{func_name}",
                chunk_type="signature",
                section=_section_label(section),
                name=func_name,
                parent=parent,
                module=module,
                signature=sig,
                text=f"{parent}.{func_name}: {sig} | Class: {parent} | Module: {module}",
            )
        )

    return sigs


def _chunk_kb(path: Path) -> list[KbChunk]:
    content = path.read_text(encoding="utf-8")
    chunks: list[KbChunk] = []

    current_section = ""
    current_name = ""
    current_lines: list[str] = []

    def flush_entry() -> None:
        nonlocal current_name, current_lines
        if not current_name or not current_lines:
            return

        entry_text = "\n".join(current_lines).strip()
        module = _parse_module(entry_text)
        section_label = _section_label(current_section)

        chunks.append(
            KbChunk(
                id=f"{section_label.lower()}:{current_name}",
                chunk_type="entry",
                section=section_label,
                name=current_name,
                parent="",
                module=module,
                signature="",
                text=f"### {current_name}\nSection: {section_label}\nModule: {module}\n{entry_text}",
            )
        )
        chunks.extend(_extract_signatures(entry_text, current_section, current_name, module))
        current_lines = []

    for line in content.splitlines():
        h2 = H2_RE.match(line)
        if h2:
            flush_entry()
            current_section = h2.group(1).strip()
            current_name = ""
            continue

        h3 = H3_RE.match(line)
        if h3:
            flush_entry()
            current_name = h3.group(1).strip()
            current_lines = []
            continue

        if current_name:
            current_lines.append(line)

    flush_entry()
    return chunks


class ManimDocsService:
    """Singleton service for querying Manim CE documentation and signatures."""

    def __init__(self) -> None:
        self._chunks: list[KbChunk] | None = None
        self._bm25: BM25Okapi | None = None
        self._initialized: bool = False

    def _resolve_kb_path(self) -> Path | None:
        candidates = [
            Path(os.getenv("MANIM_KB_PATH", "")),
            Path(__file__).resolve().parents[5] / "mcpservers" / "manim_kb.md",
            Path(__file__).resolve().parents[4] / "apps" / "mcpservers" / "manim_kb.md",
            Path("/app/apps/mcpservers/manim_kb.md"),
            Path("apps/mcpservers/manim_kb.md").resolve(),
            Path("../../../mcpservers/manim_kb.md").resolve(),
        ]
        for p in candidates:
            if p and p.is_file():
                return p
        return None

    def _ensure_index(self) -> bool:
        if self._initialized:
            return True

        kb_path = self._resolve_kb_path()
        if not kb_path:
            logger.warning("manim_kb.md not found in search paths")
            return False

        cache_dir = Path(__file__).resolve().parents[2] / ".cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "manim_kb_bm25.pkl"

        file_stat = kb_path.stat()
        file_hash = hashlib.sha256(kb_path.read_bytes()[:100000]).hexdigest()

        if cache_path.is_file():
            try:
                with open(cache_path, "rb") as f:
                    cache_data = pickle.load(f)
                if (
                    cache_data.get("hash") == file_hash
                    and cache_data.get("mtime") == file_stat.st_mtime
                ):
                    self._chunks = cache_data["chunks"]
                    self._bm25 = cache_data["bm25"]
                    self._initialized = True
                    logger.info("Loaded cached Manim KB BM25 index (%d chunks)", len(self._chunks))
                    return True
            except Exception as exc:
                logger.debug("Stale or invalid KB cache: %s", exc)

        logger.info("Building Manim KB index from %s...", kb_path)
        chunks = _chunk_kb(kb_path)
        corpus = [c.text.lower().split() for c in chunks]
        bm25 = BM25Okapi(corpus)

        self._chunks = chunks
        self._bm25 = bm25
        self._initialized = True

        try:
            with open(cache_path, "wb") as f:
                pickle.dump(
                    {
                        "hash": file_hash,
                        "mtime": file_stat.st_mtime,
                        "chunks": chunks,
                        "bm25": bm25,
                    },
                    f,
                )
        except Exception as exc:
            logger.debug("Failed to write KB cache: %s", exc)

        logger.info("Manim KB index ready: %d chunks", len(chunks))
        return True

    def search_docs(self, query: str, top_k: int = 5) -> str:
        """Search Manim API classes, functions, and constants."""
        q = (query or "").strip()
        if not q:
            return "Please provide a non-empty search query."

        if not self._ensure_index() or not self._chunks or not self._bm25:
            return "Manim documentation index unavailable in current environment."

        tokens = q.lower().split()
        scores = self._bm25.get_scores(tokens)

        # Lexical boost for exact name matches
        q_clean = q.strip().lower()
        scored_indices: list[tuple[float, int]] = []
        for i, c in enumerate(self._chunks):
            if c.chunk_type != "entry":
                continue
            base_score = float(scores[i])
            c_name_lower = c.name.lower()
            if c_name_lower == q_clean:
                base_score += 15.0
            elif q_clean in c_name_lower:
                base_score += 5.0
            scored_indices.append((base_score, i))

        scored_indices.sort(key=lambda x: x[0], reverse=True)
        top_hits = [self._chunks[i] for score, i in scored_indices[:top_k] if score > 0.05]

        if not top_hits:
            return f"No matching Manim documentation found for '{query}'."

        formatted: list[str] = []
        for i, hit in enumerate(top_hits, 1):
            text_lines = hit.text.splitlines()
            # Trim method list if excessively long
            trimmed_lines: list[str] = []
            method_count = 0
            for line in text_lines:
                if line.strip().startswith("- `"):
                    method_count += 1
                    if method_count > 15:
                        continue
                trimmed_lines.append(line)
            if method_count > 15:
                trimmed_lines.append(f"  ... (+{method_count - 15} more methods)")

            formatted.append(f"[{i}] " + "\n".join(trimmed_lines))

        return "\n\n---\n\n".join(formatted)

    def search_signatures(self, query: str, top_k: int = 5) -> str:
        """Search constructor and method signatures for exact parameters and default values."""
        q = (query or "").strip()
        if not q:
            return "Please provide a non-empty search query."

        if not self._ensure_index() or not self._chunks or not self._bm25:
            return "Manim documentation index unavailable in current environment."

        tokens = q.lower().split()
        scores = self._bm25.get_scores(tokens)

        q_clean = q.strip().lower()
        scored_indices: list[tuple[float, int]] = []
        for i, c in enumerate(self._chunks):
            if c.chunk_type != "signature":
                continue
            base_score = float(scores[i])
            c_parent_lower = (c.parent or "").lower()
            c_name_lower = c.name.lower()
            if c_parent_lower == q_clean and c.name == "__init__":
                base_score += 20.0
            elif c_parent_lower == q_clean:
                base_score += 10.0
            elif q_clean in f"{c_parent_lower}.{c_name_lower}":
                base_score += 6.0
            scored_indices.append((base_score, i))

        scored_indices.sort(key=lambda x: x[0], reverse=True)
        top_hits = [self._chunks[i] for score, i in scored_indices[:top_k] if score > 0.05]

        if not top_hits:
            return f"No matching Manim signatures found for '{query}'."

        formatted: list[str] = []
        for i, hit in enumerate(top_hits, 1):
            formatted.append(
                f"[{i}] {hit.parent or hit.name}\n"
                f"- **Signature:** `{hit.signature}`\n"
                f"- **Module:** `{hit.module}`\n"
                f"- **Section:** {hit.section}"
            )

        return "\n\n---\n\n".join(formatted)


manim_docs_service = ManimDocsService()
