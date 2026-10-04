"""Manifest parsing and validation errors."""

from __future__ import annotations


class ManifestError(Exception):
    """Base error for YAML manifest handling."""


class ManifestValidationError(ManifestError):
    """Raised when manifest content fails schema or semantic validation."""
