"""Canonical node models for the AOS Library Knowledge Graph (LKG)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    LIBRARY = "library"
    PACKAGE = "package"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    PARAMETER = "parameter"
    RETURN_TYPE = "return_type"
    CAPABILITY = "capability"
    CONCEPT = "concept"
    ALGORITHM = "algorithm"
    MANIM_MAPPING = "manim_mapping"
    ANIMATION_PATTERN = "animation_pattern"
    PRECISION_RULE = "precision_rule"
    CODE_EXAMPLE = "code_example"


class BaseNode(BaseModel):
    """Base model for all graph nodes."""
    id: str = Field(..., description="Unique node identifier across the LKG")
    name: str = Field(..., description="Human-readable node name")
    type: NodeType = Field(..., description="Canonical node type")
    docstring: Optional[str] = Field(default=None, description="Extracted or curated docstring")
    tags: List[str] = Field(default_factory=list, description="Categorical tags for filtering")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary extensible attributes")


class ParameterInfo(BaseModel):
    name: str
    type_str: Optional[str] = None
    default_str: Optional[str] = None
    is_required: bool = True
    description: Optional[str] = None


class ReturnInfo(BaseModel):
    type_str: Optional[str] = None
    description: Optional[str] = None


class LibraryNode(BaseNode):
    type: NodeType = NodeType.LIBRARY
    version: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)


class ModuleNode(BaseNode):
    type: NodeType = NodeType.MODULE
    library: str
    qualified_name: str
    is_public: bool = True
    submodules: List[str] = Field(default_factory=list)
    exported_symbols: List[str] = Field(default_factory=list)


class FunctionNode(BaseNode):
    type: NodeType = NodeType.FUNCTION
    library: str
    module: str
    qualified_name: str
    signature_str: str = "()"
    parameters: List[ParameterInfo] = Field(default_factory=list)
    returns_info: Optional[ReturnInfo] = None
    is_compiled: bool = False
    is_deprecated: bool = False
    capabilities: List[str] = Field(default_factory=list)
    concepts: List[str] = Field(default_factory=list)
    algorithms: List[str] = Field(default_factory=list)
    manim_use_cases: List[str] = Field(default_factory=list)
    example_code: Optional[str] = None
    source_code: Optional[str] = None


class ClassNode(BaseNode):
    type: NodeType = NodeType.CLASS
    library: str
    module: str
    qualified_name: str
    constructor_sig: str = "()"
    bases: List[str] = Field(default_factory=list)
    methods: List[str] = Field(default_factory=list)
    properties: List[str] = Field(default_factory=list)
    docstring: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    concepts: List[str] = Field(default_factory=list)
    algorithms: List[str] = Field(default_factory=list)
    manim_use_cases: List[str] = Field(default_factory=list)


class CapabilityNode(BaseNode):
    type: NodeType = NodeType.CAPABILITY
    domain: str = Field(..., description="Broad mathematical domain e.g. root_finding, ode, geometry")
    description: str
    dimension: str = Field(default="2D", description="Spatial dimensionality (1D, 2D, 3D, ND)")
    input_types: List[str] = Field(default_factory=list)
    output_types: List[str] = Field(default_factory=list)
    canonical_apis: List[str] = Field(default_factory=list)
    concepts: List[str] = Field(default_factory=list)
    manim_targets: List[str] = Field(default_factory=list)


class ConceptNode(BaseNode):
    type: NodeType = NodeType.CONCEPT
    domain: str
    description: str
    formal_definition: Optional[str] = None
    related_concepts: List[str] = Field(default_factory=list)


class AlgorithmNode(BaseNode):
    type: NodeType = NodeType.ALGORITHM
    domain: str
    complexity: Optional[str] = None
    convergence: Optional[str] = None
    assumptions: List[str] = Field(default_factory=list)
    description: str = ""


class ManimMappingNode(BaseNode):
    type: NodeType = NodeType.MANIM_MAPPING
    dimension: str = "2D"
    mobject_classes: List[str] = Field(default_factory=list)
    coordinate_adapter: str = "axes.c2p(x, y)"
    visual_role: str = ""
    construction_pattern: str = ""
    update_mechanism: str = "ValueTracker + always_redraw"
    best_practices: List[str] = Field(default_factory=list)
    gotchas: List[str] = Field(default_factory=list)


class AnimationPatternNode(BaseNode):
    type: NodeType = NodeType.ANIMATION_PATTERN
    pattern_name: Optional[str] = None
    description: str
    paradigm: str = "ValueTracker"
    step_sequence: List[str] = Field(default_factory=list)
    code_template: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.pattern_name:
            self.pattern_name = self.name


class PrecisionRuleNode(BaseNode):
    type: NodeType = NodeType.PRECISION_RULE
    rule_id: str
    title: str
    anti_pattern: str
    correct_pattern: str
    rationale: str
    enforcement_level: str = "STRICT"  # STRICT, RECOMMENDED


class CodeExampleNode(BaseNode):
    type: NodeType = NodeType.CODE_EXAMPLE
    target_api: str
    computational_snippet: str
    manim_integration_snippet: Optional[str] = None
    expected_output_type: Optional[str] = None
    is_verified: bool = False
