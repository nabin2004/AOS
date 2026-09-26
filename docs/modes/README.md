# AOS Agentic Modes — Index & Taxonomy

This directory contains formal technical specifications for each agentic animation mode implemented in the **Agentic Orchestration System (AOS)**. For a comprehensive description of the top-level dispatch router, shared Docker execution containers, static Pyright LSP verification, and system glossary, see the [Architecture Overview](../architecture/overview.md).

---

## Mode Taxonomy & Overview

AOS separates pedagogical animation generation into distinct modes based on conceptual density, spatial dynamics, computational requirements, and presentation formats.

| Mode | Internal Slug | Paradigm | Intermediate Representation (IR) | Primary Output | Specification Document |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Slides Mode** | `"slide"` | Discrete Presentation | `scenes.md` (Slide sections) | `Scene` (Video) | [slides-mode.md](slides-mode.md) |
| **Animate Mode** | `"animation"` | Fluid 3B1B Motion | `scenes.md` (Narrative arc) | `Scene` / `ThreeDScene` | [animate-mode.md](animate-mode.md) |
| **Science-Viz Mode** | `"scivis"` | Computational Bridge | `scenes.md` (`get_data()` spec) | `Scene` + Data Provenance | [science-viz-mode.md](science-viz-mode.md) |
| **Marp Mode** | `"marp"` | Declarative AST Deck | `presentation.marp.md` | `Scene` or `manim-slides` | [marp-mode.md](marp-mode.md) |
| **Keyframe Pipeline** | `"keyframe"` | State-Machine Pacing | `teaching_script.json` | `VoiceoverScene` (AV Mux) | [keyframe-mode.md](keyframe-mode.md) |
| **Cinematic Pipeline** | `"cinematic"` | High-Production Visuals| Annotated `TeachingScript` | `ThreeDScene` + Audio | [cinematic-mode.md](cinematic-mode.md) |

---

## Summaries of Implemented Modes

### 1. [Slides Mode (`slides-mode.md`)](slides-mode.md)
Slides Mode synthesizes structured, presentation-style educational animations designed for learners who require clear visual chunking and reading time. The mode organizes content into discrete, self-contained slides encapsulated within Manim `VGroup` containers, introducing elements sequentially with entrance animations (`Write`, `FadeIn`), holding the frame for 2 to 4 seconds, and performing clean transitions using `FadeOut` or `ReplacementTransform` to eliminate visual clutter.

### 2. [Animate Mode (`animate-mode.md`)](animate-mode.md)
Animate Mode is the standard mathematical animation engine modeled after 3Blue1Brown pedagogical conventions. It prioritizes fluid continuous motion, dynamic geometric proofs, and intuitive concept evolution. The mode leverages `ValueTracker` variables, dynamic updaters (`always_redraw()`), mathematical morphs (`Transform`), and continuous camera translations (`MovingCameraScene`) to visualize calculus, linear algebra, and coordinate transformations.

### 3. [Science-Viz Mode (`science-viz-mode.md`)](science-viz-mode.md)
Science-Viz Mode bridges high-level animation synthesis with scientific Python computing libraries, including NumPy, SciPy, Astropy, and NetworkX. It is designed for domain-specific simulations such as celestial orbits, biochemical molecular models, differential dynamics, and graph networks. The mode strictly decouples data calculation from animation rendering by mandating an isolated `get_data()` function with robust fallback datasets and transparent data-provenance tags.

### 4. [Marp to Manim Mode (`marp-mode.md`)](marp-mode.md)
Marp Mode operationalizes a declarative slide-to-animation workflow by treating Marp CommonMark Markdown as a structured visual plan format and ManimCE as a deterministic compiler target. Rather than attempting open-ended CSS translation, the mode maps Markdown AST tokens to a fixed 6-archetype spatial layout vocabulary (`title`, `bullets`, `two-col`, `code-focus`, `math-focus`, `quote`). It supports instant sub-millisecond AST code generation targeting both static video files and interactive `manim-slides` presentations.

### 5. [Keyframe Pipeline Mode (`keyframe-mode.md`)](keyframe-mode.md)
Keyframe Mode is the autonomous multi-agent pipeline's primary operational engine for synchronized audio-visual lectures. By modeling animations as a series of discrete visual keyframe hold states bound directly to spoken voiceover segments (`with self.voiceover(...) as tracker:`), the mode guarantees audio-visual synchronization without manual frame-by-frame timing adjustments, generating reliable long-form educational videos.

### 6. [Cinematic Director Mode (`cinematic-mode.md`)](cinematic-mode.md)
Cinematic Director Mode activates specialized high-aesthetic visual parameters for complex dynamic systems, such as chaotic strange attractors (e.g., the Lorenz attractor), quantum wavefunctions, and orbital n-body physics. It enforces a signature deep dark aesthetic (`#050814`), velocity gradient color interpolation, multi-axis ambient camera rotations in `ThreeDScene`, and numerical Runge-Kutta simulation recipes.
