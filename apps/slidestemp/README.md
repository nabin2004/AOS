# AOS Manim Modular Plugin Ecosystem

An extensible, mathematically validated, and theme-agnostic computational visualization ecosystem for Manim.

---

## 🏛️ Ecosystem Architecture

```text
                               AOS Agent / LLM
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
                   Plugin Router             LKG Discovery
                   (Execution)             (Capability Index)
                         │
     ┌───────────────────┼───────────────────┐
     ▼                   ▼                   ▼
Layer A: Presentation Layer B: STEM     Layer C: Reasoning
 ├── aos-manim-slides  ├── aos-manim-maths  ├── aos-manim-algorithms
 └── aos-manim-beamer  ├── aos-manim-physics├── aos-manim-code
                       └── aos-manim-chem   └── aos-manim-proofs
     │                   │                   │
     └───────────────────┴───────────────────┘
                         │
                         ▼
                  aos-manim-core
    (Theme Engine, Manifest Protocol, Invariant Validators)
                         │
                         ▼
                   Manim Engine
```

---

## 📦 Packages

| Package | Layer | Domain | Computational Backbone | Key Capabilities |
|---|---|---|---|---|
| [`aos-manim-core`](file:///c:/Users/nabin/Desktop/myall/slidestemp/aos-manim-core) | Foundation | Protocol & Theme | SymPy, NumPy, Pydantic | `ThemeManager`, `SemanticPalette`, `PluginManifest`, `CanvasBoundsValidator`, `SymbolicEquivalenceValidator` |
| [`aos-manim-slides`](file:///c:/Users/nabin/Desktop/myall/slidestemp/aos-manim-slides) | Layer A | Presentation | Manim | `SlideSpec` AST, Markdown parser, `LayoutEngine` (`VStack`/`HStack`/overflow), `SlideScene`, templates. **User guide:** [aos-manim-slides/docs/01-usage.md](aos-manim-slides/docs/01-usage.md) |
| [`aos-manim-maths`](file:///c:/Users/nabin/Desktop/myall/slidestemp/aos-manim-maths) | Layer B | STEM (Flagship) | SymPy, SciPy, NumPy | `DerivativeVisualizer`, `IntegralVisualizer`, `RootFindingVisualizer`, `MatrixTransformationVisualizer`, `ProbabilityVisualizer` |
| [`aos-manim-algorithms`](file:///c:/Users/nabin/Desktop/myall/slidestemp/aos-manim-algorithms) | Layer C | Reasoning | NetworkX, NumPy | `ArrayMobject`, `NetworkXGraphVisualizer`, `BinarySearchVisualizer`, `BubbleSortVisualizer`, `DijkstraVisualizer` |
| [`aos-manim-physics`](file:///c:/Users/nabin/Desktop/myall/slidestemp/aos-manim-physics) | Layer B | STEM | SciPy, Pint, NumPy | `ProjectileVisualizer`, `FreeBodyDiagram`, `PendulumVisualizer` (solve_ivp ODE) |
| [`aos-manim-code`](file:///c:/Users/nabin/Desktop/myall/slidestemp/aos-manim-code) | Layer C | Reasoning | Python AST, Tracers | `CodeWindow`, `StackFrameMobject`, `CallStackMobject`, `trace_factorial_execution` |
| [`aos-manim-proofs`](file:///c:/Users/nabin/Desktop/myall/slidestemp/aos-manim-proofs) | Layer C | Reasoning | NetworkX, SymPy | `ProofStep`, `ProofDocument`, `DerivationChain`, `ProofStructureValidator` |
| [`aos-manim-chemistry`](file:///c:/Users/nabin/Desktop/myall/slidestemp/aos-manim-chemistry) | Layer B | STEM | NumPy | `AtomMobject` (CPK), `BondMobject`, `Molecule2DMobject` (H2O, CO2, Benzene), `ValenceValidator` |
| [`aos-manim-beamer`](file:///c:/Users/nabin/Desktop/myall/slidestemp/aos-manim-beamer) | Layer A | Presentation | Manim | `Block`, `AlertBlock`, `ExampleBlock`, `BeamerFrame`, `BeamerColumns`, `BeamerPresentation` |

---

## 🎨 Theme Agnostic & Configurable Styling

No plugin hardcodes colors. All visual components resolve tokens dynamically from `ThemeManager`:

```python
from aos_manim_core import set_theme, use_theme

# Switch globally to any built-in or custom theme
set_theme("academic_oxford")  # "modern_dark", "solarized_dark", "nord", "cyberpunk", "minimalist_light"

# Or scoped per slide
with use_theme("nord"):
    # Render slide in Nord palette
    pass
```

---

## 🧪 Automated Invariant Validation

Every plugin provides validation suites to verify mathematical, physical, and visual invariants:
- `SymbolicEquivalenceValidator`: Analytical equivalence via SymPy
- `IntegralConvergenceValidator`: Quadrature accuracy check against analytical integrals
- `RootPrecisionValidator`: Verification of $|f(x^*)| \le \epsilon$
- `EnergyConservationValidator`: Validates $\Delta E / E_0 \le 10^{-3}$ across ODE simulation steps
- `SortedInvariantValidator`: Validates array sorting monotonicity
- `GraphPathValidator`: Checks continuous edge existence along graph routes
- `ValenceValidator`: Enforces chemical bonding limits
- `SlideOverflowValidator` & `CanvasBoundsValidator`: Prevents bounding box visual clipping

---

## 🚀 Running Tests & Demonstration

### Run Full Test Suite (31 unit tests)
```powershell
& .venv\Scripts\pytest -v aos-manim-core aos-manim-slides aos-manim-maths aos-manim-algorithms aos-manim-physics aos-manim-code aos-manim-proofs aos-manim-chemistry aos-manim-beamer
```

### Run Ecosystem Indexer
```powershell
& .venv\Scripts\python.exe registry_indexer.py
```

Slide authoring, voiceover bookmarks, embedding other visualizers, and lecture templates: [aos-manim-slides/docs/01-usage.md](aos-manim-slides/docs/01-usage.md).

### Render Demo Presentation
```powershell
& .venv\Scripts\manim -ql -s examples/demo_presentation.py AOSComprehensiveDemoScene
```

### Render ecosystem lecture (all eight plugins, voiceover cues)
```powershell
& .venv\Scripts\manim -ql examples/ecosystem_lecture.py AOSEcosystemLecture
```