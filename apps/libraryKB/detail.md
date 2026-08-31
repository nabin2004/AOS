# AOS-LKG: Comprehensive Technical Architecture & Internal Mechanics

The **AOS Mathematical & Computational Knowledge Graph (LKG)** is an agentic, ontology-grounded knowledge base and hierarchical retrieval engine. It is specifically engineered to feed Large Language Models (LLMs) the **minimal, mathematically exact, and syntactically validated code slice** needed to produce precise Manim animation scripts without coordinate hallucination, numerical drift, or semantic misdirection.

---

## 1. System Overview & Problem Formulation

Standard Retrieval-Augmented Generation (RAG) approaches suffer from severe failure modes when applied to mathematical code generation:
1. **Lexical Distraction**: Flat text similarity retrieves homonyms across unrelated domains (e.g. querying `"Lorenz attractor"` retrieves `networkx.attracting_components` due to the token `"attract"`).
2. **Visual Coordinate Hallucination**: LLMs guess Cartesian screen coordinates (e.g., `Dot(point=[1.414, 0, 0])`) or plot fake parametric butterfly curves instead of solving the true dynamical ODE system.
3. **Context Bloat & Token Waste**: Dumping raw multi-page HTML docstrings overwhelms context windows with irrelevant C-API internals, deprecation notices, and internal wrappers.

AOS-LKG solves this with a **hierarchically constrained knowledge graph**:
$$\text{Library} \longrightarrow \text{Module} \longrightarrow \text{Capability} \longrightarrow \text{API} \longrightarrow \text{Algorithm} \longrightarrow \text{Manim Coordinate Bridge} \longrightarrow \text{Precision Rules}$$

```text
                                 ┌────────────────────────┐
                                 │   Natural Language     │
                                 │   Animation Query      │
                                 └───────────┬────────────┘
                                             │
                                     [ QueryParser ]
                                 (Domain & Dimension Detection)
                                             │
                                             ▼
                                 ┌────────────────────────┐
                                 │    Capability Search   │
                                 │    & Domain Boosting   │
                                 └───────────┬────────────┘
                                             │
                              Graph Traversal (PROVIDES / CONTAINS)
                                             │
                                             ▼
                                 ┌────────────────────────┐
                                 │ Candidate API Ranking  │
                                 │  & Domain Conflict     │
                                 │  Gating (-lambda)      │
                                 └───────────┬────────────┘
                                             │
                                             ▼
                                 ┌────────────────────────┐
                                 │ Manim Coordinate       │
                                 │ Bridge & Pattern       │
                                 │ Resolution (1D/2D/3D)  │
                                 └───────────┬────────────┘
                                             │
                                             ▼
                                 ┌────────────────────────┐
                                 │ Minimal LLM Context    │
                                 │ Prompt Slice           │
                                 └────────────────────────┘
```

---

## 2. Core Subsystems

### 2.1 Safe Dynamic Introspection Engine (`aos_lkg.extractor`)
The introspection engine introspects live Python packages via `inspect`, `importlib`, and `pkgutil` without executing dangerous top-level scripts or crashing on C-extensions:
- **`inspector.py`**:
  - `safe_signature(obj)`: Robustly retrieves parameter names, default values, kind annotations, and return types from Python functions, Cython builtins, and NumPy ufuncs using docstring signature fallback parsing.
  - `get_clean_docstring(obj)`: Cleans leading/trailing indentation and unifies whitespace.
- **`doc_parser.py`**:
  - Standardized parser for NumPy-style and Google-style docstrings.
  - Extracts short descriptions, parameters (`name`, `type`, `description`, `optional`, `default`), returns (`type`, `description`), raises, and code examples.
- **`filters.py`**:
  - Identifies and excludes private symbols (`_foo`), internal build modules (`_internals`, `tests`, `setup`), and deprecated APIs.
- **`crawler.py`**:
  - Modular recursive walker visiting modules up to a configurable `max_depth`.
  - Emits typed `LibraryNode`, `ModuleNode`, `ClassNode`, `FunctionNode`, and structural graph edges (`CONTAINS`, `EXPORTS`).

### 2.2 Semantic & Ontological Enrichment Engine (`aos_lkg.ontology`)
Scientific libraries provide computational implementations, but lack high-level mathematical taxonomy. The ontology layer enriches the raw AST graph with:
- **Mathematical Capabilities (`CapabilityNode`)**:
  - Represents mathematical tasks: `cap:ode_integration`, `cap:root_finding_bracketed`, `cap:root_finding_newton`, `cap:numerical_integration`, `cap:spline_interpolation`, `cap:graph_shortest_path`, `cap:fourier_transform`, `cap:polygon_geometry_intersection`, `cap:spatial_convex_hull_voronoi`.
  - Captures dimensional scope (`1D`, `2D`, `3D`), expected mathematical input types, and return types.
- **Mathematical Concepts (`ConceptNode`)**:
  - Formal definitions: `concept:chaotic_attractor`, `concept:ivp`, `concept:zero_crossing`, `concept:riemann_integral`, `concept:shortest_path`, `concept:fourier_spectrum`.
- **Numerical Algorithms (`AlgorithmNode`)**:
  - Algorithmic guarantees and complexity: `algo:rk45_dormand_prince` ($O(N)$ adaptive), `algo:brent_dekker` ($O(\log(1/\epsilon))$), `algo:newton_raphson` (Quadratic $O(N)$), `algo:dijkstra` ($O((V+E)\log V)$), `algo:quickhull` ($O(N\log N)$).
- **Manim Coordinate Bridges (`ManimMappingNode`)**:
  - Explicit bridge from mathematical outputs to screen coordinates:
    - 3D Dynamical Systems: `ThreeDAxes`, `ThreeDScene`, `axes.c2p(x, y, z)`
    - 2D Calculus & Curves: `Axes`, `NumberPlane`, `axes.c2p(x, y)`, `axes.get_graph()`
    - 1D Root Intervals: `NumberLine`, `number_line.n2p(x)`
    - Graph Networks: `Graph`, `networkx.spring_layout` $\to$ `layout=pos_dict`
    - Geometry: `Polygon(*[axes.c2p(x, y) for x, y in exterior])`
- **Precision & Anti-Hallucination Rules (`PrecisionRuleNode`)**:
  - Injects non-negotiable prompt instructions barring the LLM from guessing coordinates, faking parametric curves, or hardcoding scene coordinates.

### 2.3 Graph Storage & Indexing (`aos_lkg.storage`)
- **`GraphStore`**:
  - Implements bidirectional indexing over a NetworkX `MultiDiGraph` with JSON Lines persistence (`library_graph.jsonl`).
  - Provides instant sub-millisecond neighbor queries:
    - `get_apis_for_capability(cap_id)`
    - `get_algorithms_for_api(api_id)`
    - `get_manim_mappings_for_capability(cap_id)`
    - `get_precision_rules(cap_id)`
- **`ApiIndex`**:
  - Fast hash map index (`api_index.jsonl`) supporting exact qualified name lookups (`scipy.integrate.solve_ivp`), short function name index (`solve_ivp`), and library module queries.
- **`SemanticIndex`**:
  - Inverted BM25 index with mathematical synonym expansion (`lorenz` $\to$ `ode`, `solve_ivp`, `attractor`, `chaos`).
  - Multi-representation document indexing (`node.name`, `node.domain`, `node.docstring`, `node.canonical_apis`).
  - Domain gating matrix: automatically assigns negative penalties to candidates in conflicting domains.

### 2.4 Hierarchical Task Retriever (`aos_lkg.retriever`)
Unlike flat RAG which queries all 9,000+ nodes uniformly, `TaskRetriever` executes a 4-stage pipeline:
1. **Query Parsing**: Detects math domains (`differential_equations`, `root_finding`, `graph_theory`), spatial dimensionality (`1D`, `2D`, `3D`), and mathematical entities.
2. **Capability Selection**: Ranks candidate capabilities using domain-weighted BM25.
3. **Graph-Constrained API Candidate Discovery**: Collects APIs linked to the primary capability via graph edges (`PROVIDES`) and `canonical_apis`.
4. **Domain Gating & Re-ranking**: Scores candidates using token matches, domain compatibility, and graph priority, while eliminating cross-domain distractions.

### 2.5 Self-Verification & Health Engine (`aos_lkg.validator`)
- **`RuntimeChecker`**: Validates that all indexed libraries and API symbols exist in the active Python runtime.
- **`CodeSandbox`**: Executes computational code snippets in an isolated, monitored sub-environment to verify that return types and outputs match graph expectations without raising exceptions.
- **`HealthReport`**: Generates full health scorecards measuring graph integrity, edge coverage, and executable recipe validity.

---

## 3. Configuration & Extensibility

AOS-LKG is fully configurable via `lkg_config.yaml`. Adding new scientific packages is declarative:

```yaml
data_dir: data
quick_mode: false
embedding_provider: bm25

libraries:
  - name: scipy
    submodules: [optimize, integrate, interpolate, linalg, signal, spatial, special]
    max_depth: 3
    domain: calculus

  - name: scikit-learn
    submodules: [cluster, decomposition, manifold]
    max_depth: 3
    domain: machine_learning
```

To dynamically register a library from the command line:
```bash
uv run aos-lkg add-library scikit-learn --submodules cluster,decomposition --domain machine_learning --build
```
