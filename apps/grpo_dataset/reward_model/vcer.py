from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


VCER_PATTERNS = [
    r"\\bShowCreation\\(",
    r"\\bCONFIG\\s*=\\s*\\{",
    r"\\bGraphScene\\b",
    r"\\bself\\.frame\\.reorient\\(",
]


@dataclass
class VCERResult:
    score: float
    matches: list[str]


def compute_vcer_score(code: str, patterns: Iterable[str] = VCER_PATTERNS) -> VCERResult:
    matched: list[str] = []
    for pattern in patterns:
        if re.search(pattern, code):
            matched.append(pattern)

    if not patterns:
        return VCERResult(score=0.0, matches=[])

    return VCERResult(score=len(matched) / len(list(patterns)), matches=matched)
