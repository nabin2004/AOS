"""Collapse verbose sandbox/compile diagnostics before feeding them back to the model."""

from __future__ import annotations

import re

_ERROR_HEADER_RE = re.compile(
    r"(?m)^(?:Syntax error in code:|Type error in code:|Runtime error:|"
    r"error\[[^\]]+\]:|Traceback \(most recent call last\):|Compilation failed|"
    r"LaTeX Error|There are no scenes inside that module|is not in the script|"
    r"Exception: You need to call init_voiceover|You need to call init_voiceover)"
)

_BLOCK_CAP = 300


def _normalize_block(block: str) -> str:
    return re.sub(r"\s+", " ", block.strip())


def _split_error_blocks(text: str) -> list[str]:
    if not text.strip():
        return []

    matches = list(_ERROR_HEADER_RE.finditer(text))
    if not matches:
        return [text.strip()]

    blocks: list[str] = []
    if matches[0].start() > 0:
        prefix = text[: matches[0].start()].strip()
        if prefix:
            blocks.append(prefix)

    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        if block:
            blocks.append(block)

    return blocks


def _cap_block(block: str, max_chars: int) -> str:
    if len(block) <= max_chars:
        return block
    return block[: max_chars - 3].rstrip() + "..."


def summarize_diagnostic_output(
    text: str,
    *,
    max_chars: int = 1200,
    max_errors: int = 3,
) -> str:
    """Collapse Monty/compile dumps to first N distinct errors with minimal context."""
    if not text:
        return text
    if len(text) <= max_chars and max_errors >= 100:
        return text

    blocks = _split_error_blocks(text)
    if not blocks:
        return text[:max_chars]

    seen: set[str] = set()
    kept: list[str] = []
    duplicate_blocks = 0
    per_block_cap = min(_BLOCK_CAP, max(max_chars // max(max_errors, 1), 120))

    for block in blocks:
        key = _normalize_block(block)
        if key in seen:
            duplicate_blocks += 1
            continue
        seen.add(key)
        kept.append(_cap_block(block, per_block_cap))
        if len(kept) >= max_errors:
            duplicate_blocks += len(blocks) - blocks.index(block) - 1
            break

    if not kept:
        return _cap_block(text, max_chars)

    summary = "\n\n".join(kept)
    omitted_chars = max(0, len(text) - len(summary))
    if duplicate_blocks or omitted_chars:
        summary += (
            f"\n\n... ({omitted_chars} chars omitted"
            f"{f', {duplicate_blocks} duplicate blocks omitted' if duplicate_blocks else ''})"
        )

    if len(summary) > max_chars:
        return summary[: max_chars - 3].rstrip() + "..."

    return summary
