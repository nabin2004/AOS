# AOS Mathematical & Computational Knowledge Graph (LKG)

> **Grounding LLM-Generated Manim Programs in Structured Computational Knowledge**

The **AOS Library Knowledge Graph (LKG)** is an architectural bridge connecting scientific computing libraries (**NumPy, SciPy, SymPy, NetworkX, Shapely, mpmath**) with **Manim animation primitives**, mathematical algorithms, coordinate adapters, and strict execution validation rules.

---

## The Core Problem & Philosophy

Instead of dumping hundreds of pages of raw Python documentation into generic vector RAG, the LKG structures scientific computation into a typed, traversable hierarchy:

$$\text{Task} \longrightarrow \text{Concept} \longrightarrow \text{Algorithm} \longrightarrow \text{Library Capability} \longrightarrow \text{API} \longrightarrow \text{Manim Representation} \longrightarrow \text{Animation Strategy}$$

### Four Complementary Layers

```text
                 AOS Library KB
                       │
       ┌───────────────┼────────────────┐
       │               │                │
       ▼               ▼                ▼
  Knowledge Graph    API Index       Semantic Index
(MultiDiGraph JSONL) (O(1) Exact API) (BM25 + Token Index)
       │               │                │
 relationships      signatures       natural language
       │               │                │
       └───────────────┼────────────────┘
                       │
                       ▼
                 Task Retriever
                       │
                       ▼
         Dense LLM Context Slice (500–1500 tokens)
```

---

## Key Features

1. **Introspection & Extraction Engine**:
   - Python introspection (`inspect`, `dir()`, `pkgutil`, `typing`, `__all__`).
   - Safe signature extraction with fallback for compiled C/Cython functions, ufuncs, and built-ins.
   - NumPy and Google docstring parsing for parameter constraints, defaults, and LaTeX formulas.
2. **Computational & Manim Ontology**:
   - 15+ Core Capabilities: Root Finding, Adaptive Quadrature, Symbolic Calculus, ODEs, Spline Interpolation, Eigen-decomposition, SVD, Dijkstra/Shortest Path, Graph Traversals, Polygon Intersections, Convex Hulls, FFT.
   - Manim Mappings: `Axes`, `NumberLine`, `Dot`, `Graph`, `Polygon`, `ValueTracker`, `always_redraw`, `MathTex`.
   - Animation Patterns: `iterative_tangent_descent`, `bracket_bisection_narrowing`, `dijkstra_frontier_expansion`, `riemann_sum_limit`.
   - Strict Precision Rules: Zero visual estimation, coordinate transformation adapters (`axes.c2p()`, `number_line.n2p()`), updater memory leak prevention.
3. **Task Retriever & Prompt Formatter**:
   - Maps user prompt (e.g. *"Animate Newton's method for $\sqrt{2}$"*) to a minimal 500–1500 token high-density context block containing primary and alternative backends, algorithm assumptions, coordinate bridges, and verified code recipes.
4. **Self-Verifying Runtime Validator**:
   - Live version check against installed packages.
   - Signature consistency verification.
   - Code sandbox testing ensuring 100% of executable recipes execute without errors.

---

## Installation & CLI Usage

### 1. Installation
```bash
uv pip install -e ".[dev]"
```

### 2. Build Knowledge Graph
```bash
uv run aos-lkg build
```

### 3. Retrieve LLM Context Slice
```bash
uv run aos-lkg retrieve "Animate Newton's method for finding sqrt(2)"
uv run aos-lkg retrieve "Visualize shortest path using Dijkstra algorithm on a weighted graph"
uv run aos-lkg retrieve "Find intersection of two circles and fill overlapping area"
uv run aos-lkg retrieve "Simulate Lorenz attractor trajectory using ODE integration"
```

### 4. Inspect Any API or Capability Node
```bash
uv run aos-lkg inspect "scipy.optimize.brentq"
uv run aos-lkg inspect "cap:root_finding_bracketed"
```

### 5. Run Live Self-Verification Suite
```bash
uv run aos-lkg verify
```

### 6. View Graph Statistics
```bash
uv run aos-lkg stats
```

---

## Example LLM Prompt Slice Output

When querying: `"Animate Newton's method for finding sqrt(2)"`

```markdown
[TASK]
Animate Newton's method for finding sqrt(2)

[MATH CAPABILITY]
Domain: root_finding
Capability: Derivative-Based Root Finding (Newton-Raphson / Halley / Secant)
Description: Iterative tangent/secant root finding from an initial guess x0 using function and derivative evaluations.
Inputs: Callable[[float], float], float, Optional[Callable[[float], float]]
Outputs: float

[PRIMARY COMPUTATIONAL BACKEND]
API: scipy.optimize.newton
Signature: (func, x0, fprime=None, args=(), tol=1.48e-08, maxiter=50, fprime2=None, x1=None, rtol=0.0, full_output=False, disp=True)
Doc Summary: Find a root of a real or complex function using the Newton-Raphson
Required Params: func (callable), x0 (float, sequence, or ndarray)
Optional Params: fprime=None, args=(), tol=1.48e-08, maxiter=50

[ALGORITHM & METHODOLOGY]
Algorithm: Newton-Raphson Method
Complexity: O(log(1/eps))
Convergence: Quadratic (order 2)
Assumptions: f'(x*) != 0; Initial guess x0 sufficiently close to root

[RELEVANT MANIM MOBJECTS & COORDINATE BRIDGES]
Mobjects: Axes, NumberPlane
Coordinate Adapter: `axes.c2p(x, y)`
- Best Practice: Always wrap math coordinates in axes.c2p(x, y) to obtain Manim scene coordinates.
- Best Practice: Use axes.get_graph(func, color=...) for continuous function curves.

[ANIMATION PATTERN]
Pattern: Iterative Tangent Descent (Newton-Raphson Pattern) (Succession / Iterative Loop with Coordinate Mapping)
Step Sequence:
  1. Initialize axes and plot function curve f(x).
  2. For each iteration i, calculate current x_i, y_i = f(x_i), and slope m = f'(x_i).
  3. Compute next iterate x_{next} = x_i - y_i / m.
  4. Animate vertical dashed line from (x_i, 0) to (x_i, y_i).
  5. Draw tangent line from (x_i, y_i) to (x_{next}, 0).
  6. Flash / Animate Dot moving to (x_{next}, 0) and update step counter text.

[PRECISION & ANTI-HALLUCINATION RULES]
[STRICT] Never manually estimate mathematical coordinates on screen
  Anti-pattern: Dot(point=[-1.414, 0, 0]) or estimating roots visually.
  Correct: root = scipy.optimize.brentq(f, a, b); Dot(point=axes.c2p(root, 0))
  Rationale: Screen coordinates in Manim depend on axis ranges, aspect ratios, and scene camera. Always compute the mathematical result numerically/symbolically, then convert via axes.c2p().

[VERIFIED EXECUTABLE RECIPE]
Example: Newton-Raphson Root Finding for Sqrt(2)
Computational Backend:
```python
import numpy as np
from scipy.optimize import newton

def f(x): return x**2 - 2
def f_prime(x): return 2*x

# Record iterations
steps = [0.5]
for _ in range(5):
    x_next = steps[-1] - f(steps[-1]) / f_prime(steps[-1])
    steps.append(x_next)
root = steps[-1]  # ~1.41421356
```
```

---

## Test Suite

Run pytest with coverage:
```bash
uv run pytest tests/ -v
```
All 20 unit and integration tests pass with 100% verification score.
