"""Manim Mappings, Animation Patterns, Precision Rules, and Executable Code Templates."""

from __future__ import annotations

from typing import List

# pyrefly: ignore [missing-import]
from aos_lkg.schema.nodes import (
    ManimMappingNode,
    AnimationPatternNode,
    PrecisionRuleNode,
    CodeExampleNode,
)


MANIM_MAPPING_DEFINITIONS: List[ManimMappingNode] = [
    ManimMappingNode(
        id="manim:Axes",
        name="Manim 2D Axes Coordinate System",
        mobject_classes=["Axes", "NumberPlane"],
        coordinate_adapter="axes.c2p(x, y)",
        visual_role="Primary 2D Cartesian coordinate framework for plotting mathematical functions, curves, and tangent lines.",
        construction_pattern=(
            "axes = Axes(x_range=[x_min, x_max, x_step], y_range=[y_min, y_max, y_step], "
            "axis_config={'include_numbers': True, 'include_tip': True})"
        ),
        update_mechanism="Static backdrop or dynamic axes with ValueTracker scaling",
        best_practices=[
            "Always wrap math coordinates in axes.c2p(x, y) to obtain Manim scene coordinates.",
            "Use axes.get_graph(func, color=...) for continuous function curves.",
            "Use axes.get_tangent_line(x, graph) or custom secant calculation.",
            "Use axes.get_area(graph, x_range=[a, b], color=...) for definite integrals.",
        ],
        gotchas=[
            "Never manually guess [x, y, 0] screen coordinates for function values; always use axes.c2p().",
            "Ensure the function domain matches x_range to avoid out-of-frame clipping.",
        ],
    ),
    ManimMappingNode(
        id="manim:NumberLine",
        name="Manim 1D Number Line Coordinate System",
        mobject_classes=["NumberLine"],
        coordinate_adapter="number_line.n2p(x)",
        visual_role="1D scalar coordinate axis for 1D root intervals, number representations, and scalar bisections.",
        construction_pattern="nl = NumberLine(x_range=[x_min, x_max, step], include_numbers=True)",
        update_mechanism="n2p(tracker.get_value())",
        best_practices=[
            "Use number_line.n2p(val) to place Dot or ticks on the 1D axis.",
        ],
        gotchas=[
            "Do not confuse number line coordinates with scene units.",
        ],
    ),
    ManimMappingNode(
        id="manim:Dot",
        name="Manim Dot / Point Marker",
        mobject_classes=["Dot", "LabeledDot"],
        coordinate_adapter="Dot(point=axes.c2p(x, y), color=...)",
        visual_role="Marks exact numerical coordinates (roots, intersections, vertices, initial guesses).",
        construction_pattern="dot = Dot(axes.c2p(x_val, y_val), color=YELLOW, radius=0.08)",
        update_mechanism="dot.add_updater(lambda d: d.move_to(axes.c2p(tracker.get_value(), f(tracker.get_value()))))",
        best_practices=[
            "Pair with always_redraw or updater when tracking dynamic variables.",
            "Add a label using MathTex and next_to(dot, direction, buff=0.1).",
        ],
        gotchas=[
            "Updaters must not allocate heavy new Mobjects on every frame; update existing position in-place or use always_redraw carefully.",
        ],
    ),
    ManimMappingNode(
        id="manim:Graph",
        name="Manim Discrete Network Graph",
        mobject_classes=["Graph"],
        coordinate_adapter="graph[node_id].get_center()",
        visual_role="Displays discrete nodes and weighted/unweighted edges for graph theory algorithms (Dijkstra, BFS, MST).",
        construction_pattern=(
            "graph = Graph(vertices, edges, layout=layout_dict, vertex_config={'radius': 0.25}, "
            "edge_config={'stroke_width': 2})"
        ),
        update_mechanism="Animate vertex color changes and edge highlighting in succession",
        best_practices=[
            "Precompute node coordinates using networkx.spring_layout or circular_layout and pass as layout=pos_dict.",
            "Highlight visited edges using graph.edges[(u, v)].animate.set_color(YELLOW).",
        ],
        gotchas=[
            "Ensure edge tuples match the directionality/order defined in the Graph initialization.",
        ],
    ),
    ManimMappingNode(
        id="manim:Polygon",
        name="Manim Geometric Polygon & Shaded Regions",
        dimension="2D",
        mobject_classes=["Polygon", "Polygram"],
        coordinate_adapter="Polygon(*[axes.c2p(x, y) for x, y in vertices])",
        visual_role="Visualizes geometric hulls, intersecting regions, and Voronoi cells.",
        construction_pattern="poly = Polygon(*[axes.c2p(x, y) for x, y in pts], color=BLUE, fill_opacity=0.3)",
        update_mechanism="Transform(old_poly, new_poly)",
        best_practices=[
            "Feed vertices directly from Shapely polygon exterior coordinates or SciPy ConvexHull vertices.",
        ],
        gotchas=[
            "Ensure vertex ordering is convex/counter-clockwise to prevent self-intersecting polygon rendering glitches.",
        ],
    ),
    ManimMappingNode(
        id="manim:ThreeDAxes",
        name="Manim 3D Axes Coordinate Framework",
        dimension="3D",
        mobject_classes=["ThreeDAxes", "ThreeDScene"],
        coordinate_adapter="axes.c2p(x, y, z)",
        visual_role="3D Cartesian coordinate framework for chaotic dynamical systems, Lorenz attractors, ODE phase space trajectories, and surfaces.",
        construction_pattern=(
            "axes = ThreeDAxes(x_range=[x_min, x_max, x_step], y_range=[y_min, y_max, y_step], z_range=[z_min, z_max, z_step])\n"
            "self.set_camera_orientation(phi=65 * DEGREES, theta=-45 * DEGREES)"
        ),
        update_mechanism="Move camera with self.begin_ambient_camera_rotation(rate=0.2) and trace trajectory via VMobject or TracedPath",
        best_practices=[
            "Inherit from ThreeDScene rather than Scene for 3D camera controls.",
            "Always wrap 3D state coordinates in axes.c2p(x, y, z).",
            "Use VMobject().set_points_smoothly([axes.c2p(*p) for p in points]) for smooth ODE trajectory curves.",
            "Add ambient camera rotation (self.begin_ambient_camera_rotation(rate=0.15)) to convey 3D depth.",
        ],
        gotchas=[
            "Do not use 2D Axes or 2D [x, y, 0] coordinates for 3D state variables (x, y, z).",
            "Set appropriate camera phi/theta to prevent trajectories from rendering flat.",
        ],
    ),
    ManimMappingNode(
        id="manim:Line",
        name="Manim 2D/3D Geometric Line & Tangents",
        dimension="2D",
        mobject_classes=["Line", "DashedLine"],
        coordinate_adapter="Line(axes.c2p(x1, y1), axes.c2p(x2, y2))",
        visual_role="Connects coordinates, draws tangent and secant lines, projection dashed lines, and graph edges.",
        construction_pattern="line = Line(axes.c2p(x1, y1), axes.c2p(x2, y2), color=YELLOW, stroke_width=3)",
        update_mechanism="Transform(old_line, new_line) or always_redraw(lambda: Line(axes.c2p(...), axes.c2p(...)))",
        best_practices=[
            "Always map endpoint coordinates with axes.c2p(x, y) or number_line.n2p(x).",
            "Use DashedLine for vertical projections and reference coordinates.",
        ],
        gotchas=[
            "Do not pass raw math coordinates without axes.c2p() conversion.",
        ],
    ),
    ManimMappingNode(
        id="manim:Arrow",
        name="Manim Vector Arrow & Direction Indicator",
        dimension="2D",
        mobject_classes=["Arrow", "Vector", "DoubleArrow"],
        coordinate_adapter="Arrow(axes.c2p(x1, y1), axes.c2p(x2, y2), buff=0)",
        visual_role="Visualizes vector fields, directional derivatives, eigenvectors, gradient descent steps, and phase trajectories.",
        construction_pattern="arrow = Arrow(axes.c2p(0, 0), axes.c2p(vx, vy), color=MAROON, buff=0)",
        update_mechanism="arrow.put_start_and_end_on(axes.c2p(x1, y1), axes.c2p(x2, y2))",
        best_practices=[
            "Set buff=0 when anchoring arrow tips exactly to mathematical coordinates.",
            "Use Vector([x, y]) when drawing vectors from origin.",
        ],
        gotchas=[
            "Default buff > 0 creates gaps between coordinate points and arrow endpoints.",
        ],
    ),
    ManimMappingNode(
        id="manim:MathTex",
        name="Manim LaTeX Mathematical Formula & Equations",
        dimension="2D",
        mobject_classes=["MathTex", "Tex"],
        coordinate_adapter="MathTex(r'...').next_to(target_mobject, direction)",
        visual_role="Renders exact mathematical notation, formulas, dynamic numerical values, step derivations, and variable labels.",
        construction_pattern="tex = MathTex(r'\\int_a^b f(x)\\,dx = F(b) - F(a)', font_size=36)",
        update_mechanism="TransformMatchingTex(old_tex, new_tex) or dynamic decimal updater",
        best_practices=[
            "Use raw Python strings r'...' for all LaTeX strings.",
            "Position formulas relative to coordinates using .next_to(axes.c2p(x, y), UP) or to_corner(UL).",
            "Use TransformMatchingTex for smooth formula derivations.",
        ],
        gotchas=[
            "Escape backslashes properly with raw strings r'...'.",
            "Avoid re-instantiating MathTex inside high-frequency updaters.",
        ],
    ),
    ManimMappingNode(
        id="manim:Text",
        name="Manim Text Label & Annotation",
        dimension="2D",
        mobject_classes=["Text", "MarkupText"],
        coordinate_adapter="Text('...').next_to(target, direction)",
        visual_role="Displays plain text titles, explanations, step indicators, and algorithm summaries.",
        construction_pattern="title = Text('Newton-Raphson Method', font_size=40).to_edge(UP)",
        update_mechanism="Write(text) / FadeIn(text) / Transform(old_text, new_text)",
        best_practices=[
            "Use Text for non-formula words and MathTex for mathematical symbols.",
            "Anchor to screen edges with .to_edge(UP) or .to_corner(UL).",
        ],
        gotchas=[
            "Do not put LaTeX math markup inside plain Text; use MathTex instead.",
        ],
    ),
    ManimMappingNode(
        id="manim:ParametricFunction",
        name="Manim Continuous Parametric Function Curve",
        dimension="2D",
        mobject_classes=["ParametricFunction", "FunctionGraph"],
        coordinate_adapter="ParametricFunction(lambda t: axes.c2p(fx(t), fy(t)), t_range=[t_min, t_max, t_step])",
        visual_role="Visualizes continuous parametric curves, Fourier epicycles, splines, special functions, and 2D ODE phase paths.",
        construction_pattern=(
            "curve = ParametricFunction(lambda t: axes.c2p(np.cos(t), np.sin(t)), "
            "t_range=[0, TAU, 0.02], color=YELLOW)"
        ),
        update_mechanism="Create(curve) / Transform(old_curve, new_curve)",
        best_practices=[
            "Always wrap lambda return values in axes.c2p().",
            "Use NumPy-vectorized mathematical functions.",
        ],
        gotchas=[
            "Ensure t_step is sufficiently dense to avoid jagged polygon rendering.",
        ],
    ),
    ManimMappingNode(
        id="manim:Matrix",
        name="Manim Matrix & Linear Transformation Display",
        dimension="2D",
        mobject_classes=["Matrix", "DecimalMatrix", "IntegerMatrix"],
        coordinate_adapter="Matrix(np_array).to_corner(UR)",
        visual_role="Displays 2D/3D transformation matrices, eigenvalue equations, covariance matrices, and linear systems.",
        construction_pattern="mat = Matrix([[2, 1], [0, 3]], bracket_h_buff=0.1).to_corner(UR)",
        update_mechanism="mat.animate.set_column_colors(RED, BLUE)",
        best_practices=[
            "Use DecimalMatrix when displaying dynamic floating point values.",
            "Pass 2D nested lists or NumPy 2D arrays directly into Matrix.",
        ],
        gotchas=[
            "Matrix entries are Tex mobjects; use DecimalMatrix for animated numeric values.",
        ],
    ),
    ManimMappingNode(
        id="manim:Circle",
        name="Manim Circle, Arc & Epicycle Component",
        dimension="2D",
        mobject_classes=["Circle", "Arc", "Annulus"],
        coordinate_adapter="Circle(radius=r, arc_center=axes.c2p(x, y))",
        visual_role="Visualizes Fourier harmonic epicycles, radius constraints, neighborhood balls, and planar boundaries.",
        construction_pattern="circle = Circle(radius=1.5, arc_center=axes.c2p(0, 0), color=BLUE)",
        update_mechanism="Rotate(circle, about_point=axes.c2p(cx, cy))",
        best_practices=[
            "Set arc_center with axes.c2p(x, y) for proper spatial positioning.",
            "Scale radius appropriately according to axes coordinate scaling.",
        ],
        gotchas=[
            "Default Circle radius is in scene units (not axis units); calculate radius via axes.c2p(r, 0)[0] - axes.c2p(0, 0)[0].",
        ],
    ),
    ManimMappingNode(
        id="manim:ValueTracker",
        name="Manim ValueTracker Dynamic State Variable",
        dimension="1D",
        mobject_classes=["ValueTracker", "ComplexValueTracker"],
        coordinate_adapter="tracker.get_value()",
        visual_role="Drives continuous time parameterizations, animated slider values, dynamic Riemann partitions, and root convergence.",
        construction_pattern="tracker = ValueTracker(initial_val)\nself.play(tracker.animate.set_value(target_val), run_time=3)",
        update_mechanism="Mobject.add_updater(lambda m: m.move_to(axes.c2p(tracker.get_value(), f(tracker.get_value()))))",
        best_practices=[
            "Use ValueTracker as the central clock for continuous variable interpolations.",
            "Pair with always_redraw for clean declarative scene construction.",
        ],
        gotchas=[
            "ValueTracker is not a visible Mobject; do not add it to scene with self.add() or self.play(Create(tracker)).",
        ],
    ),
    ManimMappingNode(
        id="manim:VGroup",
        name="Manim Vectorized Mobject Group Container",
        dimension="2D",
        mobject_classes=["VGroup", "Group"],
        coordinate_adapter="VGroup(*mobjects)",
        visual_role="Batches multiple geometric entities, curves, labels, and polygons for coordinated transforms and animations.",
        construction_pattern="group = VGroup(curve1, curve2, label1, label2)\nself.play(FadeIn(group))",
        update_mechanism="self.play(group.animate.shift(RIGHT * 2))",
        best_practices=[
            "Group related sub-elements in VGroup to apply simultaneous animations (.animate.set_opacity(), Transform, FadeIn).",
            "Use arrange(DOWN, buff=0.2) for automatic vertical/horizontal layouts.",
        ],
        gotchas=[
            "VGroup only holds VMobjects; use Group if mixing ThreeDScene mobjects or non-vector elements.",
        ],
    ),
    ManimMappingNode(
        id="manim:Square",
        name="Manim Geometric Rectangle & Boundary Box",
        dimension="2D",
        mobject_classes=["Rectangle", "Square", "SurroundingRectangle"],
        coordinate_adapter="Rectangle(width=w, height=h).move_to(axes.c2p(cx, cy))",
        visual_role="Visualizes Riemann sum integration bars, bounding boxes, interval highlights, and formula frames.",
        construction_pattern="rect = Rectangle(width=dx, height=h, color=GREEN, fill_opacity=0.4).move_to(axes.c2p(x, y/2))",
        update_mechanism="Transform(old_rects, new_rects)",
        best_practices=[
            "Use SurroundingRectangle(mobject, color=YELLOW) to highlight key formulas or results.",
            "Use axes.get_riemann_rectangles() for automatic integration bar generation.",
        ],
        gotchas=[
            "Ensure Rectangle dimensions account for axis scaling factors.",
        ],
    ),
    ManimMappingNode(
        id="manim:DecimalNumber",
        name="Manim Dynamic Numeric Value Display",
        dimension="1D",
        mobject_classes=["DecimalNumber", "Integer"],
        coordinate_adapter="DecimalNumber(number=val).next_to(target, direction)",
        visual_role="Displays live changing numerical quantities (integral area, iteration counter, error bound, objective value).",
        construction_pattern="num = DecimalNumber(0, num_decimal_places=4)\nnum.add_updater(lambda d: d.set_value(tracker.get_value()))",
        update_mechanism="num.add_updater(lambda d: d.set_value(tracker.get_value()))",
        best_practices=[
            "Use DecimalNumber instead of re-instantiating MathTex on every frame.",
            "Combine with MathTex using VGroup or .next_to() for formula value readouts.",
        ],
        gotchas=[
            "Always use .set_value() inside updater rather than replacing the Mobject.",
        ],
    ),
    ManimMappingNode(
        id="manim:TracedPath",
        name="Manim Dynamic Traced Path Curve",
        dimension="3D",
        mobject_classes=["TracedPath"],
        coordinate_adapter="TracedPath(dot.get_center, stroke_color=GOLD, stroke_width=2)",
        visual_role="Dynamically traces real-time paths of moving particles, ODE state vectors, or pendulum bobs.",
        construction_pattern="trail = TracedPath(dot.get_center, stroke_color=GOLD, stroke_width=2, dissipating_time=None)",
        update_mechanism="Automatic continuous path accretion as target point moves",
        best_practices=[
            "Pass dot.get_center (callable function) as first argument.",
            "Set dissipating_time=None for persistent trajectory accumulation.",
        ],
        gotchas=[
            "Pass the method dot.get_center without parentheses so it evaluates dynamically on each frame.",
        ],
    ),
    ManimMappingNode(
        id="manim:Surface",
        name="Manim 3D Surface & Function Mesh",
        dimension="3D",
        mobject_classes=["Surface", "ParametricSurface"],
        coordinate_adapter="Surface(lambda u, v: axes.c2p(u, v, f(u, v)), u_range=[u_min, u_max], v_range=[v_min, v_max])",
        visual_role="Visualizes 3D multivariable surfaces, loss landscapes, scalar fields z = f(x, y), and saddle points.",
        construction_pattern=(
            "surface = Surface(lambda u, v: axes.c2p(u, v, np.sin(u) * np.cos(v)), "
            "u_range=[-3, 3], v_range=[-3, 3], resolution=(32, 32))"
        ),
        update_mechanism="Create(surface) with ambient camera rotation",
        best_practices=[
            "Use moderate resolution (e.g. 24x24 to 36x36) for fast rendering.",
            "Set surface checkerboard_colors or fill_opacity for clear 3D depth perception.",
        ],
        gotchas=[
            "High resolution (> 64x64) causes significant frame rendering slowdowns.",
        ],
    ),
]


ANIMATION_PATTERN_DEFINITIONS: List[AnimationPatternNode] = [
    AnimationPatternNode(
        id="pattern:iterative_tangent_descent",
        name="Iterative Tangent Descent (Newton-Raphson Pattern)",
        description="Animates step-by-step Newton iterations: vertical projection -> tangent line drawing -> x-intercept descent -> next iterate.",
        paradigm="Succession / Iterative Loop with Coordinate Mapping",
        step_sequence=[
            "1. Initialize axes and plot function curve f(x).",
            "2. For each iteration i, calculate current x_i, y_i = f(x_i), and slope m = f'(x_i).",
            "3. Compute next iterate x_{next} = x_i - y_i / m.",
            "4. Animate vertical dashed line from (x_i, 0) to (x_i, y_i).",
            "5. Draw tangent line from (x_i, y_i) to (x_{next}, 0).",
            "6. Flash / Animate Dot moving to (x_{next}, 0) and update step counter text.",
            "7. Repeat until |x_{next} - x_i| < tolerance or max iterations reached.",
        ],
        code_template=(
            "# Step-by-step Newton-Raphson visual loop\n"
            "for i in range(num_steps):\n"
            "    x_curr = steps[i]\n"
            "    y_curr = f(x_curr)\n"
            "    x_next = steps[i + 1]\n"
            "    # Vertical line to curve\n"
            "    v_line = DashedLine(axes.c2p(x_curr, 0), axes.c2p(x_curr, y_curr), color=GRAY)\n"
            "    dot_curve = Dot(axes.c2p(x_curr, y_curr), color=RED)\n"
            "    # Tangent line to next root intercept\n"
            "    tangent = Line(axes.c2p(x_curr, y_curr), axes.c2p(x_next, 0), color=YELLOW)\n"
            "    dot_next = Dot(axes.c2p(x_next, 0), color=GREEN)\n"
            "    self.play(Create(v_line), FadeIn(dot_curve), run_time=0.6)\n"
            "    self.play(Create(tangent), run_time=0.8)\n"
            "    self.play(FadeIn(dot_next), run_time=0.4)\n"
        ),
    ),
    AnimationPatternNode(
        id="pattern:bracket_bisection_narrowing",
        name="Bracket Bisection Narrowing (Brent / Bisection Pattern)",
        description="Animates interval halving [a, b] around a root with shaded interval bands and midpoint evaluation.",
        paradigm="Dynamic Rectangle / Vertical Region Updates",
        step_sequence=[
            "1. Plot curve and identify starting bracket [a, b] where f(a)*f(b) < 0.",
            "2. Render vertical highlight bars or shaded rectangle over [a, b].",
            "3. Compute midpoint c = (a + b) / 2 and evaluate sign of f(c).",
            "4. Animate shrinking bracket boundary from a or b to c.",
            "5. Zoom/focus as interval width becomes sub-pixel.",
        ],
        code_template=(
            "bracket_rect = always_redraw(lambda: Rectangle(\n"
            "    width=abs(axes.c2p(b_tracker.get_value(), 0)[0] - axes.c2p(a_tracker.get_value(), 0)[0]),\n"
            "    height=axes.y_length,\n"
            "    color=BLUE, fill_opacity=0.2\n"
            ").move_to(axes.c2p((a_tracker.get_value() + b_tracker.get_value()) / 2, 0)))"
        ),
    ),
    AnimationPatternNode(
        id="pattern:dijkstra_frontier_expansion",
        name="Graph Dijkstra Frontier Expansion",
        description="Animates prioritized vertex exploration, distance label updates, and shortest-path tree highlighting.",
        paradigm="Graph Vertex/Edge State Color Transitions",
        step_sequence=[
            "1. Create Manim Graph using NetworkX layout positions.",
            "2. Maintain priority queue state and visited sets.",
            "3. For each visited node, transition vertex color from Unvisited (GRAY) -> Frontier (BLUE) -> Settled (GREEN).",
            "4. Pulse adjacent edges and update neighbor distance labels.",
            "5. Once destination reached, trace final shortest path in RED/YELLOW glow with Create(path_lines).",
        ],
        code_template=(
            "# Color frontier and trace path\n"
            "for u, v in dijkstra_steps:\n"
            "    self.play(graph.vertices[v].animate.set_color(YELLOW), run_time=0.3)\n"
            "    self.play(graph.edges[(u, v)].animate.set_color(GREEN).set_stroke(width=4), run_time=0.4)\n"
        ),
    ),
    AnimationPatternNode(
        id="pattern:riemann_sum_limit",
        name="Riemann Sum Limit Approaching Integral Area",
        description="Animates the convergence of subinterval rectangles to the exact integral area under f(x).",
        paradigm="Transform of Riemann Rectangles",
        step_sequence=[
            "1. Compute exact definite integral using scipy.integrate.quad.",
            "2. Generate discrete Riemann rectangles for n = 4, 8, 16, 32, 64.",
            "3. Progressively Transform rectangles group while updating sum value MathTex.",
            "4. Morph final high-N rectangles into smooth axes.get_area() fill.",
        ],
        code_template=(
            "rects = axes.get_riemann_rectangles(graph, x_range=[a, b], dx=0.5, stroke_width=0.5)\n"
            "self.play(Create(rects))\n"
            "for dx in [0.25, 0.1, 0.05]:\n"
            "    new_rects = axes.get_riemann_rectangles(graph, x_range=[a, b], dx=dx, stroke_width=0.2)\n"
            "    self.play(Transform(rects, new_rects), run_time=0.8)\n"
        ),
    ),
    AnimationPatternNode(
        id="pattern:ode_trajectory_phase_space_3d",
        name="3D Chaotic ODE Phase Space Trajectory (Lorenz / Dynamical Systems)",
        description="Animates the continuous integration and dynamic 3D tracing of chaotic differential equations in phase space.",
        paradigm="Numerical Integration + VMobject Smooth Coordinate Path + Ambient Camera Rotation",
        step_sequence=[
            "1. Define continuous vector field dy/dt = f(t, state).",
            "2. Numerically solve IVP using scipy.integrate.solve_ivp(f, t_span, y0, method='RK45', dense_output=True).",
            "3. Sample continuous trajectory points and map to 3D Manim coordinates via [axes.c2p(x, y, z) for x, y, z in solution.y.T].",
            "4. Construct VMobject curve with set_points_smoothly(mapped_points).",
            "5. Animate trajectory revelation via Create(curve) with concurrent ambient 3D camera rotation.",
        ],
        code_template=(
            "# 3D ODE Trajectory in ThreeDScene\n"
            "sol = solve_ivp(lorenz, (0, 40), [1.0, 1.0, 1.0], method='RK45', t_eval=np.linspace(0, 40, 4000))\n"
            "pts = [axes.c2p(x, y, z) for x, y, z in sol.y.T]\n"
            "trajectory = VMobject(color=GOLD, stroke_width=2)\n"
            "trajectory.set_points_smoothly(pts)\n"
            "self.begin_ambient_camera_rotation(rate=0.15)\n"
            "self.play(Create(trajectory), run_time=8, rate_func=linear)\n"
        ),
    ),
]


PRECISION_RULE_DEFINITIONS: List[PrecisionRuleNode] = [
    PrecisionRuleNode(
        id="rule:ode_numerical_integration_only",
        rule_id="PR-000",
        name="Mandatory Numerical ODE Integration",
        title="Never manually construct or approximate ODE trajectories",
        anti_pattern="ParametricFunction(...) with fake butterfly formulas or hardcoded attractor coordinates.",
        correct_pattern="sol = scipy.integrate.solve_ivp(ode_func, t_span, y0, method='RK45'); pts = [axes.c2p(*p) for p in sol.y.T]",
        rationale="Chaotic systems have exponential divergence from initial conditions. Trajectories must be calculated via validated numerical integrators (RK45/solve_ivp).",
        enforcement_level="STRICT",
    ),
    PrecisionRuleNode(
        id="rule:zero_visual_hallucination",
        rule_id="PR-001",
        name="Zero Visual Coordinate Approximation",
        title="Never manually estimate mathematical coordinates on screen",
        anti_pattern="Dot(point=[-1.414, 0, 0]) or estimating roots visually.",
        correct_pattern="root = scipy.optimize.brentq(f, a, b); Dot(point=axes.c2p(root, 0))",
        rationale="Screen coordinates in Manim depend on axis ranges, aspect ratios, and scene camera. Always compute the mathematical result numerically/symbolically, then convert via axes.c2p().",
        enforcement_level="STRICT",
    ),
    PrecisionRuleNode(
        id="rule:coordinate_adapter_strictness",
        rule_id="PR-002",
        name="Strict Coordinate Adapter Usage",
        title="Use axes.c2p(x, y) or number_line.n2p(x) for all placements",
        anti_pattern="Placing labels and curves using hardcoded 3D scene vectors [2.5, -1.2, 0].",
        correct_pattern="dot.move_to(axes.c2p(x, y)); label.next_to(dot, UP, buff=0.15)",
        rationale="Hardcoded scene vectors break instantly if axes are shifted, zoomed, or resized.",
        enforcement_level="STRICT",
    ),
    PrecisionRuleNode(
        id="rule:updater_instantiation_leak",
        rule_id="PR-003",
        name="Updater Object Re-instantiation Prevention",
        title="Avoid heavy Mobject allocation inside updaters",
        anti_pattern="axes.add_updater(lambda a: Axes(...)) inside frame loop.",
        correct_pattern="Use always_redraw for lightweight elements (e.g. Dot, Line, MathTex) or update properties with dot.move_to().",
        rationale="Allocating complex coordinate grids or full Tex mobjects per frame causes severe rendering lag and memory leaks.",
        enforcement_level="RECOMMENDED",
    ),
    PrecisionRuleNode(
        id="rule:symbolic_to_numerical_conversion",
        rule_id="PR-004",
        name="SymPy to NumPy/Manim Bridge",
        title="Lambdify symbolic expressions for numerical evaluation in Manim",
        anti_pattern="Passing raw SymPy Expr directly into axes.get_graph().",
        correct_pattern="f_num = sympy.lambdify(x, expr, 'numpy'); axes.get_graph(f_num)",
        rationale="Manim graph renderers evaluate functions across dense NumPy float arrays. Lambdification guarantees vectorization and prevents TypeError.",
        enforcement_level="STRICT",
    ),
]


CODE_EXAMPLE_DEFINITIONS: List[CodeExampleNode] = [
    CodeExampleNode(
        id="example:newton_sqrt2",
        name="Newton-Raphson Root Finding for Sqrt(2)",
        target_api="scipy.optimize.newton",
        computational_snippet=(
            "import numpy as np\n"
            "from scipy.optimize import newton\n"
            "\n"
            "def f(x): return x**2 - 2\n"
            "def f_prime(x): return 2*x\n"
            "\n"
            "# Record iterations\n"
            "steps = [0.5]\n"
            "for _ in range(5):\n"
            "    x_next = steps[-1] - f(steps[-1]) / f_prime(steps[-1])\n"
            "    steps.append(x_next)\n"
            "root = steps[-1]  # ~1.41421356\n"
        ),
        manim_integration_snippet=(
            "from manim import *\n"
            "import numpy as np\n"
            "\n"
            "class NewtonMethodScene(Scene):\n"
            "    def construct(self):\n"
            "        axes = Axes(x_range=[0, 3, 1], y_range=[-2, 7, 1], axis_config={'include_numbers': True})\n"
            "        graph = axes.get_graph(lambda x: x**2 - 2, color=BLUE)\n"
            "        self.play(Create(axes), Create(graph))\n"
            "        \n"
            "        steps = [0.5, 2.25, 1.5694, 1.4218, 1.4142]\n"
            "        for i in range(len(steps) - 1):\n"
            "            x_curr = steps[i]\n"
            "            y_curr = x_curr**2 - 2\n"
            "            x_next = steps[i+1]\n"
            "            v_line = DashedLine(axes.c2p(x_curr, 0), axes.c2p(x_curr, y_curr), color=GRAY)\n"
            "            tangent = Line(axes.c2p(x_curr, y_curr), axes.c2p(x_next, 0), color=YELLOW)\n"
            "            dot = Dot(axes.c2p(x_curr, 0), color=RED)\n"
            "            self.play(Create(v_line), Create(tangent), FadeIn(dot), run_time=0.7)\n"
        ),
        expected_output_type="float",
        is_verified=True,
    ),
    CodeExampleNode(
        id="example:scipy_brentq_root",
        name="Brentq Zero Crossing Bracketed",
        target_api="scipy.optimize.brentq",
        computational_snippet=(
            "import numpy as np\n"
            "from scipy.optimize import brentq\n"
            "\n"
            "f = lambda x: np.sin(x) - 0.5*x\n"
            "root = brentq(f, 1.0, 2.5)  # Exact zero crossing ~ 1.89549\n"
        ),
        manim_integration_snippet=(
            "from manim import *\n"
            "import numpy as np\n"
            "from scipy.optimize import brentq\n"
            "\n"
            "class BrentqScene(Scene):\n"
            "    def construct(self):\n"
            "        axes = Axes(x_range=[-1, 4, 1], y_range=[-2, 2, 1], axis_config={'include_numbers': True})\n"
            "        f = lambda x: np.sin(x) - 0.5*x\n"
            "        graph = axes.get_graph(f, color=TEAL)\n"
            "        root = brentq(f, 1.0, 2.5)\n"
            "        root_dot = Dot(axes.c2p(root, 0), color=GOLD)\n"
            "        root_label = MathTex(f'x^* \\\\approx {root:.4f}').next_to(root_dot, UP)\n"
            "        self.play(Create(axes), Create(graph))\n"
            "        self.play(FadeIn(root_dot), Write(root_label))\n"
        ),
        expected_output_type="float",
        is_verified=True,
    ),
    CodeExampleNode(
        id="example:networkx_dijkstra",
        name="NetworkX Shortest Path Visualization",
        target_api="networkx.shortest_path",
        computational_snippet=(
            "import networkx as nx\n"
            "G = nx.Graph()\n"
            "G.add_weighted_edges_from([(0,1,2), (1,2,3), (0,3,1), (3,2,1)])\n"
            "path = nx.shortest_path(G, source=0, target=2, weight='weight')  # [0, 3, 2]\n"
        ),
        manim_integration_snippet=(
            "from manim import *\n"
            "import networkx as nx\n"
            "\n"
            "class DijkstraScene(Scene):\n"
            "    def construct(self):\n"
            "        G = nx.Graph()\n"
            "        G.add_edges_from([(0,1), (1,2), (0,3), (3,2)])\n"
            "        pos = {0: [-2,0,0], 1: [0,1.5,0], 3: [0,-1.5,0], 2: [2,0,0]}\n"
            "        mg = Graph(list(G.nodes), list(G.edges), layout=pos, vertex_config={'radius': 0.2})\n"
            "        self.play(Create(mg))\n"
            "        path = [0, 3, 2]\n"
            "        for i in range(len(path)-1):\n"
            "            u, v = path[i], path[i+1]\n"
            "            self.play(mg.edges[(min(u,v), max(u,v))].animate.set_color(YELLOW).set_stroke(width=5))\n"
        ),
        expected_output_type="List[int]",
        is_verified=True,
    ),
    CodeExampleNode(
        id="example:shapely_intersection",
        name="Shapely Curve/Polygon Intersection",
        target_api="shapely.intersection",
        computational_snippet=(
            "from shapely.geometry import Point, Polygon\n"
            "p1 = Point(0, 0).buffer(2.0)  # Circle\n"
            "p2 = Point(1.5, 0).buffer(1.5)\n"
            "inter = p1.intersection(p2)  # Overlap polygon\n"
            "coords = list(inter.exterior.coords)\n"
        ),
        manim_integration_snippet=(
            "from manim import *\n"
            "from shapely.geometry import Point\n"
            "\n"
            "class IntersectionScene(Scene):\n"
            "    def construct(self):\n"
            "        axes = Axes(x_range=[-3, 4, 1], y_range=[-3, 3, 1])\n"
            "        p1 = Point(0, 0).buffer(2.0)\n"
            "        p2 = Point(1.5, 0).buffer(1.5)\n"
            "        inter = p1.intersection(p2)\n"
            "        pts = [axes.c2p(x, y) for x, y in inter.exterior.coords]\n"
            "        inter_poly = Polygon(*pts, color=GREEN, fill_opacity=0.5)\n"
            "        self.play(Create(axes))\n"
            "        self.play(FadeIn(inter_poly))\n"
        ),
        expected_output_type="shapely.Polygon",
        is_verified=True,
    ),
    CodeExampleNode(
        id="example:lorenz_attractor_solve_ivp",
        name="Lorenz Attractor 3D ODE Integration",
        target_api="scipy.integrate.solve_ivp",
        computational_snippet=(
            "import numpy as np\n"
            "from scipy.integrate import solve_ivp\n"
            "\n"
            "def lorenz(t, state, sigma=10.0, rho=28.0, beta=8.0/3.0):\n"
            "    x, y, z = state\n"
            "    return [sigma * (y - x), x * (rho - z) - y, x * y - beta * z]\n"
            "\n"
            "sol = solve_ivp(lorenz, (0, 30), [1.0, 1.0, 1.0], method='RK45', t_eval=np.linspace(0, 30, 2000))\n"
            "trajectory_points = sol.y.T  # Shape: (2000, 3)\n"
        ),
        manim_integration_snippet=(
            "from manim import *\n"
            "import numpy as np\n"
            "from scipy.integrate import solve_ivp\n"
            "\n"
            "class LorenzAttractorScene(ThreeDScene):\n"
            "    def construct(self):\n"
            "        axes = ThreeDAxes(x_range=[-30, 30, 10], y_range=[-30, 30, 10], z_range=[0, 50, 10])\n"
            "        self.set_camera_orientation(phi=65 * DEGREES, theta=-45 * DEGREES)\n"
            "        self.add(axes)\n"
            "        \n"
            "        def lorenz(t, state, sigma=10.0, rho=28.0, beta=8.0/3.0):\n"
            "            x, y, z = state\n"
            "            return [sigma * (y - x), x * (rho - z) - y, x * y - beta * z]\n"
            "        \n"
            "        sol = solve_ivp(lorenz, (0, 40), [1.0, 1.0, 1.0], method='RK45', t_eval=np.linspace(0, 40, 3000))\n"
            "        pts = [axes.c2p(x, y, z) for x, y, z in sol.y.T]\n"
            "        curve = VMobject(color=GOLD, stroke_width=2)\n"
            "        curve.set_points_smoothly(pts)\n"
            "        \n"
            "        self.begin_ambient_camera_rotation(rate=0.15)\n"
            "        self.play(Create(curve), run_time=8, rate_func=linear)\n"
        ),
        expected_output_type="np.ndarray",
        is_verified=True,
    ),
]
