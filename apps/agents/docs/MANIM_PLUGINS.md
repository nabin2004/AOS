# Manim domain plugins — developer notes

I built these as editable Manim packages under `apps/agents/tools/templates/`. The goal is not “one giant animation library.” It is a **semantic visualization API**: libraries compute truth, Manim draws, agents compose concepts.

Related: [Manim Voiceover + AOS audio](MANIM_VOICEOVER.md), [SFT data generation](../sft_data_gen/README.md).

---

## Mental model

```text
                    Shared primitives (manim_viz)
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   manim_math            manim_physics          manim_dsa
   manim_ai              manim_chess
```

Rules I stick to:

1. **Compute ≠ draw.** Numerical / combinatorial truth lives in `compute/` (numpy, scipy, sympy, torch CPU, pure Python). Builders only turn arrays/steps into `VGroup`s.
2. **Concepts are the agent surface.** Prefer `get_concept("id").build(...)` over inventing one-off Manim from scratch when a concept exists.
3. **Compose primitives.** Physics projectile = particle + trajectory + axes. DSA BFS = graph layout + visit order. I do not rewrite axes for every scene.
4. **Chess is the exception that proves the rule.** `manim_chess` uses python-chess as the source of truth and a widget API (`ChessBoard`), not the concept registry. Everything else follows the AI/math registry pattern.

---

## Packages I ship today

| Package | Path | Role |
|---------|------|------|
| `manim_viz` | `tools/templates/viz/` | Shared theme, axes, vectors, particle, plots, array bars, graph/tree layout, `ConceptRegistry` |
| `manim_math` | `tools/templates/math/` | Linalg, calculus, simple ODE (scipy) |
| `manim_physics` | `tools/templates/physics/` | HS mechanics only |
| `manim_dsa` | `tools/templates/dsa/` | Sort / search / BST / BFS–DFS step traces |
| `manim_ai` | `tools/templates/ai/` | Dive-into-DL concepts + torch CPU compute |
| `manim_chess` | `tools/templates/chess/` | 2D SVG board via python-chess + SFX |

All are wired editable from `apps/agents/pyproject.toml` (`tool.uv.sources`). Torch for AI is pinned to the **CPU** wheel (`pytorch-cpu` index).

### Quick imports

```python
# Shared drawing
from manim_viz import make_axes, array_bars, graph_nodes_edges, DEFAULT_THEME

# Curriculum-style domains
from manim_math import get_concept, list_concepts
from manim_physics import get_concept as phys_concept
from manim_dsa import get_concept as dsa_concept
from manim_ai import get_concept as ai_concept, LinearLayer, Network

# Chess widget
from manim_chess import ChessBoard, BoardTheme
```

### Concept IDs (V1)

**Math:** `vector_2d`, `matrix_multiply`, `eigen_2x2`, `function_plot`, `derivative_tangent`, `riemann_sum`, `harmonic_oscillator_phase` (+ stubs `series`, `complex_plane`)

**Physics:** `newtons_second_law`, `projectile_motion`, `shm_spring`, `mechanical_energy`, `momentum_1d_collision`

**DSA:** `array_bars`, `bubble_sort`, `merge_sort`, `binary_search`, `bst_insert`, `bfs`, `dfs` (+ stubs `dijkstra`, `avl`, `heap`, `dp_table`)

**AI:** ~69 concepts across fundamentals / NN / CNN / transformers / optim / stubs — see `list_concepts()` after `import manim_ai`.

```python
from manim_math import list_concepts
print([c.id for c in list_concepts(include_stubs=False)])
```

---

## How I run demos

From `apps/agents` (default Manim colors — black bg, no custom `#1a1a2e`):

```bash
uv run manim -ql tools/templates/math/demos/demo_derivative.py DemoDerivative
uv run manim -ql tools/templates/math/demos/demo_eigen.py DemoEigen
uv run manim -ql tools/templates/physics/demos/demo_projectile.py DemoProjectile
uv run manim -ql tools/templates/physics/demos/demo_shm.py DemoSHM
uv run manim -ql tools/templates/dsa/demos/demo_merge_sort.py DemoMergeSort
uv run manim -ql tools/templates/dsa/demos/demo_bfs.py DemoBFS
```

Demos are **animated scenes** (Create / MoveAlongPath / Transform), not a single `FadeIn` of a concept card. Concept builders remain the reusable “nouns”; demos show how I stage them for teaching.

Outputs land under `apps/agents/media/videos/`.

---

## Extending a plugin

When I add a new idea, I almost never start with a full Scene. I do this:

### 1. Put truth in `compute/`

```python
# manim_dsa/compute/sorting.py — yields steps, no Manim imports
def bubble_sort_steps(arr) -> list[dict]:
    ...
    return [{"array": ..., "highlights": [...], "swaps": [...]}]
```

Same idea in math (`eig_2x2`, `riemann_sum`, `harmonic_oscillator`) and physics (`projectile_trajectory`, `collision_1d`). AI uses `manim_ai.compute.*` on CPU torch.

### 2. Register a builder

```python
from manim_dsa.registry import register_concept
from manim_viz import array_bars, highlight_indices

@register_concept(
    id="bubble_sort",
    domain="dsa",
    chapter="1.1",
    title="Bubble Sort",
    tags=["sorting"],
)
def build_bubble_sort(values=None):
    steps = bubble_sort_steps(values or [5, 1, 4, 2])
    bars = array_bars(steps[-1]["array"])
    ...
    return VGroup(...)
```

Import the module from the package `__init__` / `concepts/__init__.py` so registration runs on import.

### 3. Prefer `manim_viz` for drawing

Axes, vectors, particles, array bars, graph layout — extend `manim_viz` if the primitive is reusable across domains. Do **not** copy-paste NumberPlane setup into every plugin.

### 4. Stub what I am not ready to own

```python
stub_concept(id="dijkstra", domain="dsa", chapter="3.1", title="Dijkstra", tags=["graph"])
```

Agents can still see the id in `list_concepts()`; the card says “coming soon.”

### 5. Add a thin animated demo (optional but valuable)

Demos teach **staging**: Write title → Create axes → animate motion → Indicate. That is what I want the coder agent to imitate, not a frozen poster.

### 6. Wire agents if it is a new package

In `apps/agents/pyproject.toml`:

```toml
dependencies = [..., "manim-mydomain"]

[tool.uv.sources]
manim-mydomain = { path = "tools/templates/mydomain", editable = true }
```

Then add a one-liner to `coder_agent.py` (same place as math/physics/dsa hints).

### What I deliberately skip (for now)

- Runtime `pip install` dependency registries
- Pickle ODE caches / GPU cupy paths
- Refactoring `manim_ai` into `manim_viz` (future migration)
- Full physics / every DSA algorithm / Lorenz

New domains should feel cheap: **~20–30 primitives + compute traces + composition**, not fifty independent scenes.

---

## Agents: how I want the coder to use this

The coder system prompt already steers domain imports. My intended loop:

```text
user topic
   → pick domain (math / physics / dsa / ai / chess)
   → list_concepts / get_concept
   → build() for the hard visual nouns
   → write Scene that animates those mobjects
   → compile_manim_code
   → repair from log (≤3 attempts)
```

Guidance I care about:

- Prefer plugins over hand-rolled matrices / boards / attention weights.
- Keep scenes 2D unless the concept truly needs 3D.
- For narration: VoiceoverScene + bookmarks — see [MANIM_VOICEOVER.md](MANIM_VOICEOVER.md).
- Chess: `ChessBoard` + python-chess legality; do not fake piece motion.
- AI: real torch compute behind attention / conv / optim — no random “fake” attention rows.

If a concept is missing, the agent should either compose `manim_viz` + a small compute snippet, or fall back to plain Manim — and that gap is a signal for me to register a new concept later.

---

## Finetuning / SFT: how plugins change the data story

I collect SFT from **real agent runs that compile Manim**, not fabricated tool traces (`sft_data_gen/`). Plugins change what “good” looks like in those trajectories.

### What I want trajectories to learn

1. **Domain routing** — “projectile” → `manim_physics`; “merge sort” → `manim_dsa`; “softmax” → `manim_ai`.
2. **Concept composition** — import `get_concept`, `build`, then animate; do not paste a 200-line from-scratch SVD every time.
3. **Compute discipline** — when numbers matter (eigenvalues, collision velocities, attention weights), call compute (or a concept that already does).
4. **Repair patterns** — LaTeX / SoX / layout errors, then fix and recompile.

### How I grow data for a new plugin

1. Add primitives + concepts + 1–2 demos (as above).
2. Seed topics in `sft_data_gen/` (e.g. extend `manim_curriculum_200.txt` or a domain-specific list: projectiles, SHM, BFS, Riemann sums).
3. `generate_prompts.py` → prompt bank that *names* the domain and asks for a visual explanation.
4. `collect_traces.py` / `run_waves.sh` until `compile_ok` for those prompts.
5. Export with `export_local_sft.py` / the export_traces pipeline.

The moat I am aiming for:

> Build ~30 good domain primitives → generate high-quality agent trajectories that *compose* them → teach the model that loop.

Adding the 6th domain should not mean “collect 100k random Manim snippets.” It should mean “register concepts + seed prompts + keep the compile/repair loop.”

### Prompt shape that works for me

Naturalistic user requests that imply a visual noun:

- “Animate mid-point Riemann sums for \(f(x)=x^2\) on \([0,2]\).”
- “Show an elastic 1D collision and check momentum.”
- “Walk BFS on a small labeled graph and print visit order.”
- “Explain self-attention weights for tokens I, love, AI.”

Avoid prompts that only ask for theory with no visual deliverable — those do not exercise plugins or Manim compile.

---

## Layout cheat sheet

```text
apps/agents/tools/templates/
  viz/          manim_viz
  math/         manim_math   + demos/
  physics/      manim_physics + demos/
  dsa/          manim_dsa     + demos/
  ai/           manim_ai      + demos/
  chess/        manim_chess   + demos/
```

Typical domain package:

```text
manim_*/ 
  __init__.py          # import concepts → fill registry; export get_concept
  registry.py          # ConceptRegistry singleton (from manim_viz)
  compute/             # no Manim
  concepts/            # @register_concept builders
demos/
  demo_*.py            # animated Scene, default Manim colors
```

---

## Checklist when I ship a domain bump

- [ ] `compute/` covered by a tiny smoke assert (finite arrays / sorted output / row-stochastic attention)
- [ ] `list_concepts()` includes the new ids
- [ ] At least one `-ql` demo renders
- [ ] Agents `pyproject.toml` + `coder_agent.py` hint updated if new package
- [ ] Optional: topic seeds added for SFT wave

That is the whole loop I want this repo to optimize for: **primitives → concepts → demos → agent trajectories → finetune → better composition.**
