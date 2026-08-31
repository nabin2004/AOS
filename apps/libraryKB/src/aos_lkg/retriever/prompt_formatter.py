"""PromptFormatter: Transforms a RetrievedSlice into a high-density, 500-1500 token LLM context block."""

from __future__ import annotations

from typing import Optional
from aos_lkg.retriever.task_retriever import RetrievedSlice


class PromptFormatter:
    """Formats structured knowledge slices for downstream LLM generation."""

    @staticmethod
    def format_llm_context(slice_data: RetrievedSlice) -> str:
        """Format the retrieved slice into canonical markdown context blocks."""
        lines = []

        lines.append(f"[TASK]\n{slice_data.query}\n")

        # 1. Math Capability
        if slice_data.primary_capability:
            cap = slice_data.primary_capability
            lines.append("[MATH CAPABILITY]")
            lines.append(f"Domain: {cap.domain}")
            lines.append(f"Capability: {cap.name}")
            lines.append(f"Description: {cap.description}")
            if cap.input_types:
                lines.append(f"Inputs: {', '.join(cap.input_types)}")
            if cap.output_types:
                lines.append(f"Outputs: {', '.join(cap.output_types)}\n")

        # 2. Computational Backend API
        if slice_data.primary_api:
            api = slice_data.primary_api
            qualname = getattr(api, "qualified_name", api.name)
            sig = getattr(api, "signature_str", getattr(api, "constructor_sig", "()"))
            lines.append("[PRIMARY COMPUTATIONAL BACKEND]")
            lines.append(f"API: {qualname}")
            lines.append(f"Signature: {sig}")
            if api.docstring:
                summary = api.docstring.split("\n")[0]
                lines.append(f"Doc Summary: {summary}")
            if getattr(api, "parameters", None):
                req_params = [f"{p.name} ({p.type_str or 'Any'})" for p in api.parameters if p.is_required]
                opt_params = [f"{p.name}={p.default_str}" for p in api.parameters if not p.is_required]
                if req_params:
                    lines.append(f"Required Params: {', '.join(req_params)}")
                if opt_params:
                    lines.append(f"Optional Params: {', '.join(opt_params[:4])}")
            elif getattr(api, "methods", None):
                public_methods = [m for m in api.methods if not m.startswith("_")][:5]
                if public_methods:
                    lines.append(f"Methods: {', '.join(public_methods)}")
            lines.append("")

        # 3. Alternative Backends
        if slice_data.alternative_apis:
            lines.append("[ALTERNATIVE BACKENDS]")
            for alt in slice_data.alternative_apis:
                alt_qual = getattr(alt, "qualified_name", alt.name)
                alt_sig = getattr(alt, "signature_str", getattr(alt, "constructor_sig", "()"))
                lines.append(f"- {alt_qual}{alt_sig}")
            lines.append("")

        # 4. Algorithm & Methodology
        if slice_data.algorithms:
            lines.append("[ALGORITHM & METHODOLOGY]")
            for algo in slice_data.algorithms:
                lines.append(f"Algorithm: {algo.name}")
                if algo.complexity:
                    lines.append(f"Complexity: {algo.complexity}")
                if algo.convergence:
                    lines.append(f"Convergence: {algo.convergence}")
                if algo.assumptions:
                    lines.append(f"Assumptions: {'; '.join(algo.assumptions)}")
                if algo.description:
                    lines.append(f"Summary: {algo.description}")
            lines.append("")

        # 5. Relevant Manim Mobjects & Coordinate Adapters
        if slice_data.manim_mappings:
            lines.append("[RELEVANT MANIM MOBJECTS & COORDINATE BRIDGES]")
            for mm in slice_data.manim_mappings:
                lines.append(f"Mobjects: {', '.join(mm.mobject_classes)}")
                lines.append(f"Coordinate Adapter: `{mm.coordinate_adapter}`")
                if mm.construction_pattern:
                    lines.append(f"Construction: `{mm.construction_pattern}`")
                if mm.best_practices:
                    for bp in mm.best_practices[:2]:
                        lines.append(f"- Best Practice: {bp}")
            lines.append("")

        # 6. Animation Pattern & Steps
        if slice_data.animation_patterns:
            lines.append("[ANIMATION PATTERN]")
            for pat in slice_data.animation_patterns:
                lines.append(f"Pattern: {pat.name} ({pat.paradigm})")
                lines.append(f"Description: {pat.description}")
                if pat.step_sequence:
                    lines.append("Step Sequence:")
                    for s in pat.step_sequence:
                        lines.append(f"  {s}")
                if pat.code_template:
                    lines.append(f"Pattern Template:\n```python\n{pat.code_template.strip()}\n```")
            lines.append("")

        # 7. Precision & Anti-Hallucination Rules
        if slice_data.precision_rules:
            lines.append("[PRECISION & ANTI-HALLUCINATION RULES]")
            for rule in slice_data.precision_rules:
                lines.append(f"[{rule.enforcement_level}] {rule.title}")
                lines.append(f"  Anti-pattern: {rule.anti_pattern}")
                lines.append(f"  Correct: {rule.correct_pattern}")
                lines.append(f"  Rationale: {rule.rationale}")
            lines.append("")

        # 8. Verified Code Snippet
        if slice_data.code_examples:
            lines.append("[VERIFIED EXECUTABLE RECIPE]")
            for ex in slice_data.code_examples:
                lines.append(f"Example: {ex.name}")
                if ex.computational_snippet:
                    lines.append(f"Computational Backend:\n```python\n{ex.computational_snippet.strip()}\n```")
                if ex.manim_integration_snippet:
                    lines.append(f"Manim Scene Integration:\n```python\n{ex.manim_integration_snippet.strip()}\n```")
            lines.append("")

        return "\n".join(lines).strip()
