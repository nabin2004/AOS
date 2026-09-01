from manim import *

class FundamentalTheoremOfCalculus(Scene):
    """
    An animation demonstrating the Fundamental Theorem of Calculus by showing
    the relationship between the area under a derivative curve and the value
    of the original function.
    """
    def construct(self):
        # CONFIGURATION
        # Define axes properties for a consistent look
        axes_config = {
            "x_range": [-0.5, 8.5, 1],
            "x_length": 7,
            "axis_config": {"include_tip": False, "color": GREY_A},
        }

        # Create two sets of axes: one for f(x) and its integral, one for f'(x)
        axes_top = Axes(**axes_config, y_range=[-1, 9, 1], y_length=3).to_edge(UP)
        axes_bottom = Axes(**axes_config, y_range=[-0.5, 2, 0.5], y_length=2).to_edge(DOWN)
        
        # Add labels to the axes
        labels_top = axes_top.get_axis_labels(x_label="x", y_label="y")
        labels_bottom = axes_bottom.get_axis_labels(x_label="x", y_label="f'(x)")
        
        # Define the functions to be plotted
        # f(x)