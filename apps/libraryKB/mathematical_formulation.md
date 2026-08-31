# Mathematical Formulation of the Library Knowledge Graph (LKG)

This document formalizes the mathematical structures, graph relations, coordinate projection spaces, and scoring functions underlying the **AOS Library Knowledge Graph (AOS-LKG)**.

---

## 1. Graph Definition and Node Spaces

The Library Knowledge Graph is defined as a typed, directed multigraph:
$$\mathcal{G} = (\mathcal{V}, \mathcal{E}, \tau_V, \tau_E)$$

where the node set $\mathcal{V}$ is partitioned into eight disjoint subsets:
$$\mathcal{V} = \mathcal{V}_{\text{lib}} \cup \mathcal{V}_{\text{mod}} \cup \mathcal{V}_{\text{fn}} \cup \mathcal{V}_{\text{cls}} \cup \mathcal{V}_{\text{cap}} \cup \mathcal{V}_{\text{algo}} \cup \mathcal{V}_{\text{concept}} \cup \mathcal{V}_{\text{manim}} \cup \mathcal{V}_{\text{pattern}} \cup \mathcal{V}_{\text{rule}}$$

### Node Type Functions
1. **Computational Implementations**:
   - $f \in \mathcal{V}_{\text{fn}}$: A discrete executable function defined by its signature $\text{sig}(f) = (\mathcal{P}, \mathcal{R})$, qualified namespace $\text{qual}(f) \in \mathcal{S}^*$, and parameter schema $\mathcal{P} = \{(p_i, t_i, v_i^{\text{def}})\}$.
2. **Mathematical Capabilities**:
   - $c \in \mathcal{V}_{\text{cap}}$: An abstract mathematical capability defined by domain $d(c) \in \mathcal{D}$, dimensional rank $\dim(c) \in \{1, 2, 3\}$, input manifold $\mathcal{X}_{\text{in}}$, and output manifold $\mathcal{Y}_{\text{out}}$.
3. **Algorithmic Guarantees**:
   - $a \in \mathcal{V}_{\text{algo}}$: A formal numerical algorithm characterized by time complexity $\mathcal{T}(a)$, convergence order $\mathcal{O}(a)$, and mathematical precondition set $\mathcal{C}(a)$.
4. **Coordinate Bridge Adapters**:
   - $m \in \mathcal{V}_{\text{manim}}$: A visual mapping operator specifying Manim Mobject representations $\mathcal{M}$ and spatial transformation adapter $\Pi_m: \mathbb{R}^k \to \mathbb{R}^3_{\text{scene}}$.

---

## 2. Typed Relational Edge Calculus

The edge set $\mathcal{E} \subseteq \mathcal{V} \times \mathcal{V} \times \tau_E$ contains labeled directed relations:

$$\tau_E = \{\text{CONTAINS}, \text{EXPORTS}, \text{PROVIDES}, \text{IMPLEMENTS}, \text{MAPS\_TO\_MOBJECT}, \text{CONSTRAINED\_BY}, \text{ALTERNATIVE\_TO}, \text{APPLIES\_PATTERN}\}$$

### Core Relational Invariants:
1. **Capability Realization**:
   $$\forall c \in \mathcal{V}_{\text{cap}}, \quad \exists f \in \mathcal{V}_{\text{fn}} \quad \text{s.t.} \quad (f, c, \text{PROVIDES}) \in \mathcal{E}$$
2. **Algorithmic Grounding**:
   $$\forall f \in \mathcal{V}_{\text{fn}}, \quad (f, a, \text{IMPLEMENTS}) \in \mathcal{E} \implies a \in \mathcal{V}_{\text{algo}}$$
3. **Coordinate Projection Grounding**:
   $$\forall c \in \mathcal{V}_{\text{cap}}, \quad \exists m \in \mathcal{V}_{\text{manim}} \quad \text{s.t.} \quad (c, m, \text{MAPS\_TO\_MOBJECT}) \in \mathcal{E}$$

---

## 3. Hierarchical Retrieval & Domain Gating Formulation

Given a natural language animation query $q \in \mathcal{Q}$, the retriever computes a minimal subgraph slice $\mathcal{G}_q^* \subset \mathcal{G}$.

### Step 1: Intent & Domain Classification
Let $\phi(q)$ be the intent projection function returning detected domains $\mathcal{D}_q \subseteq \mathcal{D}$ and spatial dimension $\dim_q \in \{1, 2, 3\}$:
$$\mathcal{D}_q = \{d \in \mathcal{D} \mid \exists w \in \text{Keywords}(d) \text{ in } q\}$$

### Step 2: Capability Candidate Ranking
For each capability $c \in \mathcal{V}_{\text{cap}}$, the capability relevance score is given by:
$$S_{\text{cap}}(c \mid q) = \text{BM25}(c, q) \cdot \left(1 + \mu_1 \cdot \mathbb{I}(d(c) \in \mathcal{D}_q)\right) \cdot \left(1 + \mu_2 \cdot \mathbb{I}(\dim(c) = \dim_q)\right)$$

The optimal capability is selected via:
$$c^* = \arg\max_{c \in \mathcal{V}_{\text{cap}}} S_{\text{cap}}(c \mid q)$$

### Step 3: API Selection with Negative Domain Gating
Let $\mathcal{F}_{\text{cand}} = \mathcal{N}_{\text{graph}}(c^*) \cup \text{Canon}(c^*) \cup \text{Search}_{\text{BM25}}(q \mid \mathcal{D}_q)$. For every candidate function $f \in \mathcal{F}_{\text{cand}}$, its final ranking score is formulated as:

$$S_{\text{api}}(f \mid q, c^*) = w_1 S_{\text{tok}}(f, q) + w_2 \mathbb{I}(f \in \mathcal{N}_{\text{graph}}(c^*)) + w_3 \mathbb{I}(f \in \text{Canon}(c^*)) + w_4 S_{\text{doc}}(f, q) - \lambda \cdot \Omega(d(f), \mathcal{D}_q)$$

where $\Omega(d_1, \mathcal{D}_2)$ is the domain conflict matrix:
$$\Omega(d_1, \mathcal{D}_2) = \begin{cases} 1 & \text{if } d_1 \in \text{Exclusions}(\mathcal{D}_2) \\ 0 & \text{otherwise} \end{cases}$$

When $\lambda \gg w_1 + w_2 + w_3$, any cross-domain distractor (e.g. `networkx.attracting_components` where $d(f) = \text{graph\_theory}$ and $\mathcal{D}_q = \{\text{differential\_equations}\}$) satisfies:
$$S_{\text{api}}(f \mid q, c^*) \to -\infty$$
guaranteeing strict mathematical domain isolation.

---

## 4. Coordinate Transformation & Anti-Hallucination Mapping

Let $\mathcal{M}_{\text{scene}} = [-W/2, W/2] \times [-H/2, H/2] \times [-Z/2, Z/2]$ denote the bounded 3D Manim world coordinate space.

### Coordinate Projection Operator
For any mathematical state vector $\mathbf{x} = (x_1, x_2, \dots, x_k) \in \mathbb{R}^k$, the spatial placement map $\Pi_{\text{axes}}: \mathbb{R}^k \to \mathcal{M}_{\text{scene}}$ is defined as:

$$\Pi_{\text{axes}}(\mathbf{x}) = \begin{bmatrix}
\frac{x_1 - x_{\min}}{x_{\max} - x_{\min}} \cdot W_{\text{axes}} + x_{\text{origin}} \\
\frac{x_2 - y_{\min}}{y_{\max} - y_{\min}} \cdot H_{\text{axes}} + y_{\text{origin}} \\
\frac{x_3 - z_{\min}}{z_{\max} - z_{\min}} \cdot D_{\text{axes}} + z_{\text{origin}}
\end{bmatrix}$$

### Anti-Hallucination Invariant:
$$\forall \mathbf{p} \in \mathcal{P}_{\text{visual}}, \quad \exists \mathbf{x} \in \mathbb{R}^k, \quad \mathbf{p} = \Pi_{\text{axes}}(\mathbf{x})$$
$$\text{with } \mathbf{x} \text{ computed strictly via } f^*(\mathbf{x}_0, t)$$
$$\text{No arbitrary constant vector } \mathbf{c} \in \mathbb{R}^3 \text{ is permitted as an un-mapped coordinate.}$$
