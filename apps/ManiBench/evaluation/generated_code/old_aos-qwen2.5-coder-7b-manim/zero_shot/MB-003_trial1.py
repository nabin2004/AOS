from manim import *

class ConvolutionAnimation(Scene):
    def construct(self):
        # Create axes for signal and output
        signal_axes = Axes(
            x_range=[0, 5, 1],
            y_range=[0, 3, 1],
            axis_config={"color": BLUE},
        )
        output_axes = Axes(
            x_range=[0, 5, 1],
            y_range=[0, 8, 2],
            axis_config={"color": GREEN},
        )

        # Signal data points
        signal_data = [1, 2, 1, 0, 1]
        
        # Create signal bar chart
        signal_bar_chart = BarChart(
            values=signal_data,
            max_value=max(signal_data),
            bar_names=["", "", "", "", ""],
            label_y_axis="Amplitude",
            label_x_axis="Time",
            x_length=5,
            y_length=3,
            config={
                "x_start": 0,
                "y_start": 0,
                "x_direction": RIGHT,
                "y_direction": UP,
                "x_length": 5,
                "y_length": 3,
                "decimal_number_config": {"num_decimal_places": 0}
            }
        ).next_to(signal_axes, DOWN)

        # Kernel data points
        kernel_data = [1, -1, 1]

        # Create kernel bar chart
        kernel_bar_chart = BarChart(
            values=kernel_data,
            max_value=max(kernel_data),
            bar_names=["", "", ""],
            label_y_axis="Weight",
            label_x_axis="Filter Position",
            x_length=3,
            y_length=2,
            config={
                "x_start": 0,
                "y_start": 0,
                "x_direction": RIGHT,
                "y_direction": UP,
                "x_length": 3,
                "y_length": 2,
                "decimal_number_config": {"num_decimal_places": 0}
            }
        ).to_edge(LEFT)

        # Create output bar chart
        output_bar_chart = BarChart(
            values=[0]*len(signal_data),
            max_value=max(signal_data),
            bar_names=["", "", "", "", ""],
            label_y_axis="Sum",
            label_x_axis="Time",
            x_length=5,
            y_length=3,
            config={
                "x_start": 0,
                "y_start": 0,
                "x_direction": RIGHT,
                "y_direction": UP,
                "x_length": 5,
                "y_length": 3,
                "decimal_number_config": {"num_decimal_places": 0}
            }
        ).next_to(output_axes, DOWN)

        # Labels
        signal_label = Text("Signal").next_to(signal_axes, UP)
        kernel_label = Text("Kernel").next_to(kernel_bar_chart, UP)
        output_label = Text("Convolution Output").next_to(output_axes, UP)

        # Animation sequence
        self.play(Create(signal_axes), Create(signal_bar_chart))
        self.play(Create(kernel_axes), Create(kernel_bar_chart))
        self.play(Create(output_axes), Create(output_bar_chart))
        self.play(Write(signal_label), Write(kernel_label), Write(output_label))

        # Slide kernel across signal
        for i in range(len(signal_data)):
            # Highlight current slice of signal
            signal_slice = signal_bar_chart.get_bar(i)
            self.play(signal_slice.animate.set_fill(YELLOW, opacity=0.5))

            # Calculate convolution at this position
            conv_result = sum(a*b for a, b in zip(signal_data[i:i+len(kernel_data)], kernel_data))
            
            # Update output chart
            output_bar_chart.update_values([conv_result] + [0]*(len(signal_data)-i-1))
            
            # Move kernel one step right
            self.play(kernel_bar_chart.animate.shift(RIGHT*0.5))
            
            # Wait briefly before next step
            self.wait(0.5)

        self.wait(2)