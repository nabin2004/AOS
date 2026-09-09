"""Collapse verbose sandbox/compile diagnostics before feeding them back to the model."""

from __future__ import annotations

import re

_TRACEBACK_FULL_RE = re.compile(
    r"(?m)(?:[+\u2500-\u257f|╭╮╰╯│─\s]*Traceback \(most recent call last\)[^\n]*[\s\S]*?(?:^[ \t]*(?:[A-Za-z_]+Error|Exception):[^\n]*|\Z))"
)

_ERROR_HEADER_RE = re.compile(
    r"(?m)^(?:Syntax error in code:|Type error in code:|Runtime error:|"
    r"error\[[^\]]+\]:|Compilation failed|"
    r"LaTeX Error|There are no scenes inside that module|is not in the script|"
    r"Exception: You need to call init_voiceover|You need to call init_voiceover|"
    r"[A-Za-z_]+Error:)"
)

_BLOCK_CAP = 600


def _normalize_block(block: str) -> str:
    return re.sub(r"\s+", " ", block.strip())


def extract_clean_traceback(text: str, max_chars: int = 2500) -> str | None:
    """Extract and condense a Python or Rich traceback, focusing on the user scene frames and exception."""
    m = _TRACEBACK_FULL_RE.search(text)
    if not m:
        return None
    tb = m.group(0).strip()
    if len(tb) <= max_chars:
        return tb

    lines = tb.splitlines()
    construct_idx = None
    for idx, line in enumerate(lines):
        if "in construct" in line.lower() or ("workspace" in line.lower() and ".py" in line.lower()):
            construct_idx = idx
            break

    header = lines[0]
    if construct_idx is not None:
        start = max(0, construct_idx - 2)
        end = min(len(lines) - 1, construct_idx + 20)
        scene_snippet = "\n".join(lines[start:end])
        tail_snippet = "\n".join(lines[-8:])
        return f"{header}\n... [startup frames omitted] ...\n{scene_snippet}\n... [internal library calls omitted] ...\n{tail_snippet}"

    head = "\n".join(lines[:10])
    tail = "\n".join(lines[-20:])
    return f"{header}\n... [intermediate frames omitted] ...\n{tail}"


def _is_benign_noise(block: str) -> bool:
    b_low = block.lower()
    return "sox could not be found" in b_low and "error" not in b_low and "traceback" not in b_low


def _split_error_blocks(text: str) -> list[str]:
    if not text.strip():
        return []

    matches = list(_ERROR_HEADER_RE.finditer(text))
    if not matches:
        return [text.strip()]

    blocks: list[str] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        if block and not _is_benign_noise(block):
            blocks.append(block)

    return blocks


def _cap_block(block: str, max_chars: int) -> str:
    if len(block) <= max_chars:
        return block
    return block[: max_chars - 3].rstrip() + "..."


def summarize_diagnostic_output(
    text: str,
    *,
    max_chars: int = 2500,
    max_errors: int = 3,
) -> str:
    """Collapse Monty/compile dumps to first N distinct errors with minimal context."""
    if not text:
        return text
    if len(text) <= max_chars and max_errors >= 100:
        return text

    # 1. Prioritize real Python/Rich tracebacks
    tb = extract_clean_traceback(text, max_chars=max_chars)
    if tb:
        return tb

    blocks = _split_error_blocks(text)
    if not blocks:
        # Strip benign SoX warning if present before taking tail
        clean_text = re.sub(r"\[\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}\]\s+WARNING\s+SoX could not be found![\s\S]*?(?=Manim|\n\n|\Z)", "", text).strip()
        return _cap_block(clean_text or text, max_chars)

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
        dup_str = f", {duplicate_blocks} duplicate blocks omitted" if duplicate_blocks else ""
        summary += f"\n\n... ({omitted_chars} chars omitted{dup_str})"

    if len(summary) > max_chars:
        return summary[: max_chars - 3].rstrip() + "..."

    return summary
