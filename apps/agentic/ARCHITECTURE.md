# AOS Agentic Architecture: Multi-Agent Semantic Router (v2)

## The Core Problem: LLMs vs. Deep OOP Hierarchies
Programmatic video generation using Manim Community edition poses a unique challenge for Large Language Models (LLMs). Manim is built on a deep, imperative Object-Oriented Programming (OOP) hierarchy consisting of over 240 nodes and abstract classes. 

LLMs inherently struggle with deep inheritance trees. When fed the raw Manim architecture, they suffer from cognitive overload—hallucinating methods, attempting to instantiate abstract base classes (like `Mobject` or `Animation`), and fundamentally failing at 2D spatial reasoning (e.g., placing text completely off-screen). 

**For 7B models (Qwen Coder), these problems are catastrophic.** A 7B model has ~4K–8K effective reasoning tokens, limited spatial reasoning, fragile long-context fidelity, and a strong tendency to copy surface patterns from its prompt.

## The Solution: Inverting the Paradigm
The **AOS (Agentic Orchestration System)** implements a **Multi-Agent Semantic Router** enforced by `PydanticAI`. Instead of teaching the AI the entire OOP graph, we break the video generation process into a highly specialized assembly line. **The AI is treated as a categorical decision engine** (enum picker + slot filler), while deterministic Python handles the rigorous math, spatial layouts, and code generation.

### Design Principle for 7B Models
> Every time you ask the model to emit raw Python (args strings, lambda expressions, code snippets), you're fighting its weaknesses. Every time you ask it to pick from a menu, fill a structured field, or follow a pattern, you're playing to its strengths.

---

## 1. Knowledge Extraction & Validation Layer
**Files:** `extract_pdf_graphs.py`, `validation.py`, `manim_leaf_roster.json`

To prevent hallucinations, we extracted the literal inheritance graphs directly from the official Manim Community reference manual. 
- We filtered out all abstract base classes (e.g., `VMobject`, `CoordinateSystem`) into a `manim_leaf_roster.json`.
- The Pydantic validation layer restricts the LLM's output `Literal` types strictly to a **Core catalog of 27 mobjects + 23 animations** (the classes needed for 95% of educational videos).
- If an agent tries to instantiate an abstract class, the Pydantic schema physically traps the error and forces a retry.

### Core Catalogs (Tiered for 7B Reliability)
The full roster has 211+ classes. A 7B model struggles to pick from 211 options. The Core catalogs contain only the most common classes:
- **Core Mobjects (27):** Text, Title, MathTex, Axes, Circle, Dot, Arrow, VGroup, FunctionGraph, etc.
- **Core Animations (23):** Create, Write, FadeIn, FadeOut, ReplacementTransform, Indicate, etc.

---

## 2. The Multi-Agent Assembly Line (`pipeline.py`)
The pipeline maps the four core branches of Manim (Scenes, Mobjects, Animations, Cameras) into isolated agent responsibilities:

### A. Architect (Deterministic — No LLM)
- **Role:** Determines the macro container for the lecture.
- **Implementation:** Keyword heuristic (not an LLM call). Saves the 7B model's token budget.
- **Output:** `SceneEnvironment` — scene class, camera, plugins, background color.
- **Logic:** "3D" → `ThreeDScene`, "zoom" → `MovingCameraScene`, default → `Scene`.

### B. Prop Master Agent (Structured Output)
- **Role:** Allocates the visual elements required for the pedagogical prompt.
- **Output:** `SceneMobjectRoster` — a flat list of `ManimMobject` objects.
- **Key v2 Change:** `initial_args: str` (freeform Python) replaced with `MobjectConfig` (typed slots):
  - `config.tex` for LaTeX strings (validated for balanced braces)
  - `config.x_range`, `config.y_length` for Axes dimensions
  - `config.function_expr` for FunctionGraph expressions
  - `config.color`, `config.fill_opacity` for styling
- **VGroup Support:** `group_name` field groups related objects (auto-assembled by the Code Assembler).
- **System Prompt:** Few-shot examples (2 concrete input→output examples) instead of exhaustive 200+ class catalogs.

### C. Layout Critic (Deterministic Spatial Engine)
**File:** `layout_critic.py`
- **Role:** Resolves spatial blindness. Because LLMs are terrible at predicting `[x, y, z]` coordinates, this step is handled by a deterministic, non-LLM Python script.
- **v2 Change:** Size estimation reads from typed `MobjectConfig` (e.g., Axes `x_length`/`y_length`) for more accurate AABB approximation.
- **Implementation:**
  - **3-Zone Layout Enforcement:** Automatically partitions the 16:9 canvas into `TOP_BANNER`, `HERO_CANVAS`, and `WORKING_MARGIN`.
  - **Collision & Clipping:** AABB intersection detection with orthogonal relaxation. Bounds clamping to safe 16:9 frame.
  - **Relative Anchoring:** Stacks items using standardized buffs and anchors multi-line math by left edge.

### D. Choreographer Agent (Structured Output)
- **Role:** Maps out the temporal transitions and visual actions.
- **v2 Schema Improvements:**
  - `target_variables: list[str]` — supports grouped animations (multiple targets → `AnimationGroup`/`LaggedStart`)
  - `source_variable` — required for `ReplacementTransform`/`TransformMatchingTex`
  - `rate_func` — animation easing (smooth, there_and_back, linear, etc.)
  - `wait_after` — seconds to pause after animation (critical for watchable output)
  - `cleanup_before` — variables to `FadeOut` before this animation (prevents screen clutter)
  - `shift_direction` — directional entry for `FadeIn`/`FadeOut`
  - `lag_ratio` — stagger ratio for `LaggedStart` with multiple targets
- **Cross-Validation:** `validate_choreography_against_roster()` checks all variable references exist before assembly.

### E. Code Assembler (Deterministic)
- **Role:** Compiles the final Manim CE Python script deterministically.
- **v2 Changes:**
  - Uses `ManimMobject.to_constructor_call()` — typed config → correct Python constructors
  - Auto-generates `VGroup()` declarations from `group_name` fields
  - Handles transforms: `ReplacementTransform(source, target)`
  - Handles grouped animations: multiple targets → `AnimationGroup`/`LaggedStart`
  - Emits `self.wait()` calls for pacing
  - Emits cleanup `FadeOut()` calls before new sections
  - Applies `rate_func` to `self.play()` kwargs

### F. Repair Loop (Syntax Check)
- **Role:** Catches Python syntax errors before the code reaches the Manim renderer.
- **Implementation:** `compile(code, "<scene>", "exec")` + error routing to the responsible agent.
- **Diagnoses:** LaTeX errors → Prop Master, undefined variables → Choreographer, positioning errors → Layout Critic.

---

## 3. Sandboxed Execution Environment (`manim.cfg`)
- **Workspace Sandboxing:** All artifacts routed to `workspace/` to prevent Git pollution.
- **Headless Mode:** Preview windows and verbose logging suppressed.
- **Stateful Caching:** Enabled for iterative Repair loops — unchanged animations load from cache.

---

## 4. What a 7B Qwen Model Can/Cannot Do

### ✅ Reliable
- Pick from a small enum (5–30 choices) — Scene type, Mobject class, Animation class
- Fill structured fields — variable_name, purpose, run_time, color
- Follow 2-3 few-shot examples
- Produce simple LaTeX — `a^2 + b^2 = c^2`, `\int_0^1 f(x)\,dx`

### ❌ Unreliable (Offloaded to Deterministic Code)
- Write correct Python code as a string — replaced by `MobjectConfig`
- Reason about spatial coordinates — handled by Layout Critic
- Maintain variable name consistency — enforced by cross-validation
- Pick from 200+ options — constrained to Core 27/23
- Plan temporal pacing — structured by `wait_after`, `cleanup_before`
