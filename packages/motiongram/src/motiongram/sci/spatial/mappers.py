"""Spatial coordinate system specifications and mappers for scientific scenes."""

from __future__ import annotations

from motiongram.sci.schema import CoordinateSystemSpec


class CoordinateMapper:
    """Manages translation of data dimensions to Manim coordinate systems."""

    @staticmethod
    def get_axes_code(spec: CoordinateSystemSpec) -> str:
        """Generate Python code snippet that constructs the coordinate system in Manim."""
        if spec.type == "axes_3d":
            return (
                f"ThreeDAxes(\n"
                f"            x_range={spec.x_range},\n"
                f"            y_range={spec.y_range},\n"
                f"            z_range={spec.z_range},\n"
                f"            x_length={spec.x_length},\n"
                f"            y_length={spec.y_length},\n"
                f"            z_length={spec.z_length},\n"
                f"            axis_config={{\n"
                f"                'stroke_width': 1.5,\n"
                f"                'color': GREY_B,\n"
                f"                'font_size': 20,\n"
                f"            }},\n"
                f"            x_axis_config={{'color': '#4fc3f7'}},\n"  # light blue x
                f"            y_axis_config={{'color': '#aed581'}},\n"  # light green y
                f"            z_axis_config={{'color': '#ffcc80'}},\n"  # amber z
                f"        )"
            )
        elif spec.type == "axes_2d":
            return (
                f"Axes(\n"
                f"            x_range={spec.x_range},\n"
                f"            y_range={spec.y_range},\n"
                f"            x_length={spec.x_length},\n"
                f"            y_length={spec.y_length},\n"
                f"            axis_config={{\n"
                f"                'stroke_width': 1.8,\n"
                f"                'color': GREY_B,\n"
                f"                'font_size': 22,\n"
                f"            }},\n"
                f"        )"
            )
        elif spec.type == "number_plane":
            return (
                f"NumberPlane(\n"
                f"            x_range={spec.x_range},\n"
                f"            y_range={spec.y_range},\n"
                f"            background_line_style={{\n"
                f"                'stroke_color': GREY_D,\n"
                f"                'stroke_width': 0.8,\n"
                f"                'stroke_opacity': 0.6,\n"
                f"            }},\n"
                f"        )"
            )
        raise ValueError(f"Unknown coordinate system type: {spec.type}")
