"""Curated Mathematical & Computational Capabilities ontology for AOS LKG."""

from __future__ import annotations

from typing import List
from aos_lkg.schema.nodes import CapabilityNode, ConceptNode, AlgorithmNode


CAPABILITY_DEFINITIONS: List[CapabilityNode] = [
    # --- ROOT FINDING & EQUATION SOLVING ---
    CapabilityNode(
        id="cap:root_finding_bracketed",
        name="Bracketed Root Finding (Brent / Bisection)",
        domain="root_finding",
        description="Finds scalar roots of continuous 1D function f(x) = 0 within a guaranteed sign-change bracket [a, b].",
        input_types=["Callable[[float], float]", "float", "float"],
        output_types=["float", "RootResults"],
        canonical_apis=["scipy.optimize.brentq", "scipy.optimize.bisect", "scipy.optimize.brenth", "scipy.optimize.root_scalar"],
        concepts=["concept:zero_crossing", "concept:intermediate_value_theorem", "concept:continuity"],
        manim_targets=["manim:NumberLine", "manim:Axes", "manim:Dot", "manim:Line", "manim:MathTex"],
        tags=["root_finding", "zeros", "bracketing", "1d", "scalar"],
    ),
    CapabilityNode(
        id="cap:root_finding_newton",
        name="Derivative-Based Root Finding (Newton-Raphson / Halley / Secant)",
        domain="root_finding",
        description="Iterative tangent/secant root finding from an initial guess x0 using function and derivative evaluations.",
        input_types=["Callable[[float], float]", "float", "Optional[Callable[[float], float]]"],
        output_types=["float"],
        canonical_apis=["scipy.optimize.newton", "scipy.optimize.root_scalar"],
        concepts=["concept:newton_raphson", "concept:tangent_line", "concept:quadratic_convergence", "concept:derivatives"],
        manim_targets=["manim:Axes", "manim:Dot", "manim:Line", "manim:ValueTracker", "manim:MathTex"],
        tags=["root_finding", "newton", "tangent", "iterative", "convergence"],
    ),
    CapabilityNode(
        id="cap:symbolic_equation_solving",
        name="Exact & Symbolic Equation Solving",
        domain="symbolic_algebra",
        description="Finds closed-form exact or high-precision numerical roots of algebraic and transcendental equations.",
        input_types=["sympy.Expr", "sympy.Symbol"],
        output_types=["List[sympy.Expr]", "sympy.Float"],
        canonical_apis=["sympy.solvers.solve", "sympy.solvers.solveset", "sympy.nsolve"],
        concepts=["concept:algebraic_equations", "concept:exact_closed_form", "concept:polynomial_roots"],
        manim_targets=["manim:MathTex", "manim:Axes", "manim:Dot"],
        tags=["symbolic", "exact", "sympy", "algebra"],
    ),

    # --- CALCULUS & INTEGRATION ---
    CapabilityNode(
        id="cap:numerical_integration",
        name="Adaptive Numerical Quadrature (1D & Multi-D Integration)",
        domain="calculus",
        description="Computes definite integrals of functions over finite or infinite intervals using adaptive Gauss-Kronrod quadrature.",
        input_types=["Callable[[float], float]", "float", "float"],
        output_types=["Tuple[float, float]"],
        canonical_apis=["scipy.integrate.quad", "scipy.integrate.dblquad", "scipy.integrate.trapezoid", "scipy.integrate.cumulative_trapezoid"],
        concepts=["concept:definite_integral", "concept:riemann_sum", "concept:area_under_curve", "concept:fundamental_theorem_of_calculus"],
        manim_targets=["manim:Axes", "manim:Polygon", "manim:MathTex", "manim:ValueTracker"],
        tags=["calculus", "integration", "area", "quadrature", "riemann"],
    ),
    CapabilityNode(
        id="cap:symbolic_calculus",
        name="Symbolic Differentiation & Integration",
        domain="symbolic_algebra",
        description="Computes exact symbolic derivatives, anti-derivatives, series expansions (Taylor, Laurent), and limits.",
        input_types=["sympy.Expr", "sympy.Symbol"],
        output_types=["sympy.Expr"],
        canonical_apis=["sympy.diff", "sympy.integrate", "sympy.series", "sympy.limit"],
        concepts=["concept:derivative", "concept:anti_derivative", "concept:taylor_series", "concept:limits"],
        manim_targets=["manim:MathTex", "manim:Axes", "manim:ParametricFunction"],
        tags=["symbolic", "derivative", "taylor", "integral"],
    ),

    # --- DIFFERENTIAL EQUATIONS ---
    CapabilityNode(
        id="cap:ode_integration",
        name="Initial Value Problem ODE Integration (Runge-Kutta, BDF, Radau)",
        domain="differential_equations",
        dimension="3D",
        description="Integrates systems of first-order ordinary differential equations dy/dt = f(t, y) with initial conditions y(t0)=y0 (e.g. Lorenz attractor, double pendulum, chaotic orbits, projectile physics).",
        input_types=["Callable[[float, np.ndarray], np.ndarray]", "Tuple[float, float]", "np.ndarray"],
        output_types=["OdeResult"],
        canonical_apis=["scipy.integrate.solve_ivp", "scipy.integrate.odeint"],
        concepts=["concept:vector_field", "concept:phase_portrait", "concept:trajectory", "concept:dynamical_system", "concept:chaotic_attractor"],
        manim_targets=["manim:ThreeDAxes", "manim:Axes", "manim:ParametricFunction", "manim:Dot", "manim:Arrow"],
        tags=["ode", "differential_equations", "trajectory", "phase_space", "lorenz", "attractor", "chaos", "chaotic_attractor", "runge_kutta", "dynamical_system", "rossler", "pendulum"],
    ),

    # --- INTERPOLATION & SPLINES ---
    CapabilityNode(
        id="cap:spline_interpolation",
        name="Cubic & B-Spline Curve Interpolation",
        domain="interpolation",
        description="Fits smooth piecewise cubic polynomials or B-splines through discrete control points with C1/C2 continuity.",
        input_types=["np.ndarray", "np.ndarray"],
        output_types=["scipy.interpolate.CubicSpline", "scipy.interpolate.BSpline"],
        canonical_apis=["scipy.interpolate.CubicSpline", "scipy.interpolate.make_interp_spline", "scipy.interpolate.splrep", "scipy.interpolate.splev"],
        concepts=["concept:spline_continuity", "concept:smooth_curve", "concept:control_points"],
        manim_targets=["manim:Axes", "manim:ParametricFunction", "manim:Dot", "manim:VGroup"],
        tags=["interpolation", "splines", "smooth_curve", "cubic_spline", "control_points"],
    ),

    # --- LINEAR ALGEBRA ---
    CapabilityNode(
        id="cap:eigen_decomposition",
        name="Eigenvalue & Eigenvector Decomposition",
        domain="linear_algebra",
        description="Computes eigenvalues and eigenvectors of square matrices A v = lambda v, representing invariant directions and scale factors.",
        input_types=["np.ndarray"],
        output_types=["Tuple[np.ndarray, np.ndarray]"],
        canonical_apis=["scipy.linalg.eig", "numpy.linalg.eig", "scipy.linalg.eigh"],
        concepts=["concept:eigenvalue", "concept:eigenvector", "concept:linear_transformation", "concept:matrix_diagonalization"],
        manim_targets=["manim:Axes", "manim:ThreeDAxes", "manim:Arrow", "manim:Matrix", "manim:MathTex"],
        tags=["linear_algebra", "eigenvalues", "eigenvectors", "matrix_transformation"],
    ),
    CapabilityNode(
        id="cap:matrix_transformation",
        name="Linear Transformations & SVD / Matrix Inversion",
        domain="linear_algebra",
        description="Solves linear systems Ax = b, computes Singular Value Decomposition (SVD), matrix inverse, and rotation/projection operators.",
        input_types=["np.ndarray", "Optional[np.ndarray]"],
        output_types=["np.ndarray"],
        canonical_apis=["scipy.linalg.solve", "scipy.linalg.svd", "scipy.linalg.inv", "numpy.linalg.det"],
        concepts=["concept:linear_system", "concept:matrix_inversion", "concept:singular_values", "concept:basis_transformation"],
        manim_targets=["manim:Axes", "manim:Matrix", "manim:Arrow", "manim:Polygon"],
        tags=["linear_algebra", "svd", "matrix", "basis_transform"],
    ),

    # --- GRAPH THEORY ---
    CapabilityNode(
        id="cap:graph_shortest_path",
        name="Graph Shortest Path & Dijkstra / A* Search",
        domain="graph_theory",
        description="Finds the shortest weighted or unweighted path and shortest distances between nodes in a graph.",
        input_types=["networkx.Graph", "Any", "Any"],
        output_types=["List[Any]", "float"],
        canonical_apis=["networkx.shortest_path", "networkx.dijkstra_path", "networkx.astar_path", "networkx.shortest_path_length"],
        concepts=["concept:shortest_path", "concept:dijkstra_algorithm", "concept:graph_distance", "concept:priority_queue"],
        manim_targets=["manim:Graph", "manim:Dot", "manim:Line", "manim:Arrow", "manim:MathTex"],
        tags=["graph_theory", "dijkstra", "shortest_path", "network", "pathfinding"],
    ),
    CapabilityNode(
        id="cap:graph_traversal",
        name="Graph Traversal (BFS / DFS / Spanning Trees)",
        domain="graph_theory",
        description="Traverses graph topologies in breadth-first or depth-first order, and generates Minimum Spanning Trees (Kruskal/Prim).",
        input_types=["networkx.Graph", "Any"],
        output_types=["Iterator[Tuple[Any, Any]]", "networkx.Graph"],
        canonical_apis=["networkx.bfs_edges", "networkx.dfs_edges", "networkx.minimum_spanning_tree", "networkx.spring_layout"],
        concepts=["concept:breadth_first_search", "concept:depth_first_search", "concept:minimum_spanning_tree", "concept:graph_layout"],
        manim_targets=["manim:Graph", "manim:Dot", "manim:Line", "manim:VGroup"],
        tags=["graph_theory", "bfs", "dfs", "mst", "traversal"],
    ),

    # --- COMPUTATIONAL GEOMETRY ---
    CapabilityNode(
        id="cap:polygon_geometry_intersection",
        name="2D Polygon & Curve Intersection / Boolean Ops",
        domain="computational_geometry",
        description="Computes geometric intersections, unions, differences, convex hulls, and bounding boxes of 2D shapes.",
        input_types=["shapely.Geometry", "shapely.Geometry"],
        output_types=["shapely.Geometry"],
        canonical_apis=["shapely.intersection", "shapely.union", "shapely.difference", "shapely.convex_hull", "shapely.Polygon"],
        concepts=["concept:geometric_intersection", "concept:boolean_operations", "concept:convex_hull", "concept:polygon_clipping"],
        manim_targets=["manim:Polygon", "manim:Dot", "manim:Axes", "manim:VGroup"],
        tags=["geometry", "polygon", "intersection", "shapely", "convex_hull"],
    ),
    CapabilityNode(
        id="cap:spatial_convex_hull_voronoi",
        name="Convex Hull, Voronoi Diagrams & Delaunay Triangulation",
        domain="computational_geometry",
        description="Computes spatial structures including convex hulls, Voronoi tessellations, and Delaunay triangulations for point sets.",
        input_types=["np.ndarray"],
        output_types=["scipy.spatial.ConvexHull", "scipy.spatial.Voronoi", "scipy.spatial.Delaunay"],
        canonical_apis=["scipy.spatial.ConvexHull", "scipy.spatial.Voronoi", "scipy.spatial.Delaunay", "scipy.spatial.distance_matrix"],
        concepts=["concept:convex_hull", "concept:voronoi_diagram", "concept:delaunay_triangulation", "concept:point_cloud"],
        manim_targets=["manim:Polygon", "manim:Dot", "manim:Line", "manim:VGroup"],
        tags=["geometry", "spatial", "convex_hull", "voronoi", "delaunay"],
    ),

    # --- SIGNAL & FOURIER ANALYSIS ---
    CapabilityNode(
        id="cap:fourier_transform",
        name="Discrete & Fast Fourier Transform (FFT / IFFT)",
        domain="signal_processing",
        description="Computes 1D/2D frequency spectrum decompositions, frequency filtering, and inverse transforms.",
        input_types=["np.ndarray"],
        output_types=["np.ndarray"],
        canonical_apis=["scipy.fft.fft", "scipy.fft.ifft", "scipy.fft.fftfreq", "numpy.fft.fft"],
        concepts=["concept:fourier_series", "concept:frequency_spectrum", "concept:harmonic_decomposition", "concept:phase"],
        manim_targets=["manim:Axes", "manim:ParametricFunction", "manim:Arrow", "manim:Circle", "manim:MathTex"],
        tags=["fourier", "fft", "frequency", "harmonics", "signal", "epicycles"],
    ),

    # --- SPECIAL FUNCTIONS ---
    CapabilityNode(
        id="cap:special_functions",
        name="Special Mathematical Functions (Gamma, Bessel, Legendre, Error)",
        domain="special_functions",
        description="Evaluates transcendental and special functions of mathematical physics and statistics with full machine precision.",
        input_types=["Union[float, np.ndarray]"],
        output_types=["Union[float, np.ndarray]"],
        canonical_apis=["scipy.special.gamma", "scipy.special.jv", "scipy.special.legendre", "scipy.special.erf"],
        concepts=["concept:gamma_function", "concept:bessel_function", "concept:orthogonal_polynomials"],
        manim_targets=["manim:Axes", "manim:ParametricFunction", "manim:MathTex"],
        tags=["special_functions", "gamma", "bessel", "legendre", "physics"],
    ),
]


CONCEPT_DEFINITIONS: List[ConceptNode] = [
    ConceptNode(
        id="concept:zero_crossing",
        name="Zero Crossing / Scalar Root",
        domain="calculus",
        description="A point x* where a real-valued function f(x) satisfies f(x*) = 0, corresponding to an x-axis intercept.",
        formal_definition="f(x^*) = 0, \\quad x^* \\in [a, b]",
        related_concepts=["concept:intermediate_value_theorem", "concept:continuity"],
    ),
    ConceptNode(
        id="concept:newton_raphson",
        name="Newton-Raphson Iteration",
        domain="numerical_analysis",
        description="An iterative root-finding algorithm that approximates roots via successive tangent line x-intercepts.",
        formal_definition="x_{n+1} = x_n - \\frac{f(x_n)}{f'(x_n)}",
        related_concepts=["concept:tangent_line", "concept:quadratic_convergence"],
    ),
    ConceptNode(
        id="concept:definite_integral",
        name="Definite Integral & Riemann Sum",
        domain="calculus",
        description="The signed area under a curve f(x) over [a, b], formalized as the limit of Riemann sums as partition width approaches zero.",
        formal_definition="\\int_a^b f(x)\\,dx = \\lim_{\\Delta x \\to 0} \\sum_{i=1}^n f(x_i^*)\\,\\Delta x_i",
        related_concepts=["concept:area_under_curve", "concept:riemann_sum"],
    ),
    ConceptNode(
        id="concept:shortest_path",
        name="Shortest Path in Weighted Graphs",
        domain="graph_theory",
        description="A path between two vertices in a graph such that the sum of the weights of its constituent edges is minimized.",
        formal_definition="d(u, v) = \\min_{P} \\sum_{e \\in P} w(e)",
        related_concepts=["concept:dijkstra_algorithm", "concept:graph_distance"],
    ),
    ConceptNode(
        id="concept:geometric_intersection",
        name="Geometric Intersection",
        domain="geometry",
        description="The spatial set of points shared simultaneously by two or more geometric curves, polygons, or surfaces.",
        formal_definition="A \\cap B = \\{ p \\mid p \\in A \\land p \\in B \\}",
        related_concepts=["concept:boolean_operations", "concept:polygon_clipping"],
    ),
    ConceptNode(
        id="concept:fourier_series",
        name="Fourier Series / Harmonic Decomposition",
        domain="signal_processing",
        description="Representation of a function as a superposition of sinusoidal harmonics with distinct amplitudes and phases.",
        formal_definition="f(t) = \\sum_{n=-\\infty}^{\\infty} c_n e^{i 2\\pi n f_0 t}",
        related_concepts=["concept:frequency_spectrum", "concept:epicycles"],
    ),
    ConceptNode(
        id="concept:chaotic_attractor",
        name="Chaotic Strange Attractor & Phase Portrait",
        domain="differential_equations",
        description="A set of numerical states in phase space toward which a nonlinear dynamical system evolves deterministically with sensitive dependence on initial conditions (e.g. Lorenz butterfly attractor).",
        formal_definition="\\dot{x}=\\sigma(y-x),\\quad \\dot{y}=x(\\rho-z)-y,\\quad \\dot{z}=xy-\\beta z",
        related_concepts=["concept:vector_field", "concept:trajectory", "concept:dynamical_system"],
    ),
]


ALGORITHM_DEFINITIONS: List[AlgorithmNode] = [
    AlgorithmNode(
        id="algo:brent_dekker",
        name="Brent-Dekker Method",
        domain="root_finding",
        complexity="O(log(1/eps))",
        convergence="Superlinear (approx 1.839)",
        assumptions=["f(a) * f(b) < 0", "f is continuous on [a, b]"],
        description="Combines root bracketing, bisection, and inverse quadratic interpolation for guaranteed robust convergence.",
    ),
    AlgorithmNode(
        id="algo:newton_raphson",
        name="Newton-Raphson Method",
        domain="root_finding",
        complexity="O(log(1/eps))",
        convergence="Quadratic (order 2)",
        assumptions=["f'(x*) != 0", "Initial guess x0 sufficiently close to root"],
        description="Successive approximation using first-order Taylor expansion and tangent lines.",
    ),
    AlgorithmNode(
        id="algo:dijkstra",
        name="Dijkstra's Algorithm",
        domain="graph_theory",
        complexity="O((|V| + |E|) log |V|)",
        assumptions=["Non-negative edge weights"],
        description="Greedy priority-queue exploration of the lowest cumulative distance frontier.",
    ),
    AlgorithmNode(
        id="algo:rk45_dormand_prince",
        name="Dormand-Prince Runge-Kutta (RK45)",
        domain="differential_equations",
        complexity="Adaptive O(N)",
        assumptions=["Continuous vector field f(t, y)"],
        description="Explicit Runge-Kutta pair of order 4 and 5 with adaptive step size control.",
    ),
    AlgorithmNode(
        id="algo:quickhull",
        name="Quickhull Algorithm",
        domain="computational_geometry",
        complexity="O(N log N) average, O(N^2) worst case",
        assumptions=["Planar or 3D point cloud"],
        description="Divide-and-conquer geometric hull construction analogous to Quicksort.",
    ),
]
