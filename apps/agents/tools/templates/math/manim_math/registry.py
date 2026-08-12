"""manim_math registry singleton."""

from manim_viz import ConceptRegistry

REGISTRY = ConceptRegistry()
register_concept = REGISTRY.register_concept
get_concept = REGISTRY.get_concept
list_concepts = REGISTRY.list_concepts
domains = REGISTRY.domains
stub_concept = REGISTRY.stub_concept
