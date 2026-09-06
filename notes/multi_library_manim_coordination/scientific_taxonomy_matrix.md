# Scientific Taxonomy Matrix for Multi-Library SFT Data Generation

This matrix establishes the combinatorial grid for generating diverse, challenging, and pedagogically sound training examples. By sampling from across these distinct axes, we prevent topic collapse and ensure fine-tuned models can generalize across both numerical mathematics and visual animation patterns.

---

## Axis 1: Scientific Engines & Numerical Primitives

| Category | Library Function | Canonical Scientific Topics | Visual Representation |
|----------|------------------|-----------------------------|-----------------------|
| **ODEs & Dynamical Systems** | `scipy.integrate.solve_ivp` | Lorenz Attractor, Rössler Attractor, Double Pendulum, Lotka-Volterra Predator-Prey, Van der Pol Oscillator | 3D parametric trajectories, phase portraits, velocity vector fields |
| **Optimization & Landscapes** | `scipy.optimize.minimize` | Rosenbrock Valley ("banana function"), Gradient Descent on Quadratic Bowls, Rastrigin Multi-Modal Surface | Surface3D with path tracing, contour lines with descending iteration dots |
| **Fourier & Signal Processing** | `scipy.signal` / `numpy.fft` | Square Wave Fourier Decomposition, Convolution of Pulses, High/Low Pass Filters, Audio Waveform Spectrum | Summation of rotating epicycles, animated convolution sliding windows, frequency domain bars |
| **Curve Fitting & Interpolation** | `scipy.interpolate.splprep` / `interp1d` | Spline path smoothing, noisy scientific data regression, Bezier path fitting | Scatter points with animated tightening B-spline curve |
| **Computational Geometry** | `scipy.spatial.Voronoi` / `Delaunay` | Cellular automata partitions, network triangulation, sensor coverage maps | Dynamic seed dots with evolving Voronoi polygonal cell boundaries |
| **Linear Algebra & Transforms** | `numpy.linalg.eig` / `svd` | Matrix transformation of unit circle into ellipse, Principal Component Analysis (PCA), Eigenvectors | Transformed grid, unit vectors stretching along principal axes |

---

## Axis 2: Manim Visual Classes & Camera Paradigms

| Scene Archetype | Primary Manim Classes | Key Methods / Idioms | Target Use Case |
|-----------------|-----------------------|----------------------|-----------------|
| **3D State Space** | `ThreeDScene`, `ThreeDAxes`, `Surface` | `self.set_camera_orientation()`, `self.begin_ambient_camera_rotation()`, `axes.c2p()` | Chaotic attractors, 3D loss functions, multivariable vector calculus |
| **Moving Focus / Zoom** | `MovingCameraScene` | `self.camera.frame.animate.set(width=...).move_to()` | Zooming in on critical points, following a gradient descent trajectory in detail |
| **Vector Space & Fields** | `Scene`, `ArrowVectorField`, `StreamLines` | `ArrowVectorField(func)`, `StreamLines(func).start_animation()` | Fluid dynamics, phase portraits, electromagnetic fields |
| **Multi-Panel Comparison** | `Scene`, `VGroup`, `NumberPlane` | Grouping sub-axes side-by-side: `axes1.to_edge(LEFT)`, `axes2.to_edge(RIGHT)` | Time domain vs Frequency domain, State variable $x(t)$ vs Phase space $(x, \dot{x})$ |
| **HUD / Screen Fixed Overlays** | `ThreeDScene`, `VoiceoverScene` | `self.add_fixed_in_frame_mobjects(title, equations)` | Keeping LaTeX equations and theorem cards static in screen space while 3D camera orbits |

---

## Axis 3: Dynamic Motion & Animation Idioms

1. **Continuous Array Traversal (`ValueTracker` + Updater)**
   - **Pattern**: `tracker = ValueTracker(0)`, with `mob.set_points_as_corners([axes.c2p(*p) for p in points[:int(tracker.get_value()) + 1]])`.
   - **Use Case**: Smoothly growing differential equation curves and animated particle trails.

2. **Phase Space Vector Field Streaming**
   - **Pattern**: `stream_lines = StreamLines(vector_field_func, stroke_width=2, max_anchors_per_line=30)` accompanied by `stream_lines.start_animation(warm_up=False, flow_speed=1.5)`.
   - **Use Case**: Visualizing steady-state flows and unstable saddle points.

3. **Symbolic LaTeX Transformation (`TransformMatchingShapes` / `TransformMatchingTex`)**
   - **Pattern**: Showing the analytical differential equation step, then transforming into the discretized update step.
   - **Use Case**: Mathematical proofs, algorithm derivation before code execution.

4. **Dynamic Dot & Value Readout**
   - **Pattern**: `DecimalNumber.add_updater(lambda d: d.set_value(tracker.get_value()))`.
   - **Use Case**: Real-time energy meters, loss value readouts, time indicators.

---

## Axis 4: Narration & Pedagogical Voiceover Pacing

1. **Single-Thought Synchronized Hook**
   - **Structure**: One unified voiceover block where the primary visual matches speech duration (`run_time=tracker.duration`).
   - **Target**: Quick theorem demonstrations, single dynamic trajectory sweeps.

2. **Two-Stage "Theory then Simulation" Architecture**
   - **Stage 1 (Analytical)**: Introduce LaTeX differential equations, boundary conditions, or cost functions in 2D with dedicated voiceover.
   - **Stage 2 (Numerical Execution)**: Camera transitions (or 2D equations fade), 3D axes or phase portrait initializes, and numerical trajectory draws in sync with explanation.

3. **Three-Stage "Setup, Simulation, Interpretation" Proof**
   - **Stage 1**: Problem formulation and physical intuition.
   - **Stage 2**: Numerical computation results drawn over time.
   - **Stage 3**: Zooming in or highlighting fixed points / limit cycles, explaining the scientific consequence.
