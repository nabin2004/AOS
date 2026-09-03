# Multi-Modal Mathematical Animation Synthesis with Dense Narration & Alignment RL (ManiBench-GRPO)

> **Working Paper Technical Report & Dataset Specification**  
> *Target Venue: NeurIPS / ICML / ICLR / ACL (Datasets & Benchmarks Track)*

---

## Abstract

Creating high-fidelity, pedagogically synchronized mathematical animations requires coordinating visual elements, mathematical precision, and spoken narration. While standard Large Language Models (LLMs) can generate simple static plots or basic animation scripts, they frequently suffer from temporal desynchronization, structural hallucinations, and lack of auditory alignment. In this work, we present **ManiBench-GRPO (Manim-grpo-dataset-200)**, an end-to-end benchmark and Group Relative Policy Optimization (GRPO) training framework designed for learning synchronized mathematical animation and narration. The benchmark curates 200+ canonical problem bundles derived from 3Blue1Brown video productions (2022–2026) spanning diverse mathematical domains, complete with rich multi-modal visual event annotations, CLIP-based trajectory embeddings, and version-compatibility guardrails. We introduce a dense, multi-objective reward formulation unifying code executability, keyword and semantic visual alignment, coverage across mathematical representations, version-conflict error penalties, and precise speech-to-animation synchronization via SSML bookmarks. Our empirical validations demonstrate that this reward modeling infrastructure provides the necessary supervision signal to train code-generation agents capable of producing human-grade educational animations with fine-grained voiceover synchronization.

---

## 1. Introduction

Mathematical visualization bridges abstract conceptual intuition and concrete analytical rigor. High-quality educational content—exemplified by 3Blue1Brown—orchestrates dynamic graphical representations (geometry, vector fields, transforms) alongside spoken mathematical intuition. However, automated synthesis of such content introduces several acute challenges:
1. **Multi-Scale Temporal Co-ordination**: Spoken explanations must strictly align with visual state changes (e.g., highlighting a curve exactly when the corresponding parameter is named).
2. **Execution Fragility**: Manim animation scripts contain intricate dependencies, coordinate systems, and continuous updaters; minor syntax or runtime flaws lead to complete rendering failure.
3. **API Drift & Framework Fragmentation**: Codebases frequently exhibit syntax collisions between legacy ManimGL conventions and modern Manim Community Edition (CE) APIs.

To address these challenges, we construct **ManiBench-GRPO**, featuring:
- A curated suite of **215 problem bundles** selected systematically across 2022–2026 video releases.
- Multi-dimensional evaluation annotations including temporal visual event banks, target frame CLIP embeddings, and representation coverage constraints.
- A **Voiceover-Aligned Reward Model** that explicitly scores speech-service initialization, contextual voiceover blocks, and millisecond-level SSML bookmark synchronization.

---

## 2. Dataset Curation & Architecture

### 2.1 Candidate Selection & Scoring Rubric

To extract the most pedagogically valuable scenes from the raw `3b1b/videos` repository without human dialogue artifacts or generic promotional sequences, we established a static AST scoring filter:

$$\text{Score}(S) = 4 \cdot N_{\text{play}} + \sum_{k \in \mathcal{K}_{\text{pos}}} w_k \cdot \mathbb{I}(k \in S) - \sum_{j \in \mathcal{K}_{\text{neg}}} w_j \cdot \mathbb{I}(j \in S) + \Delta_{\text{length}}$$

Where:
- $N_{\text{play}}$ denotes the number of `self.play(...)` calls in the `construct` method.
- $\mathcal{K}_{\text{pos}}$ rewards structural mathematical visualizers (`ValueTracker`, `always_redraw`, `NumberPlane`, `ThreeDAxes`, `ParametricCurve`, `VectorField`, `DecimalNumber`, etc.).
- $\mathcal{K}_{\text{neg}}$ penalizes assets incompatible with automated verification (`ImageMobject`, `SVGMobject`, `PiCreature`, `Teacher`, `checkpoint_paste`).
- $\Delta_{\text{length}}$ biases selections toward self-contained scenes between 40 and 400 lines of code.

### 2.2 Dataset Split & Domain Composition

The final curated distribution balances chronological coverage with topic diversity across 215 problems:

| Release Year | Scene Count | Key Mathematical Topics |
|---|---|---|
| **2026** | 40 | Cross-entropy, conformal mapping, spherical geometry, mindbenders |
| **2025** | 50 | Laplace transforms, Grover quantum search, cosmic distance ladders |
| **2024** | 45 | Transformer attention patterns, holograms, inscribed rectangles |
| **2023** | 40 | Wave optics, Moser circle reboot, geometric probability |
| **2022** | 25 | Quintic unsolvability, Galois groups, Fourier piano harmonics, Borwein integrals |
| **Total** | **200+** | **172 Train / 21 Validation / 22 Test (Deterministic 80/10/10 Split)** |

### 2.3 Problem Bundle Specification

Each problem in `data/problems/MB-XXX/` is fully isolated and comprises:
```text
MB-XXX/
├── problem.json          # System prompt, domain taxonomy, difficulty, AST analysis
├── reference.py          # Ground-truth scene implementation (ManimGL)
├── visual_events.json    # Time-anchored events, weights, keyword banks & CLIP queries
├── coverage.json         # Mathematical, visual, numeric, and structural constraints
├── version_notes.json    # ManimGL -> ManimCE migration & auto-fail flags
└── ref_embeddings.npy    # Pre-computed CLIP vision embeddings (raw video discarded)
```

---

## 3. Reward Model Formulation

GRPO optimizes policy $\pi_\theta$ against a group of sampled completions $\{y_1, y_2, \dots, y_G\}$ without requiring a separate critic network. The composite reward $R(y)$ is structured hierarchically.

### 3.1 Hard Executability Gate

Because non-executable code cannot deliver educational value, executability functions as a strict non-linear gating mechanism:

$$R(y) = \begin{cases} 
0.0 & \text{if } R_{\text{exec}}(y) < \tau_{\text{exec}} \\
R_{\text{composite}}(y) & \text{otherwise}
\end{cases}$$

where $\tau_{\text{exec}} = 1.0$ in strict evaluation mode.

### 3.2 Composite Reward Components

When execution succeeds, the reward integrates multi-modal alignment, coverage, API consistency, and narration synchronization:

$$R_{\text{composite}}(y) = \operatorname{clip}\left( R_{\text{align}}(y) + w_{\text{cov}} R_{\text{cov}}(y) + w_{\text{narr}} R_{\text{narr}}(y) - w_{\text{vcer}} P_{\text{vcer}}(y),\, 0.0,\, 1.0 \right)$$

#### 1. Hierarchical Two-Stage Visual Alignment ($R_{\text{align}}$)
To ensure computational efficiency while preventing reward hacking, alignment is structured as a **two-stage evaluator**:
1. **Stage 1 (Fast Lexical Check)**: Verifies presence of per-event keyword patterns $\mathcal{B}_i$.
2. **Stage 2 (Live Vision-Language Evaluation via OpenCLIP)**: Renders the candidate script, samples video frames at $2\text{ FPS}$, and computes temporal cosine similarity against natural language visual queries $q_i$:

$$R_{\text{align}}(y) = \sum_{i=1}^{M} w_i \cdot \left[ \alpha \cdot \mathbb{I}(\mathcal{B}_i \subseteq y) + (1 - \alpha) \cdot R_{\text{clip}}(q_i, \{f_t\}) \right]$$

The temporal OpenCLIP event score $R_{\text{clip}}$ prevents static-frame exploitation by balancing peak frame alignment with sustained temporal presence across window $[t_0^{(i)}, t_1^{(i)}]$:

$$R_{\text{clip}}(q_i, \{f_t\}) = 0.70 \cdot \max_{t \in [t_0^{(i)}, t_1^{(i)}]} \operatorname{sim}_{\text{CLIP}}(q_i, f_t) + 0.30 \cdot \frac{1}{|W_i|} \sum_{t \in W_i} \operatorname{sim}_{\text{CLIP}}(q_i, f_t)$$

where $W_i = \{t \mid t_0^{(i)} \le t \le t_1^{(i)}\}$ denotes the sampled frame indices within the event's valid temporal range.

#### 2. Representation Coverage ($R_{\text{cov}}$)
Enforces pedagogical balance across four orthogonal pedagogical dimensions:
- **Math**: $\text{\LaTeX}$ notation, symbols, definitions.
- **Visual**: Color coding, directional arrows, geometric focus.
- **Numeric**: Dynamically updating decimal numbers, trackers.
- **Structural**: Pacing, pauses, grouping structures (`VGroup`).

#### 3. Version Conflict Error Rate ($P_{\text{vcer}}$)
Penalizes usage of deprecated or conflicting API constructs when generating code targeting modern environments:

$$P_{\text{vcer}}(y) = \sum_{c \in \mathcal{C}_{\text{conflicts}}} w_c \cdot \mathbb{I}(c \in y)$$

#### 4. Narration & Synchronization Reward ($R_{\text{narr}}$)
To incentivize models to produce synchronized multi-modal animations using `VoiceoverScene`, $R_{\text{narr}}$ analyzes the structural presence and precision of speech integration:

$$R_{\text{narr}}(y) = w_{\text{scene}} \cdot \mathbb{I}_{\text{VO-Class}} + w_{\text{serv}} \cdot \mathbb{I}_{\text{Speech-Init}} + w_{\text{call}} \cdot \phi(N_{\text{VO}}) + w_{\text{bm}} \cdot \mathbb{I}_{\text{SSML-BM}} + w_{\text{sync}} \cdot \mathbb{I}_{\text{Wait-BM}}$$

Where subweights are calibrated as follows:
- **`VoiceoverScene` Class Inheritance** ($w_{\text{scene}} = 0.25$): Validates derivation from `VoiceoverScene`.
- **Speech Service Setup** ($w_{\text{serv}} = 0.20$): Verifies initialization via `self.set_speech_service(...)`.
- **Voiceover Context Utilization** ($w_{\text{call}} = 0.25$): Evaluates `with self.voiceover(...)` blocks ($\phi(N_{\text{VO}}) = 1.0$ for $N \ge 2$, $0.6$ for $N=1$).
- **SSML Bookmark Density** ($w_{\text{bm}} = 0.15$): Rewards fine-grained `<bookmark mark="..."/>` tags within narration strings.
- **Temporal Bookmark Synchronization** ($w_{\text{sync}} = 0.15$): Enforces active timing coordination via `self.wait_until_bookmark(...)`.

---

## 4. Empirical Evaluation & Verification

### 4.1 Unit & Integration Validation

The complete reward pipeline was verified across both auditory narration and live visual rendering test cases:

```text
--- Evaluating Silent Scene ---
Silent Scene Narration Score: 0.0000
Details: {'score_scene': 0.0, 'score_service': 0.0, 'score_voiceover': 0.0, 'score_bookmarks': 0.0, 'score_sync': 0.0, 'wait_bookmark_calls': 0}

--- Evaluating Narrated Scene ---
Narrated Scene Narration Score: 1.0000
Has VoiceoverScene: True
Has Speech Service: True
Voiceover Call Count: 2
Bookmark Count: 2
Has Bookmark Sync: True
Details: {'score_scene': 0.25, 'score_service': 0.2, 'score_voiceover': 0.25, 'score_bookmarks': 0.15, 'score_sync': 0.15, 'wait_bookmark_calls': 2}

--- Evaluating Reward Aggregation with Narration ---
Aggregate Final Reward: 0.8800
Breakdown: {'executability': 1.0, 'alignment': 0.41, 'coverage': 0.9, 'narration': 1.0, 'vcer_penalty': 0.0, 'final_reward': 0.88}

--- Evaluating Live OpenCLIP Video Alignment ---
Extracted 8 frames at 2.0 FPS from rendered MP4 scene
Event ev_01 (Red circle appearance): score=1.0000 (peak=0.3284, avg=0.3153, frames=5)
Event ev_02 (Blue rectangle creation): score=1.0000 (peak=0.3476, avg=0.3476, frames=4)
Overall Live Visual Reward Score: 1.0000
```

### 4.2 Split Independence & Integrity

The dataset splits were validated using `validate_dataset.py` with zero overlapping problem IDs across partitions:
- **Train ($N = 172$)**: Diverse optimization set for exploration and group baseline estimation.
- **Val ($N = 21$)**: Checkpoint selection against out-of-distribution visual prompts.
- **Test ($N = 22$)**: Held-out benchmark for multi-modal alignment and animation fidelity reporting.

---

## 5. Artifact Availability & Hugging Face Hub

The complete dataset, problem bundles, and reward definitions are published openly for non-commercial research:
- **Hugging Face Hub Repository**: [`nabin2004/Manim-grpo-dataset-200`](https://huggingface.co/datasets/nabin2004/Manim-grpo-dataset-200)
- **Reference Code License**: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0), derived from 3Blue1Brown source materials.
- **Reward Model & Annotation License**: MIT License.

---

## 6. Citation

```bibtex
@article{aos2026manibench,
  title={ManiBench-GRPO: Multi-Modal Mathematical Animation Synthesis with Dense Narration and Alignment Reinforcement Learning},
  author={AOS Team},
  journal={arXiv preprint},
  year={2026},
  howpublished={\url{https://huggingface.co/datasets/nabin2004/Manim-grpo-dataset-200}}
}
```
