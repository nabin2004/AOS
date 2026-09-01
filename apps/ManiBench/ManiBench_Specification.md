# ManiBench: A Benchmark for Testing Visual-Logic Drift and Syntactic Hallucinations in Manim Code Generation

**Oli, Nabin¹**  
*¹Sunway College Kathmandu, Birmingham City University, Kathmandu, Nepal*

---

## Abstract

Traditional code-generation benchmarks like HumanEval and MBPP excel at testing logic and syntax, but they fall short when code must translate into dynamic, pedagogical visuals. We introduce **ManiBench**, a specialized benchmark designed to evaluate LLM performance in generating Manim CE (Community Edition) code, a domain where temporal fidelity and version-aware API correctness are paramount.

ManiBench addresses two critical failure modes prevalent in LLM outputs:

1. **Syntactic Hallucinations**: Generating code that is grammatically valid in Python but references non-existent functions in manim, uses outdated or deprecated APIs, undefined classes, or calls that break under specific library versions.

2. **Visual-Logic Drift**: Occurrences where generated visuals diverge from intended mathematical logic, such as missing required events, incorrect causal relationships, timing errors, or model struggling to animate mathematical concepts.

The benchmark aims to collect 150-200 problems, launching with a pilot of 12 high-quality challenges across five difficulty levels. These span domains including calculus, linear algebra, probability, topology, and AI. Task types are uniquely structured into categories such as drift-sensitive transformations, debugging, version-conflict traps, and multi-scene narratives. Each pilot problem includes comprehensive reference code analysis derived from 3Blue1Brown's original ManimGL source code, cataloging scene classes, visual techniques, API patterns, and detailed ManimGL→ManimCE version conflict mappings.

To move beyond simple test-case based checks, ManiBench employs a four-tier scoring system: (1) **Executability** (Pass@1): Fraction of outputs running without exceptions or deprecated imports; (2) **Version-Conflict Error Rate**: Frequency of runs triggering mixed-API or legacy errors; (3) **Alignment Score**: The weighted fraction of required visual events that are both present and temporally accurate; (4) **Coverage Score**: The density of pedagogical elements, including mathematical-to-visual mapping and numeric annotations.

By formalizing the requirements for temporal and syntactic precision, ManiBench provides a foundational testbed for the next generation of automated educational content and visual logic synthesis.

**Keywords:** Syntactic Hallucinations, Visual-Logic Drift, ManimCE-code generation, Benchmark, LLM Evaluation, Animation Code Generation

---

## 1. Introduction

### 1.1 Motivation

The rise of large language models has dramatically accelerated code generation research. Benchmarks like HumanEval, MBPP, and APPS have become standard evaluation tools for assessing LLM coding ability. However, these benchmarks primarily focus on:

- **Logic correctness**: Does the code solve the algorithmic problem?
- **Syntax validity**: Does the code parse and execute without errors?
- **Output matching**: Do computed results match expected values?

These criteria are insufficient for domains where code generates continuous, time-dependent visual outputs. Manim, a Python animation engine created by Grant Sanderson (3Blue1Brown), generates mathematical animations by composing scene objects, applying transformations, and controlling timing. A Manim script can be **syntactically valid** yet produce:

- **Incorrect visual semantics**: An animation that moves in the wrong direction
- **Timing misalignments**: Events that occur out of order or at wrong times
- **Pedagogical failure**: An animation that obscures rather than clarifies the concept

Additionally, Manim exists in two major versions:

- **Manim CE (Community Edition)**: Open-source, actively maintained, with modern API
- **Manim GL (3B1B's version)**: Original version, uses some deprecated constructs, hand-optimized for performance

LLMs frequently mix APIs from both versions or reference functions that have been moved or renamed, producing code that fails under specific library versions.

### 1.2 Contributions

ManiBench makes four key contributions:

1. **Formalized Visual-Logic Metrics**: We define Alignment Score and Coverage Score to capture whether generated animations match pedagogical intent, beyond mere syntactic validity.

2. **Version-Aware Evaluation**: We explicitly test version-conflict errors and deprecated API usage, measuring whether code adheres to a specific Manim version's API contract.

3. **Curated Pilot Dataset**: We provide 12 hand-crafted benchmark problems drawn from 3Blue1Brown's published videos, with detailed visual event specifications and annotations.

4. **Reference Code Analysis**: For all 12 pilot problems, we analyze the original 3Blue1Brown ManimGL source code (~53,000 lines across 21 files), cataloging 143 scene classes, 120+ visual techniques, and 145 specific ManimGL→ManimCE incompatibilities. This enables precise version-conflict evaluation and provides ground truth for visual event expectations.

---

## 2. Problem Definition

### 2.1 The Two Failure Modes

#### Syntactic Hallucinations

An LLM generates code that:
- References non-existent classes (e.g., `VMobject` with incorrect spelling)
- Uses deprecated functions (e.g., `mobject.scale()` instead of `mobject.scale_to_fit_width()`)
- Calls methods with incorrect signatures
- Mixes Manim GL syntax with Manim CE (e.g., using OpenGL-specific rendering calls in CE)

**Example**:
```python
# HALLUCINATED: class does not exist
circle = MCircle(color=BLUE)  # Should be Circle

# HALLUCINATED: deprecated method
circle.apply_matrix([[1, 0], [0, 1]])  # CE removed in favor of apply_complex_function
```

#### Visual-Logic Drift

An LLM generates code that:
- Omits required visual events (e.g., gradient descent step without showing dot movement)
- Implements events in wrong order (e.g., loss curve updates before parameter updates)
- Uses incorrect timing (animations too fast, pauses missing)
- Fails to show causal relationships (e.g., showing result without showing derivation)

**Example**:
```python
# DRIFTED: Gradient descent without showing step updates
def construct(self):
    # Shows loss curve but dot doesn't move downhill
    loss_curve.animate.points = new_points
    # Missing: dot.animate.move_to(new_point)
```

### 2.2 Evaluation Challenges

**Challenge 1: Subjectivity of "Correct"**  
What counts as a correct gradient descent animation? Must the dot move along the loss surface? Must the curve update dynamically? Must the learning rate shrink?

**Challenge 2: Version Fragmentation**  
A script that passes in Manim CE may fail in Manim GL. We must specify which version(s) code targets.

**Challenge 3: Temporal Semantics**  
Unlike static code output (e.g., classification accuracy), animations have temporal semantics. An event can be present but timed incorrectly, creating pedagogical failure.

---

## 3. Benchmark Design

### 3.1 Metric Definitions

#### Metric 1: Executability (Pass@1)

**Definition**: Fraction of generated outputs that run without raising exceptions or using deprecated imports.

**Computation**:
```
Executability = (# successful executions) / (# total attempts)
```

**Success criteria**:
- Script completes without runtime exception
- No deprecated imports detected (scanned via regex or AST analysis)
- No warnings from Manim deprecation system

**Failure cases**:
- Import error (e.g., `from manim import NonExistent`)
- Runtime AttributeError (e.g., `mobject.invalid_method()`)
- Type error (e.g., passing wrong type to function)
- Unhandled exception during scene rendering

#### Metric 2: Version-Conflict Error Rate

**Definition**: Frequency with which generated code triggers errors specific to version constraints.

**Computation**:
```
Version_Conflict_Error_Rate = (# mixed-API or legacy errors) / (# total attempts)
```

**Tracked errors**:
- GL-specific syntax in CE code
- CE-only syntax in GL code
- Calls to renamed/moved functions
- Signature mismatches due to API evolution

**Example detection**:
```python
# GL-only: uses GL rendering context
from manim_gl import *
class MyScene(Scene):
    def construct(self):
        # CE and GL share most API, but GL adds render_to_movie_file()
        self.render_to_movie_file("output.mp4", renderer="opengl")
```

#### Metric 3: Alignment Score

**Definition**: The weighted fraction of required visual events that are both present and temporally accurate.

**Computation**:
```
Alignment_Score = Σ(weight_i × is_present_i × is_correct_timing_i) / Σ(weight_i)
```

Where:
- `weight_i` = importance weight of event `i` (0.0–1.0)
- `is_present_i` = 1 if event `i` is present in output, else 0
- `is_correct_timing_i` = 1 if event `i` occurs at expected time, else 0

**Required events** are specified in the problem annotation:
- What objects must move/transform?
- In what order must events occur?
- What constraints bind their timing?

**Example** (Gradient Descent):
```
Event 1 (weight=0.8): Dot moves downhill along loss surface
Event 2 (weight=0.7): Loss curve updates reflect new loss value
Event 3 (weight=0.6): Learning rate shrinks over time
Event 4 (weight=0.5): Final convergence shown explicitly

Alignment_Score = (0.8 + 0.7 + 0 + 0.5) / (0.8 + 0.7 + 0.6 + 0.5) = 0.71
```

#### Metric 4: Coverage Score

**Definition**: The density of pedagogical elements (mathematical explanation, visual mapping, numeric evidence).

**Computation**:
```
Coverage_Score = (# elements present) / (# required elements)
```

**Required elements** depend on problem domain:
- **Mathematical explanation**: Textual labels, annotations, formulas
- **Visual mapping**: Color coding, consistent object representations
- **Numeric evidence**: Values displayed (e.g., loss value, parameter value)
- **Structural clarity**: Scene organization, logical grouping

**Example** (Determinant):
```
Element 1: Grid visualized  ✓ (present)
Element 2: Transformation visualized  ✓ (present)
Element 3: Area scaling shown  ✗ (missing)
Element 4: Determinant value displayed  ✓ (present)

Coverage_Score = 3 / 4 = 0.75
```

### 3.2 Task Categories

ManiBench organizes problems into five categories:

**1. Direct Visualization (40%)**
- **Description**: Prompt → Python code (classic code generation)
- **Example**: "Write Manim code to animate the chain rule using function composition"
- **Difficulty**: Levels 1-3
- **Metric focus**: Executability, Alignment Score

**2. Drift-Sensitive (20%)**
- **Description**: Given script + required temporal transformation. Detect if visual output matches intent.
- **Example**: "Here is code for gradient descent. Does the loss curve update before or after the dot moves?"
- **Difficulty**: Levels 2-4
- **Metric focus**: Alignment Score, Coverage Score

**3. Debugging (20%)**
- **Description**: Broken code → fix (repair task)
- **Example**: "Fix this gradient descent code so the dot moves downhill and the loss curve updates"
- **Difficulty**: Levels 2-4
- **Metric focus**: Executability, Alignment Score

**4. Version-Conflict Traps (10%)**
- **Description**: Code with tempting outdated syntax. Evaluate if model recognizes version constraints.
- **Example**: "Rewrite this GL rendering call for Manim CE"
- **Difficulty**: Levels 3-5
- **Metric focus**: Version-Conflict Error Rate, Executability

**5. Multi-Scene Narrative (10%)**
- **Description**: Hardest tier. Multi-scene script combining multiple domains.
- **Example**: "Write a 3-scene animation: (1) introduce the theorem, (2) prove via construction, (3) show counterexample"
- **Difficulty**: Levels 4-5
- **Metric focus**: All metrics

### 3.3 Difficulty Levels

**Level 1 (Trivial)**
- Task: Animate simple objects (circles, squares, text)
- Example: "Create a blue circle and make it grow"
- Executability expectation: >95%

**Level 2 (Basic)**
- Task: Animate transformation or simple mathematical concept
- Example: "Animate a line rotating around a point"
- Executability expectation: 80–90%

**Level 3 (Intermediate)**
- Task: Combine multiple transformations, show mathematical relationship
- Example: "Show how the chain rule decomposes f(g(x)) via function mapping"
- Executability expectation: 70–80%

**Level 4 (Advanced)**
- Task: Multi-step derivation, temporal synchronization, pedagogical clarity
- Example: "Animate gradient descent with loss curve updating synchronized with parameter movement"
- Executability expectation: 50–70%

**Level 5 (Expert)**
- Task: Complex concept, multiple scenes, advanced Manim features
- Example: "Animate hairy ball theorem using vector field visualization on a sphere"
- Executability expectation: 30–50%

---

## 4. Benchmark Dataset

### 4.1 Pilot Dataset: 12 Problems

The pilot dataset includes 12 hand-curated problems drawn from 3Blue1Brown's published videos. Each problem includes:

1. **Problem Statement**: Natural language description
2. **Video Source**: YouTube link and timestamp
3. **Required Visual Events**: Formal specification of what must appear
4. **Difficulty Level**: 1–5
5. **Task Category**: Direct Visualization, Drift-Sensitive, Debugging, etc.
6. **Success Criteria**: Specific checkpoints for Executability, Alignment, Coverage
7. **Reference Implementation Notes**: (not shared with models, for human evaluation)
8. **Reference Code Analysis**: Scene class inventory, visual techniques, API patterns, and version conflict notes derived from original 3Blue1Brown source code
9. **Raw Code Files**: Paths to original ManimGL source files

### 4.2 Reference Code Analysis

For each pilot problem, we obtained and analyzed the original source code from 3Blue1Brown’s video repository. This analysis provides:

- **Scene class inventory**: All scene classes with descriptions and key methods (143 total across 12 problems)
- **Visual technique catalog**: Specific rendering and animation patterns used (e.g., Riemann rectangle sequences, grid transformation animations, particle systems, stereographic projections)
- **Manim API patterns**: Updaters, animation types, 3D constructs, layout methods, and custom classes used
- **Version conflict mapping**: Specific ManimGL constructs that have no direct ManimCE equivalent (145 incompatibilities documented)

| Problem | Source Files | Total Lines | Scene Classes | Visual Techniques | GL→CE Conflicts |
|---------|-------------|-------------|---------------|-------------------|-----------------|
| MB-001 | 4 | 2,193 | 16 | 10 | 15 |
| MB-002 | 3 | 8,598 | 16 | 16 | 13 |
| MB-003 | 2 | 3,309 | 13 | 11 | 14 |
| MB-004 | 2 | 5,120 | 13 | 9 | 10 |
| MB-005 | 1 | 1,132 | 11 | 7 | 10 |
| MB-006 | 3 | 7,036 | 12 | 9 | 11 |
| MB-007 | 1 | 7,044 | 13 | 9 | 11 |
| MB-008 | 1 | 2,287 | 4 | 7 | 10 |
| MB-009 | 2 | 4,943 | 11 | 9 | 11 |
| MB-010 | 1 | 3,676 | 11 | 9 | 10 |
| MB-011 | 3 | 3,796 | 12 | 12 | 16 |
| MB-012 | 1 | 4,135 | 11 | 12 | 14 |
| **Total** | **24** | **~53,269** | **143** | **120** | **145** |

#### Common Version Incompatibility Categories

1. **Import system**: `manim_imports_ext` → `from manim import *`
2. **Class configuration**: `CONFIG` dict pattern → `__init__` parameters
3. **Scene types**: `InteractiveScene`, `GraphScene`, `ReconfigurableScene` → `Scene`/`Axes` in CE
4. **Animation renames**: `ShowCreation` → `Create`, `FadeInFrom` → `FadeIn(shift=...)`
5. **PiCreature ecosystem**: `TeacherStudentsScene`, `Eyes`, `PiCreatureSays` → not in CE
6. **3D rendering**: `apply_depth_test`, `set_shading`, `TexturedSurface` → limited CE support
7. **Camera control**: `self.frame.reorient()` → `self.camera.frame` in CE
8. **Custom mobjects**: `NetworkMobject`, `Car`, `Clock`, `DieFace`, `GlowDot` → custom implementation needed

---

### Problem 1: Colliding Blocks Compute π

**Metadata**:
- **Video ID**: 6dTyOl1fmDo (YouTube)
- **Category**: Drift-Sensitive, Multi-Scene
- **Difficulty Level**: 4
- **Domain**: Physics, Numerics

**Problem Statement**:
Write Manim code to animate the collision of two blocks sliding on a frictionless surface. Block A (mass M) starts at rest. Block B (mass m) approaches from the left with velocity v₀. After elastic collision, count the total number of collisions that occur. The problem's magical property: if m/M = 0.01, exactly π wall collisions occur. Animate:
1. Block A (mass M) at x = 10, Block B (mass m) at x = 0 moving right
2. Show velocity vectors above each block
3. Show collision counter incrementing at each collision
4. Show velocity updates after each collision (calculated via elastic collision formulas)
5. Show final state with block B at rest and block A moving away
6. Display text: "Number of collisions: {n}" where n approaches π

**Required Visual Events** (with weights):
- Blocks move and collide (weight: 0.9)
- Collision counter increments correctly (weight: 0.8)
- Velocity vectors update after collision (weight: 0.7)
- Final text displays collision count (weight: 0.6)

**Success Criteria**:
- Executability: Code runs without error in Manim CE
- Alignment Score: ≥ 0.70 (most events present)
- Coverage Score: ≥ 0.75 (velocity labels, counter visible)

**Exemplar Annotation** (for manual evaluation):
```
Expected alignment: Events must occur in sequence (collision → update → count).
If only collisions and counter appear (no velocity updates), score = 0.65.
If all events present but timing is off (counter increments before collision), score = 0.55.
```

---

### Problem 2: Gradient Descent, How Neural Networks Learn

**Metadata**:
- **Video ID**: IHZwWFHWa-w
- **Category**: Direct Visualization, Drift-Sensitive
- **Difficulty Level**: 3
- **Domain**: Machine Learning, Calculus

**Problem Statement**:
Create a Manim scene animating gradient descent on a 2D loss landscape. Show:
1. A parametric surface z = L(w₁, w₂) representing loss as a function of two parameters
2. A dot starting at a high-loss location
3. At each step: (a) compute gradient ∇L at the dot's position, (b) move dot in direction of -∇L, (c) update a loss curve showing historical loss values
4. Animate 5–10 steps of descent with diminishing step size
5. Show arrows indicating gradient direction
6. Label axes: "w₁", "w₂", "Loss"

**Required Visual Events**:
- Surface/landscape visualized (weight: 0.8)
- Dot positioned at initial location (weight: 0.8)
- Gradient arrow shown and updates (weight: 0.7)
- Dot moves downhill (weight: 0.9)
- Loss curve plots historical values (weight: 0.8)
- Step size diminishes (visually, via arrow length) (weight: 0.6)

**Success Criteria**:
- Executability: ≥ 95%
- Alignment Score: ≥ 0.75 (all events present and roughly synchronized)
- Coverage Score: ≥ 0.80 (labels, arrows, curve all visible)

**Exemplar Annotation**:
```
Common errors:
- Dot moves but loss curve doesn't update (drift)
- Gradient arrows point uphill instead of downhill (logic error)
- Surface doesn't deform or update (missing pedagogical element)
- Events occur out of sync (dot moves before gradient updates)
```

---

### Problem 3: But What Is a Convolution?

**Metadata**:
- **Video ID**: KuXjwB4LzSA
- **Category**: Direct Visualization, Drift-Sensitive
- **Difficulty Level**: 3
- **Domain**: Signal Processing, Linear Algebra

**Problem Statement**:
Animate the convolution operation between a signal and a kernel. Show:
1. A 1D signal plotted on a horizontal axis (bar chart or curve)
2. A 1D kernel (filter) displayed as a sliding window
3. The sliding window moves left-to-right along the signal
4. At each position, show the element-wise product (animation or highlight)
5. Show the integral (sum) accumulating in a separate output graph
6. Animate the output graph building up point-by-point
7. Label: "Signal", "Kernel", "Convolution Output"

**Required Visual Events**:
- Signal visualized (weight: 0.8)
- Kernel/window visualized (weight: 0.8)
- Window moves through signal (weight: 0.9) [CRITICAL]
- Product highlighted at current position (weight: 0.7)
- Integral/sum accumulates in output (weight: 0.8)
- Output graph builds dynamically (weight: 0.8)

**Success Criteria**:
- Executability: ≥ 90%
- Alignment Score: ≥ 0.80 (window must move; this is the core of convolution)
- Coverage Score: ≥ 0.75

**Exemplar Annotation**:
```
Critical failure: If window doesn't move (static visualization of convolution at one position), score drops to ≤ 0.50.
This is THE defining visual event of convolution.
```

---

### Problem 4: Eigenvectors & Eigenvalues | Chapter 14

**Metadata**:
- **Video ID**: PFDu9oVAE-g
- **Category**: Direct Visualization
- **Difficulty Level**: 4
- **Domain**: Linear Algebra, Transformations

**Problem Statement**:
Animate how eigenvectors behave under a 2×2 matrix transformation. Show:
1. A 2D coordinate grid with basis vectors **e₁** and **e₂** highlighted
2. A 2×2 matrix A visualized as a transformation (grid deforms)
3. Most vectors rotate and change length
4. Special vectors (eigenvectors) only change length (stay on same line)
5. Color code eigenvectors distinctly (e.g., red for λ₁, blue for λ₂)
6. Display eigenvalues λ₁ and λ₂ alongside eigenvectors
7. Show transformation A applied smoothly over 2 seconds
8. After transformation, highlight that eigenvectors are "special"

**Required Visual Events**:
- Grid visualized (weight: 0.8)
- Basis vectors highlighted (weight: 0.7)
- Transformation applied (grid deforms) (weight: 0.9)
- Eigenvectors identified and colored distinctly (weight: 0.8)
- Eigenvalue labels shown (weight: 0.7)
- Eigenvectors remain collinear with original (weight: 0.8)

**Success Criteria**:
- Executability: ≥ 85%
- Alignment Score: ≥ 0.75
- Coverage Score: ≥ 0.80 (labels, color coding, highlighting all present)

**Exemplar Annotation**:
```
Alignment check: Eigenvectors must NOT rotate during transformation (only scale).
If eigenvectors rotate, alignment score drops significantly (visual-logic drift).
```

---

### Problem 5: The Determinant | Chapter 6

**Metadata**:
- **Video ID**: Ip3X9LOh2dk
- **Category**: Direct Visualization
- **Difficulty Level**: 2
- **Domain**: Linear Algebra, Visualization

**Problem Statement**:
Animate the geometric interpretation of the determinant. Show:
1. A unit parallelogram (defined by basis vectors **u** and **v**)
2. A 2×2 matrix A applied to the parallelogram
3. The parallelogram transforms smoothly
4. Label: "Original Area = 1"
5. After transformation, label: "New Area = |det(A)|"
6. Show the numerical value of det(A) updating as the transformation occurs
7. Display the 2×2 matrix values alongside

**Required Visual Events**:
- Original parallelogram visualized with area = 1 (weight: 0.8)
- Matrix displayed (weight: 0.7)
- Parallelogram transforms (weight: 0.9)
- New area labeled (weight: 0.8)
- Determinant value displayed and updates (weight: 0.8)

**Success Criteria**:
- Executability: ≥ 95%
- Alignment Score: ≥ 0.85 (simple, core events only)
- Coverage Score: ≥ 0.90 (labels and numbers crucial)

**Exemplar Annotation**:
```
Pedagogical intent: Show that det(A) scales area.
If transformation occurs but area is not labeled or determinant value not shown, coverage drops.
```

---

### Problem 6: The Central Limit Theorem

**Metadata**:
- **Video ID**: zeJD6dqJ5lo
- **Category**: Direct Visualization, Drift-Sensitive
- **Difficulty Level**: 3
- **Domain**: Probability, Statistics

**Problem Statement**:
Animate the Central Limit Theorem by showing how the distribution of sample means approaches a normal distribution. Show:
1. Histogram of samples from an arbitrary distribution (e.g., uniform or bimodal)
2. Repeatedly draw random samples, compute their mean, and add to a separate histogram
3. Animate the second histogram morphing from random/flat to a bell curve (normal distribution)
4. Overlay or label the resulting normal distribution
5. Show text: "Distribution of sample means → Normal distribution"

**Required Visual Events**:
- Original distribution histogram visualized (weight: 0.7)
- Samples drawn (visual indication) (weight: 0.7)
- Sample means computed and plotted (weight: 0.8)
- Histogram of sample means builds (weight: 0.9)
- Histogram converges to normal shape (weight: 0.8)
- Normal curve overlay shown (weight: 0.7)

**Success Criteria**:
- Executability: ≥ 85%
- Alignment Score: ≥ 0.75 (histogram must morph; this is key)
- Coverage Score: ≥ 0.70

**Exemplar Annotation**:
```
Critical failure: If the histogram just appears fully formed as normal (no morphing), this is visual-logic drift.
The animation must show gradual convergence.
```

---

### Problem 7: The Medical Test Paradox (Bayes' Theorem)

**Metadata**:
- **Video ID**: lG4VkPoG3ko
- **Category**: Direct Visualization
- **Difficulty Level**: 2
- **Domain**: Probability, Bayes' Theorem

**Problem Statement**:
Animate Bayes' theorem using the "Bayes box" visualization. Show:
1. A rectangle divided into four quadrants representing:
   - P(sick ∩ +)  (top-left)
   - P(not-sick ∩ +)  (top-right)
   - P(sick ∩ −)  (bottom-left)
   - P(not-sick ∩ −)  (bottom-right)
2. Initially, populate with hypothetical counts (e.g., 1 sick person in 1000)
3. Animate the division showing how many test + among the 1000
4. Highlight the sick population who tested + (top-left)
5. Show final calculation: P(sick | +) = (top-left) / (top-left + top-right)
6. Display final probability and explain the paradox (test is 95% accurate, but low disease prevalence → high false positive rate)

**Required Visual Events**:
- Rectangle divided into four quadrants (weight: 0.8)
- Populations labeled (weight: 0.7)
- Populations animated (filling or reordering) (weight: 0.8)
- Calculation shown step-by-step (weight: 0.8)
- Final probability computed and displayed (weight: 0.8)

**Success Criteria**:
- Executability: ≥ 95%
- Alignment Score: ≥ 0.80
- Coverage Score: ≥ 0.85 (all labels, all populations visible)

**Exemplar Annotation**:
```
Alignment check: Order matters. Populations must be animated in a logical sequence.
If final calculation appears without showing the box, this is pedagogical failure.
```

---

### Problem 8: Visualizing the Chain Rule

**Metadata**:
- **Video ID**: YG15m2VwSjA
- **Category**: Direct Visualization
- **Difficulty Level**: 3
- **Domain**: Calculus, Function Composition

**Problem Statement**:
Animate the chain rule using function composition. Show:
1. Two functions: g(x) and f(u), where y = f(g(x))
2. Visualize g: x → u mapping (e.g., parabola)
3. Visualize f: u → y mapping (e.g., exponential or sine)
4. Show how a small change dx in x produces:
   - A small change du in u (via g')
   - A small change dy in u (via f')
   - Overall: dy = f'(u) · g'(x) · dx
5. Animate the propagation of the infinitesimal change through both functions
6. Display the composition of derivatives: d/dx[f(g(x))] = f'(g(x)) · g'(x)

**Required Visual Events**:
- Function g plotted (weight: 0.7)
- Function f plotted (weight: 0.7)
- Input x and output y labeled (weight: 0.7)
- Small change dx shown (weight: 0.8)
- Change propagates through g (weight: 0.8)
- Change propagates through f (weight: 0.8)
- Composition formula displayed (weight: 0.7)

**Success Criteria**:
- Executability: ≥ 85%
- Alignment Score: ≥ 0.75 (all propagations present and ordered correctly)
- Coverage Score: ≥ 0.75

**Exemplar Annotation**:
```
Alignment check: Changes must propagate left-to-right (through g, then through f).
Incorrect order (f then g) is logical error → alignment drops.
```

---

### Problem 9: Integration and the Fundamental Theorem

**Metadata**:
- **Video ID**: rfG8ce4nNh0 (or 3b1b's calculus playlist)
- **Category**: Direct Visualization
- **Difficulty Level**: 3
- **Domain**: Calculus, Integration

**Problem Statement**:
Animate the Fundamental Theorem of Calculus, showing the relationship between differentiation and integration. Show:
1. A function f(x) plotted (e.g., parabola)
2. The derivative f'(x) shown below
3. Animate the area under f'(x) from 0 to x accumulating
4. Show a vertical line moving from left to right, sweeping the area
5. Display a graph of the accumulated area (which equals f(x))
6. Demonstrate: ∫₀ˣ f'(t) dt = f(x) − f(0)
7. Animate several values of x and show the correspondence

**Required Visual Events**:
- Function f visualized (weight: 0.8)
- Derivative f' visualized (weight: 0.8)
- Sweep/accumulation animated (weight: 0.9)
- Accumulated area displayed dynamically (weight: 0.8)
- Fundamental Theorem formula shown (weight: 0.7)

**Success Criteria**:
- Executability: ≥ 90%
- Alignment Score: ≥ 0.80 (all events present, sweep synchronized with accumulation)
- Coverage Score: ≥ 0.80

**Exemplar Annotation**:
```
Critical: Sweep and accumulation must be synchronized.
If area appears instantaneously without sweep animation, alignment drops.
```

---

### Problem 10: Taylor Series

**Metadata**:
- **Video ID**: 3d6DsjIBzJ4
- **Category**: Direct Visualization
- **Difficulty Level**: 4
- **Domain**: Calculus, Series

**Problem Statement**:
Animate the Taylor series expansion of a function (e.g., sin(x), e^x). Show:
1. The original function plotted in black
2. Start with the 0th-order term (constant): P₀(x) = f(0)
3. Progressively add terms: P₁(x), P₂(x), P₃(x), ...
4. Color-code each added term (e.g., red for linear, blue for quadratic, green for cubic)
5. Animate each partial sum being drawn on top of the function
6. Show numerical coefficients of the Taylor series
7. Display text explaining convergence: "Higher-order terms improve approximation"
8. Animate 5–8 terms, showing convergence toward the original function

**Required Visual Events**:
- Original function plotted (weight: 0.8)
- Partial sums P₀, P₁, ... added progressively (weight: 0.9)
- Each term colored and labeled (weight: 0.8)
- Approximation improves visually with each term (weight: 0.8)
- Convergence demonstrated (weight: 0.8)

**Success Criteria**:
- Executability: ≥ 80%
- Alignment Score: ≥ 0.75 (all terms added in order, convergence apparent)
- Coverage Score: ≥ 0.80

**Exemplar Annotation**:
```
Alignment check: Terms must be added in sequence (increasing degree).
If all terms are shown simultaneously, pedagogical value is lost → alignment drops.
```

---

### Problem 11: The Hairy Ball Theorem

**Metadata**:
- **Video ID**: BHdbsHFs2P0
- **Category**: Direct Visualization
- **Difficulty Level**: 5
- **Domain**: Topology, Vector Fields

**Problem Statement**:
Animate the Hairy Ball Theorem: a continuous vector field on a 2-sphere must have at least one point where the vector is zero (a "bald spot"). Show:
1. A 3D sphere rendered with rotation/camera movement
2. A vector field drawn on the sphere (many small arrows pointing tangent to the surface)
3. Attempt to orient all vectors continuously (smoothly, without discontinuities)
4. Show that this is impossible: at least one point must have zero vector (bald spot)
5. Animate the "combing" process, showing where tangency requirements fail
6. Highlight the bald spot with special visual marker

**Required Visual Events**:
- Sphere rendered in 3D (weight: 0.9)
- Vector field visualized (many vectors on surface) (weight: 0.9)
- Combing/alignment attempted (animating vector orientation changes) (weight: 0.8)
- Discontinuity or impossibility evident (weight: 0.8)
- Bald spot highlighted (weight: 0.7)

**Success Criteria**:
- Executability: ≥ 70%
- Alignment Score: ≥ 0.65 (complex concept; some loss of detail expected)
- Coverage Score: ≥ 0.60

**Exemplar Annotation**:
```
Alignment check: The core theorem is about impossibility of global continuity.
Animation must show attempted combing and eventual failure.
If field is just static, alignment is very low.
```

---

### Problem 12: The Windmill Problem

**Metadata**:
- **Video ID**: M64HUIJFTZM
- **Category**: Drift-Sensitive, Multi-Scene
- **Difficulty Level**: 4
- **Domain**: Geometry, Combinatorics

**Problem Statement**:
Animate the windmill problem: given n points in general position, a rotating line sweeps continuously and passes through at least two points at all times. Show:
1. A set of n points (e.g., 5–8) scattered randomly
2. A line starting horizontal, passing through two points
3. The line rotates continuously (angular velocity constant or nearly constant)
4. Whenever the line is about to lose a point, it pivots to pick up a new point (to maintain 2-point contact)
5. Animate the pivoting process
6. Show the line rotating through a full 180°, demonstrating that the pattern repeats
7. Visualize the "windmill" motion dynamically

**Required Visual Events**:
- Points visualized (weight: 0.8)
- Line rendered and passes through two points (weight: 0.9)
- Line rotates (weight: 0.9)
- Pivot events occur at correct times (weight: 0.8)
- Line maintains 2-point contact (weight: 0.8)
- 180° rotation completed (weight: 0.7)

**Success Criteria**:
- Executability: ≥ 75%
- Alignment Score: ≥ 0.70 (complex timing; some events may be omitted)
- Coverage Score: ≥ 0.65

**Exemplar Annotation**:
```
Alignment check: Pivots must occur at geometrically correct moments (when current point leaves the line).
If pivots occur randomly or timing is off, alignment drops.
```

---

## 5. Evaluation Protocol

### 5.1 Workflow

1. **Code Generation**: Prompt an LLM with problem statement.
2. **Execution**: Run generated code in Manim CE (or GL, as specified).
3. **Metric Collection**:
   - **Executability**: Does code run? (binary yes/no)
   - **Version-Conflict Errors**: Any deprecated imports? (binary yes/no)
   - **Alignment Score**: Manual review (or automated heuristic if available)
   - **Coverage Score**: Check for labels, axes, visual elements
4. **Aggregation**: Compute Pass@1 (% of attempts that pass Executability), aggregate Alignment and Coverage.

### 5.2 Human Evaluation Protocol

For Alignment and Coverage scores, we employ structured human evaluation:

**Reviewer Instructions**:
1. Watch the rendered animation
2. Check off each "Required Visual Event" as present/absent
3. Note timing: are events synchronized correctly?
4. Assess pedagogical clarity: does animation explain the concept?
5. Provide Alignment Score (0.0–1.0) and Coverage Score (0.0–1.0)

**Disagreement Resolution**:
- Two independent reviewers score each output
- If disagreement > 0.15, a third reviewer breaks the tie
- Report inter-rater agreement (Krippendorff's α or Cohen's κ)

---

## 6. Preliminary Results (Pilot Study)

**Setup**:
- **Model**: GPT-4o, Claude 3.5 Sonnet
- **Prompting**: Zero-shot (single problem prompt, no examples)
- **Manim Version**: CE
- **N**: 3 trials per model × 12 problems = 72 runs

**Results Summary**:

| Problem | Executability (GPT-4o) | Executability (Claude) | Avg Alignment | Avg Coverage |
|---------|------------------------|------------------------|---------------|--------------|
| 1 (Colliding Blocks) | 67% | 67% | 0.52 | 0.58 |
| 2 (Gradient Descent) | 100% | 100% | 0.73 | 0.82 |
| 3 (Convolution) | 0% | 33% | – | – |
| 4 (Eigenvectors) | 33% | 33% | 0.40 | 0.50 |
| 5 (Determinant) | 100% | 100% | 0.85 | 0.88 |
| 6 (CLT) | 0% | 33% | – | – |
| 7 (Medical Test) | 100% | 100% | 0.78 | 0.85 |
| 8 (Chain Rule) | 67% | 67% | 0.60 | 0.68 |
| 9 (Integration) | 0% | 33% | – | – |
| 10 (Taylor) | 33% | 33% | 0.35 | 0.42 |
| 11 (Hairy Ball) | 0% | 0% | – | – |
| 12 (Windmill) | 0% | 0% | – | – |

**Key Observations**:
1. **Simple problems** (Determinant, Medical Test): High executability (100%) and alignment (0.8+)
2. **Complex problems** (Convolution, CLT, Integration, Hairy Ball): Low executability (0–33%), suggesting API misunderstandings or missing pedagogical elements
3. **Drift events**: Problems requiring precise timing (Gradient Descent, Windmill) show lower alignment than coverage, indicating temporal synchronization issues
4. **Version conflicts**: No GL-specific syntax detected in this pilot (both models avoided GL references)

---

## 7. Discussion

### 7.1 Why ManiBench Matters

Existing benchmarks (HumanEval, APPS) measure whether code produces correct *output*. ManiBench measures whether code produces correct *understanding*. This is critical for educational tools, where a silent failure (wrong animation) is worse than a loud failure (runtime error).

### 7.2 Limitations and Future Work

1. **Alignment Scoring**: Currently manual. Future work should explore automatic alignment detection (e.g., via AST analysis or video frame comparison).
2. **Pedagogical Validation**: We do not yet validate whether animations actually teach the concept. User studies with students could improve this.
3. **Manim API Coverage**: As Manim evolves, benchmarks should be versioned and updated. The 145 documented GL→CE incompatibilities provide a starting point for automated version-conflict detection.
4. **Scalability**: Moving from 12 to 150+ problems requires annotation infrastructure and community contribution.
5. **Reference Code Utilization**: The ~53,000 lines of analyzed reference code could enable fine-tuning studies or retrieval-augmented generation experiments.

### 7.3 Broader Impact

ManiBench can be used to:
- Evaluate LLM educational content generation
- Develop better prompting strategies for animation code
- Identify systematic failure modes (e.g., "models struggle with temporal synchronization")
- Drive research into improving Manim API adoption in LLMs
- Benchmark version-aware code generation using the 145 documented GL→CE incompatibilities
- Enable retrieval-augmented generation (RAG) experiments using the reference code analysis

---

## 8. Conclusion

We introduce **ManiBench**, a specialized benchmark for evaluating Manim code generation. By formalizing metrics for syntactic correctness, version compliance, visual-logic alignment, and pedagogical coverage, ManiBench moves beyond simple test-case evaluation to assess whether generated animations actually communicate mathematical concepts.

The 12-problem pilot dataset, backed by comprehensive reference code analysis of ~53,000 lines of original 3Blue1Brown source code, demonstrates both the opportunities (simple concepts: ~80% alignment) and challenges (complex temporal reasoning: ~40% alignment) in automated animation generation. With planned expansion to 150–200 problems, ManiBench will serve as a foundational resource for advancing LLM-driven educational content creation.

---

## References

[To be populated with citations to Manim, HumanEval, MBPP, 3Blue1Brown videos, etc.]

---

## Appendix: Problem Annotation Template

```yaml
problem_id: "MB-001"
title: "Colliding Blocks Compute π"
video_id: "6dTyOl1fmDo"
category: "drift-sensitive, multi-scene"
difficulty_level: 4
domain: "physics, numerics"
raw_code_status: "collected"
raw_code_path: "raw_code/colliding_blocks_v2/"
raw_code_files: ["blocks.py", "supplements.py", "grover.py"]

prompt: |
  [Full natural language problem statement]

required_visual_events:
  - id: "evt_collision"
    description: "Blocks collide and collision counter increments"
    weight: 0.8
    timing: "during_collision"
    is_critical: true
  - id: "evt_velocity_update"
    description: "Velocity vectors update after collision"
    weight: 0.7
  - id: "evt_final_count"
    description: "Final collision count displayed"
    weight: 0.6

coverage_requirements:
  - "Collision counter visible"
  - "Velocity labels/vectors shown"
  - "Mathematical annotations present"

reference_code_analysis:
  framework: "manim_gl"
  total_lines: 2193
  scene_classes:
    - class_name: "BlocksAndWallExample"
      type: "main_scene"
      description: "..."
      key_methods: ["construct", "..."]
  visual_techniques:
    - "Phase-space circle for conservation laws"
  manim_api_patterns:
    updaters_used: ["add_updater"]
    animation_types: ["Transform", "Write"]
    custom_classes: ["Block", "Wall"]

version_conflict_notes:
  original_framework: "manim_gl"
  target_framework: "manim_ce"
  known_incompatibilities:
    - "manim_imports_ext → from manim import *"
    - "CONFIG dict → __init__ parameters"

success_criteria:
  executability_min: 0.70
  alignment_score_min: 0.70
  coverage_score_min: 0.75

exemplar_notes: |
  [Guidance for human evaluators]

reference_implementation_notes: |
  [Hidden from LLM; for paper authors only]
```

---

**Document Version**: 1.1 Pilot  
**Schema Version**: 2.0  
**Last Updated**: 2026-02-18  
**Status**: Pilot dataset complete with full reference code analysis. Ready for evaluation.
**HuggingFace**: [nabin2004/ManiBench](https://huggingface.co/datasets/nabin2004/ManiBench)
