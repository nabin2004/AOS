# AOS Mathematical Animation Benchmark (MAB-19) Specification

This document provides the formal benchmark specification for the **AOS Mathematical Animation Benchmark (MAB-19)** used to quantitatively evaluate retrieval accuracy, domain gating, and coordinate synthesis for code generation.

---

## 1. Evaluation Dimensions & Mathematical Tasks

The benchmark evaluates 19 canonical queries distributed across 8 fundamental computational mathematics disciplines:

| Test ID | Mathematical Category | Query Prompt | Expected Capability | Target API | Dim | Expected Manim Mobjects |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| `bm_ode_lorenz` | Dynamical Systems / Chaos | "Animate Lorenz attractor" | `cap:ode_integration` | `scipy.integrate.solve_ivp` | 3D | `ThreeDAxes`, `ThreeDScene` |
| `bm_ode_rossler` | Dynamical Systems / Chaos | "Simulate and plot Rossler attractor phase space in 3D" | `cap:ode_integration` | `scipy.integrate.solve_ivp` | 3D | `ThreeDAxes`, `ThreeDScene` |
| `bm_ode_pendulum` | Dynamical Systems | "Animate double pendulum phase portrait using Runge-Kutta ODE integration" | `cap:ode_integration` | `scipy.integrate.solve_ivp` | 2D | `Axes` |
| `bm_root_newton_sqrt` | Root Finding | "Animate Newton's method for finding sqrt(2)" | `cap:root_finding_newton` | `scipy.optimize.newton` | 2D | `Axes`, `Dot` |
| `bm_root_brent_zero` | Root Finding | "Find continuous zero crossing bracket on [1, 3] with Brent-Dekker method" | `cap:root_finding_bracketed` | `scipy.optimize.brentq` | 2D | `Axes`, `Dot`, `NumberLine` |
| `bm_root_symbolic_poly` | Symbolic Algebra | "Solve exact polynomial roots symbolically using SymPy" | `cap:symbolic_equation_solving` | `sympy.solvers.solve` | 2D | `MathTex` |
| `bm_calc_riemann_sum` | Calculus & Quadrature | "Animate Riemann sum rectangles converging to definite integral area" | `cap:numerical_integration` | `scipy.integrate.quad` | 2D | `Axes`, `Polygon` |
| `bm_calc_symbolic_diff` | Symbolic Calculus | "Compute symbolic derivative and Taylor series expansion" | `cap:symbolic_calculus` | `sympy.diff` | 2D | `MathTex`, `Axes` |
| `bm_graph_dijkstra` | Graph Theory | "Visualize shortest path using Dijkstra algorithm on a weighted graph" | `cap:graph_shortest_path` | `networkx.dijkstra_path` | 2D | `Graph` |
| `bm_graph_bfs_traversal` | Graph Theory | "Animate breadth-first search BFS traversal tree on a network" | `cap:graph_traversal` | `networkx.bfs_tree` | 2D | `Graph` |
| `bm_graph_mst` | Graph Theory | "Compute and animate Minimum Spanning Tree MST on a graph" | `cap:graph_traversal` | `networkx.minimum_spanning_tree` | 2D | `Graph` |
| `bm_geom_polygon_intersect` | Computational Geometry | "Find intersection of two geometric circles and fill overlapping polygon area" | `cap:polygon_geometry_intersection` | `shapely.intersection` | 2D | `Polygon`, `Axes` |
| `bm_geom_convex_hull` | Computational Geometry | "Compute and animate 2D Convex Hull for random point cloud" | `cap:spatial_convex_hull_voronoi` | `scipy.spatial.ConvexHull` | 2D | `Polygon`, `Dot` |
| `bm_geom_voronoi` | Computational Geometry | "Visualize Voronoi diagram tessellation of seed points" | `cap:spatial_convex_hull_voronoi` | `shapely.voronoi_polygons` | 2D | `Polygon`, `Dot` |
| `bm_linalg_eigenvectors` | Linear Algebra | "Visualize 2D linear transformation and invariant eigenvectors" | `cap:eigen_decomposition` | `scipy.linalg.eig` | 2D | `Axes`, `Arrow` |
| `bm_linalg_svd` | Linear Algebra | "Compute Singular Value Decomposition SVD matrix deformation" | `cap:matrix_transformation` | `scipy.linalg.svd` | 2D | `Axes`, `Arrow` |
| `bm_interp_cubic_spline` | Interpolation | "Fit and animate smooth cubic spline interpolation through control points" | `cap:spline_interpolation` | `scipy.interpolate.CubicSpline` | 2D | `Axes`, `Dot`, `ParametricFunction` |
| `bm_signal_fft` | Signal Processing | "Compute FFT frequency spectrum decomposition of audio signal" | `cap:fourier_transform` | `scipy.fft.fft` | 2D | `Axes`, `ParametricFunction` |
| `bm_signal_fourier_series` | Signal Processing | "Animate Fourier series epicycles reconstructing a square wave" | `cap:fourier_transform` | `scipy.signal.square` / `fft` | 2D | `Axes`, `Circle`, `Arrow` |

---

## 2. Quantitative Evaluation Metrics

Given $N$ evaluation test cases, the benchmark computes four orthogonal metrics and an aggregate score:

### 1. Top-1 Capability Accuracy ($\text{Acc}_{\text{cap}}$)
$$\text{Acc}_{\text{cap}} = \frac{1}{N} \sum_{i=1}^N \mathbb{I}\left(c_i^* = \hat{c}_i \lor \text{domain}(c_i^*) = \text{domain}(\hat{c}_i)\right) \times 100\%$$

### 2. Top-1 Primary API Accuracy ($\text{Acc}_{\text{api}}$)
$$\text{Acc}_{\text{api}} = \frac{1}{N} \sum_{i=1}^N \mathbb{I}\left(\hat{f}_i \in \text{TargetAPIs}_i\right) \times 100\%$$

### 3. Dimensionality Consistency ($\text{Acc}_{\text{dim}}$)
$$\text{Acc}_{\text{dim}} = \frac{1}{N} \sum_{i=1}^N \mathbb{I}\left(\dim_i^* = \widehat{\dim}_i\right) \times 100\%$$

### 4. Manim Mapping Accuracy ($\text{Acc}_{\text{manim}}$)
$$\text{Acc}_{\text{manim}} = \frac{1}{N} \sum_{i=1}^N \mathbb{I}\left(\exists m \in \widehat{\mathcal{M}}_i \text{ s.t. } m \in \mathcal{M}_i^*\right) \times 100\%$$

### Composite Benchmark Score ($\mathcal{S}_{\text{overall}}$)
$$\mathcal{S}_{\text{overall}} = 0.35 \cdot \text{Acc}_{\text{cap}} + 0.35 \cdot \text{Acc}_{\text{api}} + 0.15 \cdot \text{Acc}_{\text{dim}} + 0.15 \cdot \text{Acc}_{\text{manim}}$$

---

## 3. Running the Benchmark

Execute the automated benchmark directly via the CLI:

```bash
uv run aos-lkg benchmark
```

To run against a custom YAML configuration or custom dataset:
```bash
uv run aos-lkg benchmark --config lkg_config.yaml --data-dir data/
```
