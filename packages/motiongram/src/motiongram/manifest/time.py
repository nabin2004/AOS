"""Parse time values from YAML (seconds, or strings like ``12s``)."""

from __future__ import annotations

import re

from motiongram.manifest.errors import ManifestValidationError

_TIME_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*s?\s*$", re.IGNORECASE)


def parse_time(value: object, *, field: str = "time") -> float:
    """Parse a duration or timestamp to seconds."""
    if isinstance(value, bool):
        raise ManifestValidationError(f"{field}: boolean is not a valid time")
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        m = _TIME_RE.match(value)
        if m is None:
            raise ManifestValidationError(
                f"{field}: expected seconds or string like '12s', got {value!r}"
            )
        return float(m.group(1))
    raise ManifestValidationError(
        f"{field}: expected number or time string, got {type(value).__name__}"
    )
