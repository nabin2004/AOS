"""Scientific Defensibility & Pedagogical Validator for MotionGram DSL.

Translates the K-Dense epistemic principle:
"An animation that renders without errors does not mean it is scientifically
defensible or pedagogically sound."
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from motiongram.sci.schema import ScientificSceneSpec


@dataclass
class ValidationIssue:
    """A single scientific defensibility or pedagogical issue."""

    rule_id: str
    domain: str
    severity: Literal["error", "warning"]
    message: str
    remediation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "domain": self.domain,
            "severity": self.severity,
            "message": self.message,
            "remediation": self.remediation,
        }


@dataclass
class ValidationReport:
    """Consolidated report of defensibility validation results."""

    is_defensible: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]


class DefensibilityValidator:
    """Evaluates ScientificSceneSpec specifications against domain visual conventions and constraints."""

    DISALLOWED_COLORMAPS = {"jet", "rainbow", "hsv", "spectral"}
    PERCEPTUALLY_UNIFORM_COLORMAPS = {"viridis", "plasma", "magma", "inferno", "cividis"}

    CHAOTIC_MODELS = {
        "lorenz",
        "rossler",
        "double_pendulum",
        "duffing",
        "henon",
        "chua",
        "double_scroll",
        "multiscroll",
        "chen",
        "sprott",
        "sprott_b",
        "rabinovich_fabrikant",
        "shilnikov",
        "hyperchaotic",
        "hidden_attractor",
        "leonov",
        "aizerman",
        "chaotic_saddle",
        "transient",
        "solenoid",
        "milnor",
        "coexisting_attractors",
    }

    def __init__(self, strict: bool = False):
        self.strict = strict

    def validate(
        self,
        spec: ScientificSceneSpec,
        domain: str | None = None,
    ) -> ValidationReport:
        """Run all applicable defensibility checks against the scene spec."""
        issues: list[ValidationIssue] = []

        # Auto-detect domain if not explicitly provided
        detected_domains = self._detect_domains(spec, explicit_domain=domain)

        # Run domain-agnostic checks
        self._check_general_scientific_integrity(spec, issues)

        # Run domain-specific checks
        if "dynamical_systems" in detected_domains:
            self._check_dynamical_systems(spec, issues)
        if "linear_algebra" in detected_domains:
            self._check_linear_algebra(spec, issues)
        if "vector_calculus" in detected_domains:
            self._check_vector_calculus(spec, issues)
        if "deep_learning" in detected_domains or "machine_learning_optimization" in detected_domains:
            self._check_deep_learning(spec, issues)

        # Determine if defensible based on strictness
        if self.strict:
            is_defensible = len(issues) == 0
        else:
            is_defensible = len([i for i in issues if i.severity == "error"]) == 0

        return ValidationReport(is_defensible=is_defensible, issues=issues)

    def _detect_domains(
        self,
        spec: ScientificSceneSpec,
        explicit_domain: str | None,
    ) -> set[str]:
        domains: set[str] = set()
        if explicit_domain:
            domains.add(explicit_domain)
            return domains

        # Detect from template and model
        template = spec.scene.template.lower()
        style = spec.scene.style.lower()

        dl_keywords = [
            "deep_learning", "neural", "activation", "loss", "optimizer", "sgd",
            "adam", "backprop", "softmax", "sigmoid", "relu", "tensor", "gradient_descent",
            "machine_learning", "dl_"
        ]
        if any(k in template for k in dl_keywords) or any(k in style for k in dl_keywords):
            domains.add("deep_learning")

        if any(
            t in template
            for t in ["ode", "lorenz", "trajectory", "chaotic", "attractor", "phase_portrait"]
        ):
            domains.add("dynamical_systems")

        for ds in spec.data:
            if ds.model and ds.model.lower() in self.CHAOTIC_MODELS:
                domains.add("dynamical_systems")
            if ds.source in ("function_sampler", "analytical_surface", "loss_surface", "optimization_tracer", "softmax_normalizer"):
                domains.add("deep_learning")
            if ds.algorithm or ds.loss_function or ds.logits:
                domains.add("deep_learning")

        if any(
            t in template
            for t in ["matrix", "transform", "eigen", "determinant", "nullspace"]
        ):
            domains.add("linear_algebra")

        if any(
            t in template
            for t in ["field", "curl", "divergence", "flux", "gradient"]
        ):
            domains.add("vector_calculus")

        for vis in spec.visuals:
            if "vector_field" in vis.type or "field" in vis.type:
                domains.add("vector_calculus")
            if vis.type in ("activation_plot", "loss_landscape", "optimizer_path", "network_graph", "tensor_grid"):
                domains.add("deep_learning")

        # Default fallback
        if not domains:
            domains.add("dynamical_systems")

        return domains

    def _check_general_scientific_integrity(
        self,
        spec: ScientificSceneSpec,
        issues: list[ValidationIssue],
    ) -> None:
        """Domain-agnostic visual rules (e.g. colormap perception)."""
        for vis in spec.visuals:
            style = vis.style or {}
            cmap = style.get("colormap") or style.get("color_map") or style.get("palette")
            if cmap and str(cmap).lower() in self.DISALLOWED_COLORMAPS:
                issues.append(
                    ValidationIssue(
                        rule_id="SCI-001",
                        domain="general",
                        severity="error",
                        message=(
                            f"Visual '{vis.id}' uses non-perceptually uniform colormap '{cmap}'."
                        ),
                        remediation=(
                            "The 'Jet' or 'Rainbow' colormap introduces artificial visual edges and "
                            "distorts gradients. Replace with a perceptually uniform colormap: "
                            "'viridis', 'plasma', 'magma', or 'cividis'."
                        ),
                    )
                )

    def _check_dynamical_systems(
        self,
        spec: ScientificSceneSpec,
        issues: list[ValidationIssue],
    ) -> None:
        """Rules for ODEs, chaotic attractors, and phase portraits."""
        is_chaotic = (
            "chaotic" in spec.scene.template.lower()
            or any(
                ds.model and ds.model.lower() in self.CHAOTIC_MODELS
                for ds in spec.data
            )
        )
        visual_types = {v.type for v in spec.visuals}

        # DS-001: Vector field context requirement
        has_vector_field = any(
            v_type in visual_types
            for v_type in ["vector_field", "vector_field_2d", "vector_field_3d", "streamlines"]
        )
        if is_chaotic and not has_vector_field:
            issues.append(
                ValidationIssue(
                    rule_id="DS-001",
                    domain="dynamical_systems",
                    severity="warning",
                    message="Chaotic attractor trajectory lacks background vector field context.",
                    remediation=(
                        "Add a faint background vector field (opacity: 0.15 - 0.25) to illustrate "
                        "the phase space velocity structure that dictates trajectory flow."
                    ),
                )
            )

        # DS-002: Inset graph for chaotic divergence proofs
        if spec.scene.template == "chaotic_divergence":
            has_log_inset = False
            for vis in spec.visuals:
                if vis.type == "inset_graph" and getattr(vis, "y_scale", "linear") == "log":
                    has_log_inset = True
                    break

            if not has_log_inset:
                issues.append(
                    ValidationIssue(
                        rule_id="DS-002",
                        domain="dynamical_systems",
                        severity="error",
                        message=(
                            "Scene template 'chaotic_divergence' requires an inset graph with "
                            "logarithmic y-scale to prove exponential separation."
                        ),
                        remediation=(
                            "Add a visual component: {id: 'divergence_graph', type: 'inset_graph', "
                            "y_scale: 'log', position: 'UR'} tracking trajectory separation."
                        ),
                    )
                )

        # DS-003: Linear trajectory pacing
        for action in spec.timeline:
            if action.action in {"create", "draw_and_trace"} and action.rate_func:
                if action.rate_func != "linear":
                    issues.append(
                        ValidationIssue(
                            rule_id="DS-003",
                            domain="dynamical_systems",
                            severity="error",
                            message=(
                                f"Timeline action '{action.action}' on '{action.target}' uses "
                                f"rate_func='{action.rate_func}'. Phase space trajectory tracing must use linear pacing."
                            ),
                            remediation=(
                                "Set rate_func: 'linear' (or None) so that simulation time maps linearly "
                                "to animation time, preserving true phase velocity."
                            ),
                        )
                    )

        # DS-004: Caveat bookmark on long numerical integrations of chaotic systems
        if is_chaotic:
            max_t = 0.0
            for ds in spec.data:
                if ds.solver and ds.solver.t_span and len(ds.solver.t_span) >= 2:
                    t_span_len = ds.solver.t_span[1] - ds.solver.t_span[0]
                    if t_span_len > max_t:
                        max_t = t_span_len

            if max_t >= 20.0 and spec.narration and spec.narration.text:
                if "<bookmark mark='CAVEAT'/>" not in spec.narration.text and '<bookmark mark="CAVEAT"/>' not in spec.narration.text:
                    issues.append(
                        ValidationIssue(
                            rule_id="DS-004",
                            domain="dynamical_systems",
                            severity="warning",
                            message=(
                                f"Chaotic simulation runs for t={max_t:.1f} without a numerical drift caveat bookmark."
                            ),
                            remediation=(
                                "Include `<bookmark mark='CAVEAT'/>` in your narration text explaining "
                                "that numerical discretization error eventually dominates true chaotic divergence."
                            ),
                        )
                    )

        # DS-005: Epistemic language checks
        if spec.narration and spec.narration.text:
            text_lower = spec.narration.text.lower()
            if is_chaotic and "random" in text_lower:
                allowed_qualifiers = ["not random", "isn't random", "appears random", "seems random", "looks random"]
                if not any(q in text_lower for q in allowed_qualifiers):
                    issues.append(
                        ValidationIssue(
                            rule_id="DS-005",
                            domain="dynamical_systems",
                            severity="warning",
                            message=(
                                "Narration mentions 'random' in the context of deterministic chaos."
                            ),
                            remediation=(
                                "Do not describe chaotic attractors as random. Clarify that the system is "
                                "'strictly deterministic yet exponentially sensitive to initial conditions'."
                            ),
                        )
                    )

    def _check_linear_algebra(
        self,
        spec: ScientificSceneSpec,
        issues: list[ValidationIssue],
    ) -> None:
        """Rules for linear transformations, basis vectors, determinants, and null spaces."""
        template = spec.scene.template.lower()

        # LA-001: Singular matrix / determinant 0 requires null space representation
        is_singular = "determinant_zero" in template or "singular" in template
        for ds in spec.data:
            matrix = ds.params.get("matrix")
            det = ds.params.get("det")
            if det == 0.0 or (matrix and isinstance(matrix, list) and len(matrix) == 4 and (matrix[0]*matrix[3] - matrix[1]*matrix[2] == 0)):
                is_singular = True

        if is_singular:
            has_null_space = any(
                "null_space" in v.type or "kernel" in v.type or "nullspace" in v.id.lower()
                for v in spec.visuals
            )
            if not has_null_space:
                issues.append(
                    ValidationIssue(
                        rule_id="LA-001",
                        domain="linear_algebra",
                        severity="error",
                        message="Singular transformation (det=0) animated without visualizing the collapsed null space.",
                        remediation=(
                            "Add a visual component representing the kernel/null space line or plane "
                            "to illustrate which subspace collapses to the origin."
                        ),
                    )
                )

        # LA-002: Basis vector preservation
        if "transform" in template or "linear" in template:
            vis_ids = {v.id.lower() for v in spec.visuals}
            has_i = any(any(pattern in vid for pattern in ["i_hat", "basis_i", "basis_x"]) for vid in vis_ids)
            has_j = any(any(pattern in vid for pattern in ["j_hat", "basis_j", "basis_y"]) for vid in vis_ids)
            has_basis = has_i and has_j
            if not has_basis and "trajectory" not in template:
                issues.append(
                    ValidationIssue(
                        rule_id="LA-002",
                        domain="linear_algebra",
                        severity="warning",
                        message="Linear transformation does not explicitly show standard basis vectors (i_hat, j_hat).",
                        remediation=(
                            "Include i_hat [1, 0] and j_hat [0, 1] basis vector visual components to anchor "
                            "the visual transformation to matrix column vectors."
                        ),
                    )
                )

    def _check_vector_calculus(
        self,
        spec: ScientificSceneSpec,
        issues: list[ValidationIssue],
    ) -> None:
        """Rules for vector fields, curl, divergence, and line/surface integrals."""
        template = spec.scene.template.lower()

        if "curl" in template:
            has_probe = any(
                p in v.type
                for v in spec.visuals
                for p in ["paddle_wheel", "circulation_loop", "circulation", "probe"]
            )
            if not has_probe:
                issues.append(
                    ValidationIssue(
                        rule_id="VC-002",
                        domain="vector_calculus",
                        severity="warning",
                        message="Curl visualization lacks a macroscopic/microscopic circulation probe.",
                        remediation=(
                            "Add a microscopic paddle wheel or circulation test loop to physically "
                            "demonstrate non-zero field rotation at the evaluation point."
                        ),
                    )
                )

    def _check_deep_learning(
        self,
        spec: ScientificSceneSpec,
        issues: list[ValidationIssue],
    ) -> None:
        """Rules for Deep Learning, activations, loss landscapes, and optimizers."""
        # DL-001: Activation Mathematical Bounds & Range Compliance
        for ds in spec.data:
            if ds.source == "function_sampler":
                fn = (ds.function or "").lower()
                if fn == "sigmoid":
                    x_rng = ds.x_range or [-5.0, 5.0]
                    # If wide domain, verify visual components provide asymptote anchors
                    has_asymptote = any(
                        "sigmoid" in (v.style.get("function", "").lower() if v.style else "")
                        for v in spec.visuals
                    )
                    # Check range sanity
                    if x_rng[0] > 0 or x_rng[1] < 0:
                        issues.append(
                            ValidationIssue(
                                rule_id="DL-001",
                                domain="deep_learning",
                                severity="error",
                                message="Sigmoid activation evaluated on domain not centered around 0.",
                                remediation="Ensure Sigmoid x_range spans negative and positive inputs (e.g. [-5.0, 5.0]) to demonstrate the non-linear transition.",
                            )
                        )
            elif ds.source == "softmax_normalizer":
                # Ensure logits are non-empty
                if not ds.logits:
                    issues.append(
                        ValidationIssue(
                            rule_id="DL-001",
                            domain="deep_learning",
                            severity="error",
                            message="Softmax normalizer configured without input logits.",
                            remediation="Provide an array of raw real-valued logits (e.g. [2.0, 1.0, 0.1]) to normalize into probabilities.",
                        )
                    )

        # DL-002: Monotonic / Defensible Optimization
        for ds in spec.data:
            if ds.source in ("optimization_tracer", "optimizer_path"):
                lr = ds.learning_rate
                if lr is not None and lr > 5.0:
                    # Unusually large learning rate without warning
                    issues.append(
                        ValidationIssue(
                            rule_id="DL-002",
                            domain="deep_learning",
                            severity="warning",
                            message=f"Learning rate ({lr}) is unusually large and may cause catastrophic explosion.",
                            remediation="Use learning rate <= 1.0 unless explicitly animating a diverging or oscillatory failure case.",
                        )
                    )

        # DL-003: Color Semantics Compliance
        # Inputs: Blue (#58C4DD), Weights: Green (#83C167), Activations: Yellow (#FFFF00), Loss: Red (#FF6666), Optimizer: Gold (#FFE66D)
        for vis in spec.visuals:
            v_type = vis.type
            style = vis.style or {}
            color = str(style.get("color", "")).upper()
            if v_type == "activation_plot":
                # Prefer yellow family
                if color in ("RED", "#FF0000", "#FF6666"):
                    issues.append(
                        ValidationIssue(
                            rule_id="DL-003",
                            domain="deep_learning",
                            severity="warning",
                            message="Activation plotted in Red (conventionally reserved for Loss/Error).",
                            remediation="Use Yellow (#FFFF00) for Activations according to the Deep Learning color semantics.",
                        )
                    )
            elif v_type == "optimizer_path":
                # Prefer gold/yellow family
                if color in ("#FF6666", "RED"):
                    issues.append(
                        ValidationIssue(
                            rule_id="DL-003",
                            domain="deep_learning",
                            severity="warning",
                            message="Optimizer trajectory plotted in Red instead of Gold (#FFE66D).",
                            remediation="Use Gold (#FFE66D) for optimizer paths to distinguish the parameter search path from the error magnitude.",
                        )
                    )

        # DL-004: 3D Loss Surface Depth Cues
        has_3d_loss = any(v.type in ("loss_landscape", "loss_surface") for v in spec.visuals)
        if has_3d_loss and spec.camera.type == "three_d":
            ambient_cfg = spec.camera.ambient_rotation
            if not ambient_cfg:
                issues.append(
                    ValidationIssue(
                        rule_id="DL-004",
                        domain="deep_learning",
                        severity="warning",
                        message="3D loss landscape rendered without ambient camera rotation.",
                        remediation="Enable camera.ambient_rotation (e.g. rate: 0.05) to provide kinetic depth cues for local valleys and saddles.",
                    )
                )

        # DL-005: Pacing & Temporal Resolution for Optimization
        for act in spec.timeline:
            if act.action in ("trace_path", "draw_and_trace") and act.run_time < 1.0:
                issues.append(
                    ValidationIssue(
                        rule_id="DL-005",
                        domain="deep_learning",
                        severity="warning",
                        message=f"Optimizer descent path animated with very fast run_time ({act.run_time}s).",
                        remediation="Increase run_time to >= 2.0s to allow viewers to observe step size adaptation and momentum rolling.",
                    )
                )
