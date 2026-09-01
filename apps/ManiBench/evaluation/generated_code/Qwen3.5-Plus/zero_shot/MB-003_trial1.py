from manim import *
import numpy as np

class ConvolutionAnimation(Scene):
    def construct(self):
        # Configuration
        signal_data = np.array([0, 0, 1, 2, 3, 2, 1, 0, 0])
        kernel_data = np.array([0.5, 1, 0.5])
        
        n_signals = len(signal_data)
        n_kernel = len(kernel_data)
        n_output = n_signals + n_kernel - 1
        
        # Calculate convolution manually for plotting
        output_data = np.convolve(signal_data, kernel_data, mode='full')
        
        # Scaling factors for visual clarity
        x_scale = 0.8
        y_scale = 0.5
        y_shift_signal = 2
        y_shift_output = -2
        
        # Create Axes
        axes_signal = Axes(
            x_range=[0, n_signals + 2, 1],
            y_range=[0, 4, 1],
            x_length=(n_signals + 2) * x_scale,
            y_length=4 * y_scale,
            axis_config={"include_tip": False, "numbers_to_exclude": [0]},
        ).shift(UP * y_shift_signal)
        
        axes_output = Axes(
            x_range=[0, n_output + 2, 1],
            y_range=[0, max(output_data) + 1, 1],
            x_length=(n_output + 2) * x_scale,
            y_length=(max(output_data) + 1) * y_scale,
            axis_config={"include_tip": False, "numbers_to_exclude": [0]},
        ).shift(DOWN * y_shift_output)

        # Labels
        label_signal = Text("Signal", font_size=24).next_to(axes_signal, UP, buff=0.5)
        label_kernel = Text("Kernel", font_size=24).next_to(axes_signal, RIGHT, buff=1.0).shift(UP * y_shift_signal)
        label_output = Text("Convolution Output", font_size=24).next_to(axes_output, UP, buff=0.5)
        
        self.add(axes_signal, axes_output, label_signal, label_output)

        # Plot Signal (Bar Chart style)
        signal_bars = VGroup()
        for i, val in enumerate(signal_data):
            bar = Rectangle(
                width=x_scale * 0.8,
                height=val * y_scale,
                stroke_width=0,
                fill_color=BLUE,
                fill_opacity=0.7
            )
            bar.next_to(axes_signal.c2p(i, 0), UP, buff=0)
            bar.align_to(bar, DOWN) # Ensure alignment to axis
            # Manual positioning to ensure it sits on the x-axis of the shifted axes
            bar.move_to(axes_signal.c2p(i, val/2), DOWN) 
            signal_bars.add(bar)
        
        self.play(Create(signal_bars))

        # Plot Kernel (Initial Position)
        # We will animate the kernel moving, so we create a movable group
        kernel_group = VGroup()
        kernel_bars = VGroup()
        kernel_label = Text("Kernel", font_size=16, color=YELLOW)
        
        for i, val in enumerate(kernel_data):
            bar = Rectangle(
                width=x_scale * 0.8,
                height=val * y_scale,
                stroke_width=2,
                stroke_color=YELLOW,
                fill_color=YELLOW,
                fill_opacity=0.3
            )
            # Position relative to a center point we will move
            bar.move_to(np.array([(i - 1) * x_scale, val * y_scale / 2, 0]), DOWN)
            kernel_bars.add(bar)
        
        kernel_group.add(kernel_bars)
        kernel_group.add(kernel_label)
        kernel_label.next_to(kernel_bars, UP, buff=0.1)
        
        # Initial position of kernel (centered over first valid signal index)
        # Let's start where the kernel fully overlaps or starts entering. 
        # Index 0 of kernel aligns with Index 0 of signal.
        start_pos = axes_signal.c2p(0, 0) + np.array([0, y_shift_signal, 0]) # Base of signal axis
        # Adjust to align the first bar of kernel with first bar of signal
        # The kernel bars are centered around x=0 in their local space (indices -1, 0, 1? No, 0, 1, 2)
        # Let's re-center kernel logic: indices 0, 1, 2. Center is 1.
        # We want index 0 of kernel at index 0 of signal.
        # Local x of kernel bar 0 is -1 * x_scale (if centered at 1). 
        # Let's simplify: Place kernel group such that its first bar aligns with signal index 0.
        
        # Re-defining kernel construction for easier alignment
        kernel_group = VGroup()
        k_bars = []
        for i, val in enumerate(kernel_data):
            bar = Rectangle(
                width=x_scale * 0.8,
                height=val * y_scale,
                stroke_width=2,
                stroke_color=YELLOW,
                fill_color=YELLOW,
                fill_opacity=0.3
            )
            bar.move_to(axes_signal.c2p(i, val/2), DOWN) # Temporarily place at 0,1,2
            k_bars.append(bar)
        
        kernel_bars = VGroup(*k_bars)
        kernel_label = Text("Kernel", font_size=16, color=YELLOW).next_to(kernel_bars, UP, buff=0.1)
        kernel_group = VGroup(kernel_bars, kernel_label)
        
        # Shift kernel so the first element is at x=0 (aligned with signal start)
        # Currently first element is at axes_signal.c2p(0, ...). This is perfect.
        # But we need to lift it up to the signal level? No, it overlays the signal.
        # The axes_signal is shifted UP. The bars are placed using axes_signal.c2p.
        # So they are already in the correct global position.
        
        self.add(kernel_group)

        # Output Graph Building
        output_dots = VGroup()
        output_lines = VGroup()
        
        # Animation Loop
        # We slide the kernel from left to right.
        # Total steps: n_output. 
        # At step k, kernel starts at signal index i such that we compute output[k].
        # Output index k corresponds to sum(signal[j] * kernel[k-j]).
        # Visually, we slide the kernel array across the signal array.
        
        # Let's define the movement of the kernel group.
        # The kernel group currently covers signal indices 0, 1, 2.
        # We want to slide it so the "window" moves.
        # Actually, standard convolution visualization: Kernel flips? 
        # For symmetric kernel [0.5, 1, 0.5], flip is same.
        # We slide the kernel from left (mostly outside) to right (mostly outside).
        
        # Reset kernel position to start where it just touches the signal from the left?
        # Let's start with kernel index 0 at signal index 0.
        current_kernel_x_offset = 0
        
        # Prepare output trace
        prev_point = None
        
        # We need to animate the sliding and the calculation simultaneously
        steps = n_output + n_kernel # Extra steps to clear
        
        # Let's create a specific animation for each output point
        # Output point k is generated when the kernel slides to position k.
        # Wait, if kernel is length 3. 
        # k=0: kernel[0]*sig[0] (kernel indices 0,1,2 over sig 0, -1, -2? No)
        # Standard discrete conv: y[n] = sum(x[m]h[n-m]).
        # Visual sliding: Place kernel at position n. Multiply overlapping parts.
        
        # Let's iterate n from 0 to n_output - 1
        for n in range(n_output):
            # Determine kernel position relative to signal
            # The kernel's index 0 should be at signal index (n - n_kernel + 1)?
            # Let's just move the visual kernel group.
            # Target: The center of the kernel (index 1) should be at signal index n?
            # No, let's align kernel index 0 to signal index (n - n_kernel + 1) is confusing.
            
            # Simple approach: 
            # The output at index `n` is the sum of products when the kernel is shifted by `n`.
            # Shift `n` means kernel[0] aligns with signal[n]? 
            # If kernel[0] aligns with signal[n], then we are computing correlation usually.
            # For convolution, kernel is flipped. Since symmetric, same.
            # Let's assume the visual shows kernel sliding from left to right.
            # Position `p`: Kernel starts at signal index `p`.
            # Then output index is `p + n_kernel - 1`? 
            # Let's just map the visual slide to the output index directly.
            
            # Visual: Kernel starts with its rightmost element at signal index 0?
            # Let's start with Kernel fully to the left, then slide in.
            
            # Let's calculate the target X position for the kernel group.
            # Currently kernel group bars are at x=0, 1, 2 (signal indices).
            # We want to shift the whole group by `shift_amount`.
            # If we shift by `s`, kernel bar i is at signal index `s + i`.
            # Overlap occurs when 0 <= s+i < n_signals.
            # Output index corresponding to shift `s`?
            # Usually output index k corresponds to shift k - (kernel_len - 1) ?
            # Let's just iterate shift `s` from -(n_kernel-1) to n_signals - 1.
            # Total shifts = n_signals + n_kernel - 1 = n_output.
            # Let s range from -2 to 8 (for our data).
            # s = -2: kernel indices 0,1,2 at sig -2, -1, 0. Overlap at sig[0] with kern[2].
            # This produces output[0].
            # s = 0: kernel 0,1,2 at sig 0,1,2. Produces output[2].
            # So output index k corresponds to shift s = k - (n_kernel - 1).
            
            s = n - (n_kernel - 1)
            
            # Move Kernel
            target_x = s * x_scale
            # Current kernel bars are at i * x_scale. 
            # We need to shift the group by (s * x_scale) relative to original?
            # Original: bar i at i * x_scale.
            # New: bar i at (s + i) * x_scale.
            # So shift the whole group by s * x_scale.
            
            # Animate Move
            self.play(
                kernel_group.animate.shift(RIGHT * (s * x_scale - (kernel_group.get_center()[0] - axes_signal.get_origin()[0]))),
                run_time=0.5
            )
            # Correction: The above shift logic is tricky because get_center changes.
            # Better: Explicitly set position or track offset.
            # Let's restart the loop logic with explicit positioning.
            pass

        # RE-DOING ANIMATION LOOP WITH CLEANER POSITIONING
        # Remove previous kernel
        self.remove(kernel_group)
        
        # Create fresh kernel group
        kernel_bars = VGroup()
        for i, val in enumerate(kernel_data):
            bar = Rectangle(
                width=x_scale * 0.8,
                height=val * y_scale,
                stroke_width=2,
                stroke_color=YELLOW,
                fill_color=YELLOW,
                fill_opacity=0.3
            )
            # Place relative to an anchor point (0,0) in local coordinates
            bar.move_to(np.array([i * x_scale, val * y_scale / 2, 0]), DOWN)
            kernel_bars.add(bar)
        
        kernel_label = Text("Kernel", font_size=16, color=YELLOW).next_to(kernel_bars, UP, buff=0.1)
        kernel_group = VGroup(kernel_bars, kernel_label)
        
        # Anchor point for kernel group: We want to control the position of index 0 of kernel.
        # Let's add a dummy dot at index 0 to track? Or just math.
        # Local center of kernel_bars is roughly at x = 1 * x_scale (middle of 0,1,2).
        # We want to place the group such that local x=0 is at global signal_x = s.
        # Global Pos of local point P = Group_Pos + P_local (if group centered at 0? No).
        # Manim: group.move_to(pos) moves the CENTER of the group to pos.
        # Center of kernel_bars (indices 0,1,2) is at local x = 1.0 * x_scale.
        # We want local x=0 to be at global X = s * x_scale + axes_signal.get_origin()[0].x
        # So Center should be at: (s * x_scale + origin_x) + (1.0 * x_scale).
        # Wait, if local 0 is at X_target, and local center is at +1 scale, then Center = X_target + 1*scale.
        
        origin_x = axes_signal.get_origin()[0]
        
        output_points = []
        
        for n in range(n_output):
            s = n - (n_kernel - 1) # Shift index
            
            # Calculate target center for kernel group
            # We want kernel index 0 to be at signal index s.
            # Signal index s global x: origin_x + s * x_scale
            # Kernel index 0 local x: 0 (relative to leftmost bar? No, bars are 0,1,2)
            # The group center is at local x = 1 * x_scale (average of 0,1,2).
            # So if we move group center to X_c, then local 0 is at X_c - 1*x_scale.
            # We want X_c - 1*x_scale = origin_x + s * x_scale
            # X_c = origin_x + (s + 1) * x_scale
            
            target_center_x = origin_x + (s + 1) * x_scale
            target_center_y = axes_signal.get_origin()[1] + y_shift_signal # Keep Y aligned with signal axis base? 
            # Actually, the bars were created with heights. The center Y is half max height.
            # We just need to match the Y level of the signal bars.
            # Signal bars are on axes_signal. Kernel bars should overlay them.
            # axes_signal is shifted. The bars are placed absolutely.
            # Let's just match the Y coordinate of the kernel group to the signal bars.
            # The signal bars are drawn using axes_signal.c2p.
            # The kernel bars are drawn using absolute coordinates based on x_scale and y_scale.
            # We need to ensure the kernel group Y position matches the signal axis Y position.
            # Signal axis origin is at (0, y_shift_signal).
            # Kernel bars are drawn from y=0 to y=h.
            # We need to shift kernel group UP by y_shift_signal.
            
            target_point = np.array([target_center_x, y_shift_signal + (max(kernel_data)*y_scale)/2, 0])
            # Wait, simpler: Just shift the group so its bottom aligns with axis?
            # Let's rely on the fact that we created bars with specific heights.
            # We want the bottom of kernel bars to be at y = y_shift_signal.
            # Current bottom of kernel bars (local) is 0.
            # So we need to shift the group UP by y_shift_signal.
            # And shift RIGHT by (s + 1) * x_scale - (current_center_x_offset).
            # Initial group center (s=0 logic): 
            # If we place group at origin, center is at x=1*x_scale, y=avg_height.
            # Let's just use .move_to() on a specific reference point?
            # Easier: Create a Dot at the "anchor" (index 0 of kernel) and move that?
            
            # Let's use a simpler trick: 
            # Define the position of the first bar (index 0).
            # Local pos of first bar center: x = 0.5 * width? No, move_to was used.
            # bar.move_to([i*x_scale, h/2, 0], DOWN). 
            # This means the bottom-center of the bar is at [i*x_scale, 0, 0].
            # So the bottom-left of the first bar is at [-width/2, 0, 0].
            # This is getting messy. Let's recreate kernel bars simply.
            
            pass # Break to rewrite kernel creation for simplicity

        # FINAL CLEAN IMPLEMENTATION OF LOOP
        self.remove(kernel_group)
        
        # Re-create kernel bars with simple geometry relative to (0,0,0)
        kernel_bars = VGroup()
        for i, val in enumerate(kernel_data):
            bar = Rectangle(
                width=x_scale * 0.8,
                height=val * y_scale,
                stroke_width=2,
                stroke_color=YELLOW,
                fill_color=YELLOW,
                fill_opacity=0.3
            )
            # Place bar such that its bottom-left corner is at (i * x_scale, 0, 0)
            # Actually, let's center the bar at (i * x_scale + half_width, height/2)
            center_x = i * x_scale + (x_scale * 0.8) / 2
            center_y = (val * y_scale) / 2
            bar.move_to(np.array([center_x, center_y, 0]))
            kernel_bars.add(bar)
            
        kernel_label = Text("Kernel", font_size=16, color=YELLOW)
        kernel_label.next_to(kernel_bars, UP, buff=0.1)
        kernel_group = VGroup(kernel_bars, kernel_label)
        
        # Now, the "reference point" for alignment: 
        # We want the left edge of the first bar (index 0) to align with signal index s.
        # Left edge of first bar local x: 0 (since center is half_width, left is 0).
        # Signal index s left edge: axes_signal.c2p(s, 0)[0] - (bar_width/2).
        # Actually, signal bars are centered at integer indices.
        # Signal bar i center: axes_signal.c2p(i, 0)[0].
        # Kernel bar i center should be at axes_signal.c2p(s+i, 0)[0].
        # So we need to shift the kernel group such that:
        # Local center of kernel bar 0 + Shift = Global center of signal bar s.
        # Local center of kernel bar 0: x = (x_scale * 0.8) / 2.
        # Global center of signal bar s: origin_x + s * x_scale.
        # Shift_X = (origin_x + s * x_scale) - (x_scale * 0.8 / 2).
        
        # Let's pre-calculate the shift needed for s=0 to set initial position
        s_start = -(n_kernel - 1)
        # We will animate from s = -(n_kernel-1) to n_signals - 1
        
        # Initial Position (s = s_start)
        # But let's just loop and animate the transition.
        
        current_s = -(n_kernel - 1) - 1 # Start one step before
        
        for n in range(n_output):
            s = n - (n_kernel - 1)
            
            # Calculate target position for the group
            # We want kernel bar i to be at signal index s+i
            # Target center for kernel bar 0:
            target_bar0_x = axes_signal.c2p(s, 0)[0]
            local_bar0_x = (x_scale * 0.8) / 2
            shift_x = target_bar0_x - local_bar0_x
            
            # Target Y: align bottoms. Signal axis is at y_shift_signal.
            # Kernel bars are built from y=0 up. So shift Y by y_shift_signal.
            target_y = y_shift_signal + kernel_group.get_center()[1] # Maintain relative Y?
            # No, just shift so bottom is at y_shift_signal.
            # Current bottom of kernel_group: get_bottom()[1]
            # Target bottom: y_shift_signal
            # shift_y = y_shift_signal - kernel_group.get_bottom()[1]
            # But since we are moving incrementally, let's just set the position of a reference.
            
            # Easiest: Move the group so that a specific point matches.
            # Let's create a dummy dot in the group at the local coordinate of bar0 center?
            # No, just calculate the destination center of the whole group.
            # Group center local X: average of bar centers.
            # Bars at 0.4, 1.2, 2.0 (if scale 0.8, step 1? No step is x_scale=0.8? No x_scale=0.8 is step)
            # Wait, x_scale is 0.8. Bar width is 0.8*0.8 = 0.64.
            # Bar centers: 0.32, 1.12, 1.92. Center of group = 1.12.
            # Target for bar 0: axes_signal.c2p(s,0).x
            # Target for group center: axes_signal.c2p(s,0).x + (1.12 - 0.32) = axes_signal.c2p(s,0).x + 0.8
            # Generally: Target Group X = axes_signal.c2p(s,0).x + (Group_Local_Center_X - Bar0_Local_X)
            
            group_local_center_x = kernel_group.get_center()[0] # In local coords if at origin? 
            # Since we created it at origin-ish, this is the offset.
            # Actually, kernel_group is currently at some position. Let's reset it to 0,0 first?
            # No, let's just compute the absolute target position for the group's center.
            
            # Reference: Kernel Bar 0 center local X
            ref_local_x = (x_scale * 0.8) / 2
            # Group center local X (relative to bar 0)
            # Since bars are 0, 1, 2 steps of x_scale.
            # Centers: ref, ref+x_scale, ref+2*x_scale.
            # Average: ref + x_scale.
            offset_to_center = x_scale 
            
            target_group_x = axes_signal.c2p(s, 0)[0] + offset_to_center
            target_group_y = y_shift_signal + (kernel_group.get_height() / 2) # Center vertically on axis line?
            # No, bars sit ON the line. So center Y = y_shift_signal + height/2.
            
            target_point = np.array([target_group_x, target_group_y, 0])
            
            # Animate Move
            if n == 0:
                kernel_group.move_to(target_point)
                self.add(kernel_group)
            else:
                self.play(kernel_group.animate.move_to(target_point), run_time=0.4)
            
            # Calculate Convolution Value for this step (output[n])
            val = output_data[n]
            
            # Highlight Overlap (Optional visual flair: change color of overlapping bars)
            # Skipping complex overlap detection for brevity, relying on position.
            
            # Plot Output Point
            out_x = axes_output.c2p(n, 0)[0]
            out_y = axes_output.c2p(0, val)[1]
            point = Dot(np.array([out_x, out_y, 0]), color=GREEN)
            
            # Draw line from previous point
            if n == 0:
                line = Line(axes_output.c2p(0,0), np.array([out_x, out_y, 0]), color=GREEN)
            else:
                line = Line(prev_point, np.array([out_x, out_y, 0]), color=GREEN)
            
            self.play(
                Create(line),
                FadeIn(point),
                run_time=0.4
            )
            
            prev_point = np.array([out_x, out_y, 0])
            output_dots.add(point)
            output_lines.add(line)

        self.wait(1)