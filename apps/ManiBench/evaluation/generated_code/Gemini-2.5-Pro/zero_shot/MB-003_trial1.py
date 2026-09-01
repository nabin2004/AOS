from manim import *
import numpy as np

class Convolution1D(Scene):
    """
    An animation demonstrating the 1D convolution operation.
    The animation shows a kernel sliding over a signal, the element-wise
    products being calculated, their sum being computed, and the final
    result being plotted on an output graph.
    """
    def construct(self):
        # 1. Define data and parameters
        signal_data = [0, 1, 2, 3, 2.5, 1.5, 0.5, 0]
        kernel_data = [0.5, 1, 0.5]
        
        # For the convolution visualization, we use a padded signal
        # to show the kernel sliding in and out completely.
        padding_len = len(kernel_data) - 1
        padded_signal_data = np.pad(signal_data, (padding_len, padding_len), 'constant')
        
        # The ground truth convolution result, for plotting
        conv_output_data = np.convolve(signal_data, kernel_data, mode='full')

        # Axis and Bar Chart configurations
        axis_config = {"include_tip": False, "label_direction": DOWN}
        bar_chart_config = {"bar_width": 0.6, "bar_fill_opacity": 0.7}

        # 2. Create Axes