"""Canonical edge models and relationship types for the AOS LKG."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class EdgeType(str, Enum):
    # Structural containment
    CONTAINS = "CONTAINS"
    DEFINES = "DEFINES"
    SUBMODULE_OF = "SUBMODULE_OF"

    # API Signature & Typing
    ACCEPTS = "ACCEPTS"
    RETURNS = "RETURNS"
    YIELDS = "YIELDS"

    # Capability & Algorithm Semantics
    PROVIDES = "PROVIDES"
    IMPLEMENTS = "IMPLEMENTS"
    ALTERNATIVE_TO = "ALTERNATIVE_TO"
    RELATED_TO = "RELATED_TO"
    REQUIRES = "REQUIRES"

    # Knowledge & Application
    USEFUL_FOR = "USEFUL_FOR"
    SOLVES = "SOLVES"

    # Manim & Animation Bridges
    VISUALIZES_WITH = "VISUALIZES_WITH"
    ANIMATES_VIA = "ANIMATES_VIA"
    GOVERNED_BY = "GOVERNED_BY"
    HAS_EXAMPLE = "HAS_EXAMPLE"


class Edge(BaseModel):
    """Canonical edge representation connecting two graph nodes."""
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: EdgeType = Field(..., description="Canonical edge relationship type")
    weight: float = Field(default=1.0, description="Edge weight or relevance score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata attributes on the relationship")
