# aos-manim-maths

Flagship STEM mathematics computational visualization plugin for AOS Manim.

## Computational Backbone
- **SymPy**: Analytical derivations, integrals, root finding, symbolic simplifies.
- **SciPy**: High-precision numerical quadrature, Brent's / Newton-Raphson methods, continuous statistical distributions.
- **NumPy**: Vector fields, matrix transformations, determinant analysis.

## Features
- **Calculus**: `DerivativeVisualizer` (instantaneous slopes, secant convergence), `IntegralVisualizer` (Riemann sums, shaded area).
- **Algebra**: `RootFindingVisualizer` (Newton-Raphson step tangent lines).
- **Linear Algebra**: `MatrixTransformationVisualizer` (basis vectors $\hat{i}, \hat{j}$, determinant parallelogram), `VectorFieldVisualizer`.
- **Probability**: `ProbabilityVisualizer` (Gaussian distributions, sigma bands).
- **Mathematical Validators**: `RootPrecisionValidator`, `IntegralConvergenceValidator`.
