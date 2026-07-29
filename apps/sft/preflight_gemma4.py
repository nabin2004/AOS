#!/usr/bin/env python3
"""Compatibility alias — use preflight_sft.py."""

from __future__ import annotations

from preflight_sft import main

if __name__ == "__main__":
    raise SystemExit(main())
