"""Compiler for Scientific Simulation and Animation DSL scenes."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import yaml
from jinja2 import Environment, FileSystemLoader

from motiongram.sci.schema import (
    ScientificSceneSpec,
    VisualComponentSpec,
)
from motiongram.sci.solvers.base import DataResult
from motiongram.sci.solvers.dl_solvers import DeepLearningDataSolver
from motiongram.sci.solvers.metrics import DerivedMetric
from motiongram.sci.solvers.ode import ODESolver
from motiongram.sci.spatial.mappers import CoordinateMapper
from motiongram.sci.visuals.dl_visuals import DeepLearningVisualCodeGenerator
from motiongram.sci.visuals.inset import InsetCodeGenerator
from motiongram.sci.visuals.trajectory import TrajectoryCodeGenerator

TEMPLATES_DIR = Path(__file__).parent / "templates"


class ScientificCompiler:
    """Compiles a ScientificSceneSpec into executable ManimCE Python code."""

    def __init__(self, template_dir: Path | None = None):
        t_dir = template_dir or TEMPLATES_DIR
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(t_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def solve_data(
        self, spec: ScientificSceneSpec, quality: str = "final"
    ) -> dict[str, DataResult]:
        """Precompute all data sources and derived metrics."""
        results: dict[str, DataResult] = {}
        ode_solver = ODESolver()
        metric_solver = DerivedMetric()
        dl_solver = DeepLearningDataSolver()

        # Pass 1: Solve primary ODEs
        for ds in spec.data:
            if ds.source == "ode_solver":
                results[ds.id] = ode_solver.solve(ds, quality=quality)

        # Pass 2: Solve Deep Learning data sources
        for ds in spec.data:
            if ds.source in (
                "function_sampler",
                "analytical_surface",
                "loss_surface",
                "optimization_tracer",
                "optimizer_path",
                "softmax_normalizer",
            ):
                results[ds.id] = dl_solver.solve(ds, quality=quality)

        # Pass 3: Solve derived metrics
        for ds in spec.data:
            if ds.source == "derived_metric":
                results[ds.id] = metric_solver.solve(
                    ds, quality=quality, input_results=results
                )

        return results

    def compile(self, spec: ScientificSceneSpec, quality: str = "final") -> str:
        """Compile a ScientificSceneSpec into Python source code."""
        # 1. Run simulation precomputation
        data_results = self.solve_data(spec, quality=quality)

        # Prepare formatted data arrays for script embedding
        data_arrays: dict[str, str] = {}
        for ds_id, res in data_results.items():
            pts = np.round(res.points, 4).tolist()
            data_arrays[ds_id] = repr(pts)

        # 2. Camera & Base Class Setup
        is_3d = spec.camera.type == "three_d"
        has_voiceover = bool(spec.narration and spec.narration.text)

        if is_3d:
            base_classes = "VoiceoverScene, ThreeDScene" if has_voiceover else "ThreeDScene"
        else:
            base_classes = "VoiceoverScene, Scene" if has_voiceover else "Scene"

        # Auto-framing calculation
        camera_dict = spec.camera.model_dump()
        if spec.camera.auto_fit:
            cs_3d = [cs for cs in spec.coordinate_systems if cs.type == "axes_3d"]
            has_inset_right = any(
                v.type == "inset_graph" and getattr(v, "position", "UR").upper() in ("UR", "RIGHT", "DR")
                for v in spec.visuals
            )
            has_inset_left = any(
                v.type == "inset_graph" and getattr(v, "position", "UR").upper() in ("UL", "LEFT", "DL")
                for v in spec.visuals
            )

            if is_3d and cs_3d:
                primary_cs = cs_3d[0]
                lx = primary_cs.x_length
                ly = primary_cs.y_length
                lz = primary_cs.z_length
                d_3d = float(np.sqrt(lx**2 + ly**2 + lz**2))

                # Safe screen height is ~6.8. In 3D perspective projection, apparent diameter is ~0.70 * d_3d
                # Target apparent diameter <= 5.8 with inset, <= 6.6 without inset
                target_h = 5.8 if (has_inset_right or has_inset_left) else 6.6
                calc_zoom = round(min(0.85, (target_h / max(d_3d, 1.0)) * 1.45), 2)

                if spec.camera.zoom is None:
                    camera_dict["zoom"] = calc_zoom

                if spec.camera.frame_center is None:
                    if has_inset_right:
                        camera_dict["frame_center"] = [1.2, 0.0, 0.0]
                    elif has_inset_left:
                        camera_dict["frame_center"] = [-1.2, 0.0, 0.0]
                    else:
                        camera_dict["frame_center"] = [0.0, 0.0, 0.0]

        # 3. Coordinate Systems
        coord_systems: list[dict[str, str]] = []
        for cs in spec.coordinate_systems:
            coord_systems.append({
                "id": cs.id,
                "code": CoordinateMapper.get_axes_code(cs),
            })
        default_axes = spec.coordinate_systems[0].id if spec.coordinate_systems else "axes3d"

        # 4. Visual Components
        visual_codes: list[str] = []
        vis_map: dict[str, VisualComponentSpec] = {v.id: v for v in spec.visuals}

        for vis in spec.visuals:
            axes_id = vis.coordinate_system or default_axes
            pts_var = f"{vis.source}_pts" if vis.source else "[]"

            if vis.type == "trajectory_curve":
                code = TrajectoryCodeGenerator.generate_curve(vis, pts_var, axes_id)
                visual_codes.append(code)
            elif vis.type == "tracer_dot":
                code = TrajectoryCodeGenerator.generate_tracer_dot(
                    vis, pts_var, axes_id, is_3d=is_3d
                )
                visual_codes.append(code)
            elif vis.type in ("dynamic_line", "divergence_line"):
                code = TrajectoryCodeGenerator.generate_dynamic_line(vis)
                visual_codes.append(code)
            elif vis.type == "inset_graph":
                code = InsetCodeGenerator.generate_inset_graph(vis, pts_var, is_3d=is_3d)
                visual_codes.append(code)
            elif vis.type in ("vector_field_3d", "vector_field_2d", "vector_field"):
                code = TrajectoryCodeGenerator.generate_vector_field(vis, axes_id, is_3d=is_3d)
                visual_codes.append(code)
            elif vis.type == "vector_arrow":
                code = TrajectoryCodeGenerator.generate_vector_arrow(vis, axes_id)
                visual_codes.append(code)
            elif vis.type in ("null_space_subspace", "null_space"):
                code = TrajectoryCodeGenerator.generate_null_space(vis, axes_id)
                visual_codes.append(code)
            elif vis.type == "paddle_wheel":
                code = TrajectoryCodeGenerator.generate_paddle_wheel(vis, axes_id)
                visual_codes.append(code)
            elif vis.type == "number_plane":
                code = TrajectoryCodeGenerator.generate_number_plane(vis, axes_id)
                visual_codes.append(code)
            elif vis.type == "activation_plot":
                code = DeepLearningVisualCodeGenerator.generate_activation_plot(vis, pts_var, axes_id)
                visual_codes.append(code)
            elif vis.type in ("loss_landscape", "loss_surface"):
                code = DeepLearningVisualCodeGenerator.generate_loss_landscape(vis, pts_var, axes_id)
                visual_codes.append(code)
            elif vis.type == "optimizer_path":
                code = DeepLearningVisualCodeGenerator.generate_optimizer_path(vis, pts_var, axes_id)
                visual_codes.append(code)
            elif vis.type == "network_graph":
                code = DeepLearningVisualCodeGenerator.generate_network_graph(vis, axes_id)
                visual_codes.append(code)
            elif vis.type == "tensor_grid":
                code = DeepLearningVisualCodeGenerator.generate_tensor_grid(vis, axes_id)
                visual_codes.append(code)

        # 5. Timeline Action Blocks
        timeline_blocks: list[str] = []
        ambient_cfg = spec.camera.ambient_rotation or {}
        ambient_rate = ambient_cfg.get("rate", 0.07)
        ambient_start_after = ambient_cfg.get("start_after")
        ambient_started = False

        for act in spec.timeline:
            block_lines: list[str] = []

            # Handle trigger waiting
            if act.at.startswith("bookmark:"):
                bm_name = act.at.split(":", 1)[1]
                block_lines.append(f'self.wait_until_bookmark("{bm_name}")')
                if ambient_start_after == bm_name and not ambient_started:
                    block_lines.append(
                        f"self.begin_ambient_camera_rotation(rate={ambient_rate})"
                    )
                    ambient_started = True
            elif act.at.startswith("after:"):
                block_lines.append("self.wait(0.5)")
            elif act.at == "start" and not ambient_started and not ambient_start_after:
                if ambient_cfg:
                    block_lines.append(
                        f"self.begin_ambient_camera_rotation(rate={ambient_rate})"
                    )
                    ambient_started = True
            elif act.at != "start":
                block_lines.append(f'self.wait_until_bookmark("{act.at}")')

            # Handle action execution
            if act.action == "create":
                if act.targets:
                    t_str = ", ".join(f"Create({t})" for t in act.targets)
                    block_lines.append(f"self.play({t_str}, run_time={act.run_time})")
                else:
                    target = act.target or "None"
                    block_lines.append(
                        f"self.play(Create({target}), run_time={act.run_time})"
                    )
            elif act.action == "reveal":
                if act.targets:
                    t_str = ", ".join(f"FadeIn({t})" for t in act.targets)
                    block_lines.append(f"self.play({t_str}, run_time={act.run_time})")
                else:
                    target = act.target or "None"
                    block_lines.append(
                        f"self.play(FadeIn({target}), run_time={act.run_time})"
                    )
            elif act.action in ("fade_out", "remove"):
                if act.targets:
                    t_str = ", ".join(f"FadeOut({t})" for t in act.targets)
                    block_lines.append(f"self.play({t_str}, run_time={act.run_time})")
                else:
                    target = act.target or "None"
                    block_lines.append(
                        f"self.play(FadeOut({target}), run_time={act.run_time})"
                    )
            elif act.action == "rotate":
                target = act.target or (act.targets[0] if act.targets else "None")
                duration = act.duration or act.run_time
                block_lines.append(
                    f"self.play(Rotate({target}, angle=2*PI, run_time={duration}, rate_func=linear))"
                )
            elif act.action == "transform":
                target = act.target or (act.targets[0] if act.targets else "None")
                block_lines.append(
                    f"self.play({target}.animate.apply_matrix([[2, 4], [1, 2]]), run_time={act.run_time})"
                )
            elif act.action in ("trace_path", "trace"):
                target = act.target or (act.targets[0] if act.targets else "None")
                rate_arg = f", rate_func={act.rate_func}" if act.rate_func else ""
                block_lines.append(f"self.play(Create({target}), run_time={act.run_time}{rate_arg})")
            elif act.action == "pulse_forward":
                target = act.target or (act.targets[0] if act.targets else "None")
                block_lines.append(f"self.play(Indicate({target}, color='#ffff00', scale_factor=1.1), run_time={act.run_time})")
            elif act.action == "pulse_backprop":
                target = act.target or (act.targets[0] if act.targets else "None")
                block_lines.append(f"self.play(Indicate({target}, color='#ff4081', scale_factor=1.15), run_time={act.run_time})")
            elif act.action == "draw_and_trace":
                targets = act.targets or ([act.target] if act.target else [])

                def is_type(tid: str, expected_type: str) -> bool:
                    v = vis_map.get(tid)
                    return v.type == expected_type if v else False

                curves = [t for t in targets if is_type(t, "trajectory_curve")]
                dots = [t for t in targets if is_type(t, "tracer_dot")]

                anims = []
                for c in curves:
                    anims.append(f"Create({c})")
                for d in dots:
                    # Match dot with curve by source or order
                    d_vis = vis_map.get(d)
                    matched_curve = None
                    if d_vis and d_vis.source:
                        for c in curves:
                            c_vis = vis_map.get(c)
                            if c_vis and c_vis.source == d_vis.source:
                                matched_curve = c
                                break
                    if not matched_curve and curves:
                        matched_curve = curves[0]
                    if matched_curve:
                        anims.append(f"MoveAlongPath({d}, {matched_curve})")

                rate_arg = f", rate_func={act.rate_func}" if act.rate_func else ""
                anims_joined = ", ".join(anims)
                block_lines.append(
                    f"self.play(AnimationGroup({anims_joined}, run_time={act.run_time}{rate_arg}))"
                )
            elif act.action == "hold":
                duration = act.duration if act.duration is not None else act.run_time
                block_lines.append(f"self.wait({duration})")
            elif act.action == "write_equations":
                block_lines.append("# Equations write-up")

            if block_lines:
                timeline_blocks.append("\n            ".join(block_lines))

        # 6. Render Jinja template
        template = self.jinja_env.get_template("sci_scene.py.jinja")
        class_name = f"Scene_{re.sub(r'[^a-zA-Z0-9_]', '_', spec.scene.id)}"

        return template.render(
            scene=spec.scene,
            class_name=class_name,
            base_classes=base_classes,
            is_3d=is_3d,
            camera=camera_dict,
            has_voiceover=has_voiceover,
            narration=spec.narration,
            data_arrays=data_arrays,
            coordinate_systems=coord_systems,
            visual_components_code=visual_codes,
            timeline_blocks=timeline_blocks,
        )

    @classmethod
    def compile_yaml(cls, yaml_content: str, quality: str = "final") -> str:
        """Parse YAML string into ScientificSceneSpec and compile."""
        raw_dict = yaml.safe_load(yaml_content)
        spec = ScientificSceneSpec.model_validate(raw_dict)
        return cls().compile(spec, quality=quality)
