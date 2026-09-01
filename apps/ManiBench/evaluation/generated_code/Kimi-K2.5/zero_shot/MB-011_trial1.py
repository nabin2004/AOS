from manim import *
import numpy as np

class HairyBallTheorem(ThreeDScene):
    def construct(self):
        # Camera setup
        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES, zoom=0.9)
        
        # Title and labels (fixed in frame)
        title = Text("The Hairy Ball Theorem", font_size=40, color=WHITE)
        subtitle = Text("A continuous tangent vector field on a sphere must have a zero", 
                       font_size=24, color=YELLOW)
        title.to_edge(UP)
        subtitle.next_to(title, DOWN, buff=0.3)
        
        explanation = Text("Attempting to 'comb' the hair creates a bald spot...", 
                          font_size=22, color=GREEN)
        explanation.to_edge(DOWN)
        
        self.add_fixed_in_frame_mobjects(title, subtitle)
        
        # Create the sphere
        sphere = Sphere(radius=2, resolution=(40, 40))
        sphere.set_color(BLUE_E)
        sphere.set_opacity(0.3)
        sphere.set_stroke(BLUE_D, width=0.5, opacity=0.4)
        
        self.play(Create(sphere), run_time=2)
        self.wait()
        
        # Value tracker for the combing animation (0 = east, 1 = north)
        comb_factor = ValueTracker(0)
        
        # Create the vector field with updater
        vector_field = always_redraw(
            lambda: self.create_vector_field(sphere, comb_factor.get_value())
        )
        
        # Phase 1: Show initial field (tangent to latitudes)
        self.play(FadeIn(vector_field), run_time=2)
        self.wait()
        
        # Rotate camera to show the 3D structure
        self.move_camera(theta=150 * DEGREES, phi=60 * DEGREES, run_time=4)
        self.wait()
        
        # Phase 2: Animate the combing process
        self.add_fixed_in_frame_mobjects(explanation)
        self.play(
            comb_factor.animate.set_value(1),
            run_time=6,
            rate_func=smooth
        )
        self.wait(2)
        
        # Phase 3: Highlight the bald spot at the north pole
        self.highlight_bald_spot(sphere)
        self.wait(2)
        
        # Show that the south pole also has issues or show discontinuity attempt
        self.show_impossibility(sphere, comb_factor)
        self.wait(3)
    
    def create_vector_field(self, sphere, comb_factor, num_lat=10, num_long=20):
        """Create a tangent vector field on the sphere"""
        radius = sphere.radius
        vectors = VGroup()
        
        for i in range(num_lat):
            # Latitude angle (0 = north pole, pi = south pole)
            theta = np.pi * (i + 0.5) / num_lat
            
            for j in range(num_long):
                # Longitude angle
                phi = 2 * np.pi * j / num_long
                
                # Position on sphere
                x = radius * np.sin(theta) * np.cos(phi)
                y = radius * np.sin(theta) * np.sin(phi)
                z = radius * np.cos(theta)
                pos = np.array([x, y, z])
                
                # Calculate tangent vector based on comb factor
                direction = self.get_tangent_direction(pos, radius, comb_factor)
                
                # Magnitude decreases as we approach north pole when combing
                # This demonstrates the "bald spot" formation
                dist_from_north = np.sin(theta)  # 0 at north, 1 at equator
                
                if comb_factor > 0:
                    # As we comb toward north, vectors near north pole must shrink
                    magnitude = 0.5 * (1 - comb_factor) + 0.5 * dist_from_north
                else:
                    magnitude = 0.5
                
                # Skip if magnitude is too small (bald spot)
                if magnitude < 0.05:
                    continue
                
                end_pos = pos + direction * magnitude
                
                # Color coding: Red = small (bald), Blue = full
                color = interpolate_color(RED, BLUE, magnitude * 2)
                
                arrow = Arrow3D(
                    start=pos,
                    end=end_pos,
                    color=color,
                    thickness=0.015
                )
                vectors.add(arrow)
        
        return vectors
    
    def get_tangent_direction(self, pos, radius, comb_factor):
        """Calculate unit tangent vector at position"""
        x, y, z = pos
        r = radius
        
        # East-pointing vector (tangent to latitude)
        # Cross product of normal (pos) with north pole direction (0,0,1)
        east = np.array([-y, x, 0])
        east_norm = np.linalg.norm(east)
        if east_norm > 0.001:
            east = east / east_norm
        else:
            east = np.array([1, 0, 0])  # Arbitrary at pole
        
        # North-pointing vector (tangent toward north pole)
        # Projection of (0,0,1) onto tangent plane
        north = np.array([0, 0, r]) - (z/r) * pos
        north_norm = np.linalg.norm(north)
        if north_norm > 0.001:
            north = north / north_norm
        else:
            north = np.array([0, 0, 0])
        
        # Interpolate between east and north
        direction = (1 - comb_factor) * east + comb_factor * north
        
        # Normalize
        dir_norm = np.linalg.norm(direction)
        if dir_norm > 0.001:
            direction = direction / dir_norm
        
        return direction
    
    def highlight_bald_spot(self, sphere):
        """Highlight the zero vector location at north pole"""
        north_pole = np.array([0, 0, sphere.radius])
        
        # Create glowing sphere at north pole
        bald_spot = Sphere(radius=0.25, resolution=(20, 20))
        bald_spot.move_to(north_pole)
        bald_spot.set_color(RED)
        bald_spot.set_opacity(0.9)
        
        # Glow effect
        glow = Sphere(radius=0.4, resolution=(20, 20))
        glow.move_to(north_pole)
        glow.set_color(RED)
        glow.set_opacity(0.3)
        
        # Label
        label = Text("Bald Spot\n(v = 0)", font_size=24, color=RED)
        label.next_to(bald_spot, UP, buff=0.5)
        # Position label in 3D space near the pole but offset
        label.shift(UP * 0.5 + RIGHT * 0.5)
        
        self.add_fixed_in_frame_mobjects(label)
        
        # Pulse animation
        self.play(
            FadeIn(glow),
            FadeIn(bald_spot),
            run_time=1
        )
        self.play(
            glow.animate.scale(1.3).set_opacity(0.1),
            run_time=1.5,
            rate_func=there_and_back
        )
        
        return VGroup(bald_spot, glow, label)
    
    def show_impossibility(self, sphere, comb_tracker):
        """Show that avoiding the zero creates discontinuity"""
        # Reset comb factor slightly to show the conflict
        self.play(comb_tracker.animate.set_value(0.9), run_time=2)
        
        # Add text explaining
        text = Text("Cannot avoid the zero!\nSum of indices = Euler Characteristic = 2", 
                   font_size=22, color=ORANGE)
        text.to_edge(DOWN)
        self.add_fixed_in_frame_mobjects(text)
        
        # Flash the bald spot
        flash = Sphere(radius=0.3, resolution=(20, 20))
        flash.move_to([0, 0, sphere.radius])
        flash.set_color(YELLOW)
        flash.set_opacity(0.5)
        
        self.play(
            FadeIn(flash),
            run_time=0.5
        )
        self.play(
            FadeOut(flash),
            run_time=0.5
        )
        
        self.wait(2)