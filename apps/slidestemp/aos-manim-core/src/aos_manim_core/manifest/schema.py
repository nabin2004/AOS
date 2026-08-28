from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class BackendSpec(BaseModel):
    """Specifies an underlying computational library and entry function."""
    library: str
    symbol: Optional[str] = None
    version_req: Optional[str] = None


class ValidationRule(BaseModel):
    """Specification of invariant or correctness check executed by this capability."""
    name: str
    rule_type: str = "invariant"  # invariant, precision, bounding_box, syntax
    description: str


class Capability(BaseModel):
    """A distinct computational visualization capability exposed by a plugin."""
    name: str
    category: str
    description: str
    backends: List[str] = Field(default_factory=list)
    mobjects: List[str] = Field(default_factory=list)
    animations: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    validators: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class PluginManifest(BaseModel):
    """Machine-readable capability manifest for an AOS Manim plugin."""
    plugin: str
    version: str = "0.1.0"
    domain: str  # Presentation, STEM, Reasoning
    layer: str   # Layer A (Presentation), Layer B (STEM), Layer C (Reasoning)
    description: str
    author: str = "AOS Manim Team"
    dependencies: List[str] = Field(default_factory=list)
    capabilities: List[Capability] = Field(default_factory=list)

    def to_json(self, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)

    def save(self, filepath: Path | str) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def from_file(cls, filepath: Path | str) -> PluginManifest:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Manifest not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.model_validate(data)
