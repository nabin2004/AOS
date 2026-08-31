"""Configuration system for modular library indexing in AOS LKG."""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class LibraryConfig(BaseModel):
    """Configuration for crawling and indexing an individual library."""
    name: str = Field(..., description="Python package import name (e.g. 'scipy', 'numpy', 'sympy')")
    submodules: Optional[List[str]] = Field(
        default=None,
        description="Explicit submodules to crawl (e.g. ['optimize', 'integrate']). If None, crawls entire package.",
    )
    exclude_patterns: List[str] = Field(
        default_factory=lambda: ["tests", "testing", "_internals", "setup", "_cpython"],
        description="Module name patterns to skip.",
    )
    max_depth: int = Field(default=3, description="Maximum recursive traversal depth")
    extract_sources: bool = Field(default=False, description="Whether to extract raw Python source code")
    domain: Optional[str] = Field(
        default=None,
        description="Default mathematical domain (e.g. 'differential_equations', 'linear_algebra', 'graph_theory')",
    )


class LKGConfig(BaseModel):
    """Global configuration for AOS Library Knowledge Graph."""
    data_dir: str = Field(default="data", description="Storage directory for JSONL files and indices")
    quick_mode: bool = Field(default=False, description="Whether to run in quick/minimal mode")
    libraries: List[LibraryConfig] = Field(default_factory=list, description="List of libraries to index")
    embedding_provider: str = Field(default="bm25", description="Semantic search backend ('bm25', 'dense')")

    @classmethod
    def default_config(cls) -> LKGConfig:
        """Returns canonical default configuration for scientific Python libraries."""
        return cls(
            data_dir="data",
            quick_mode=False,
            libraries=[
                LibraryConfig(
                    name="scipy",
                    submodules=["optimize", "integrate", "interpolate", "linalg", "signal", "spatial", "special"],
                    max_depth=3,
                    domain="calculus",
                ),
                LibraryConfig(
                    name="numpy",
                    submodules=["linalg", "fft", "random"],
                    max_depth=2,
                    domain="linear_algebra",
                ),
                LibraryConfig(
                    name="sympy",
                    submodules=["solvers", "calculus", "matrices", "geometry"],
                    max_depth=3,
                    domain="symbolic_algebra",
                ),
                LibraryConfig(
                    name="networkx",
                    submodules=["algorithms.shortest_paths", "algorithms.traversal", "algorithms.community", "drawing"],
                    max_depth=3,
                    domain="graph_theory",
                ),
                LibraryConfig(
                    name="shapely",
                    submodules=None,
                    max_depth=2,
                    domain="computational_geometry",
                ),
                LibraryConfig(
                    name="mpmath",
                    submodules=None,
                    max_depth=2,
                    domain="special_functions",
                ),
            ],
        )

    @classmethod
    def from_yaml(cls, path_or_str: str | Path) -> LKGConfig:
        """Load configuration from a YAML file or string."""
        path = Path(path_or_str)
        if path.exists() and path.is_file():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        else:
            data = yaml.safe_load(str(path_or_str)) or {}

        return cls(**data)

    def to_yaml(self, filepath: str | Path) -> None:
        """Save configuration to a YAML file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.model_dump(), f, sort_keys=False, default_flow_style=False)

    def add_library(
        self,
        name: str,
        submodules: Optional[List[str]] = None,
        domain: Optional[str] = None,
        max_depth: int = 3,
    ) -> None:
        """Add or update a library configuration."""
        for lib in self.libraries:
            if lib.name == name:
                if submodules is not None:
                    lib.submodules = submodules
                if domain is not None:
                    lib.domain = domain
                lib.max_depth = max_depth
                return
        self.libraries.append(
            LibraryConfig(
                name=name,
                submodules=submodules,
                domain=domain,
                max_depth=max_depth,
            )
        )
