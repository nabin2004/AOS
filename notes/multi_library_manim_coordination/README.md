# Multi-Library Manim Coordination for SFT Dataset Generation
## Strategic Playbook: Manim + NumPy/SciPy + Synchronized Voiceover

This repository folder documents the architectural strategy, engineering patterns, dataset taxonomy, and automated collection pipeline for fine-tuning LLMs on **Multi-Library Scientific Manim Animations**.

---

## 1. Executive Summary & Supervisor Direction

During final-year research by Nabin Oli, initial fine-tuning attempts on smaller coding models (Gemma-4, Qwen2.5-Coder-7B, Qwen3-8B) struggled when generating animations that required coordinating **Manim** with scientific computing libraries (like **SciPy**'s `solve_ivp` or `minimize`).

### Key Guidance from Supervisor Nathan:
1. **Halt Continuous Pretraining (CPT)**: CPT requires billions of tokens and huge GPU resources (draining personal budgets on RunPod/Colab) without solving the precision alignment needed for code.
2. **Quality & Reasoning Over Volume**: 300–500 meticulously structured, Chain-of-Thought (CoT) guided pairs will drastically outperform thousands of noisy, uncurated scripts.
3. **Decouple Mathematics from Rendering**: Train the model to compute dense numerical solutions *upfront*, bridging them into Manim using the **Array-Slice Pattern** (`ValueTracker` + Updaters).
4. **Synchronize Voiceover via Context Managers**: Bind visual run times directly to `manim-voiceover` durations (`run_time=tracker.duration`).

---

## 2. Directory Contents

| Document | Purpose |
|----------|---------|
| [README.md](file:///c:/Users/nabin/Desktop/myall/AOS/notes/multi_library_manim_coordination/README.md) | High-level overview, supervisor principles, and index. |
| [conversation_with_gemini.md](file:///c:/Users/nabin/Desktop/myall/AOS/notes/multi_library_manim_coordination/conversation_with_gemini.md) | Verbatim archival record of Nabin's email to Nathan, supervisor reply, Manim breakdown, and Gemini technical dialogue. |
| [gotchas_and_best_practices.md](file:///c:/Users/nabin/Desktop/myall/AOS/notes/multi_library_manim_coordination/gotchas_and_best_practices.md) | Comprehensive catalogue of LLM failure modes (SciPy in updaters, audio stacking, MRO ordering, 2D/3D camera conflicts, zero-length indexing). |
| [scientific_taxonomy_matrix.md](file:///c:/Users/nabin/Desktop/myall/AOS/notes/multi_library_manim_coordination/scientific_taxonomy_matrix.md) | Combinatorial Cartesian grid mapping scientific disciplines (ODEs, optimization, Fourier, splines) to Manim visual classes and camera techniques. |
| [sft_dataset_spec.md](file:///c:/Users/nabin/Desktop/myall/AOS/notes/multi_library_manim_coordination/sft_dataset_spec.md) | Formal schema, ChatML message format, Chain-of-Thought requirements, and dataset acceptance criteria. |

---

## 3. Core Architecture Pillars

### Pillar 1: Separation of Math and Animation
Scientific solvers must never be invoked per-frame inside Manim's updater loop. The computation occurs in pure Python/NumPy, generating structured arrays before the scene timeline starts.

```python
# 1. Compute heavy math upfront
solution = solve_ivp(lorenz_system, t_span, initial_state, t_eval=t_eval)
points = np.vstack(solution.y).T * scale_factor

# 2. Animate index traversal smoothly
tracker = ValueTracker(0)
def update_curve(mob):
    idx = int(tracker.get_value())
    if idx > 1:
        mob.set_points_as_corners([axes.c2p(*p) for p in points[:idx + 1]])

curve.add_updater(update_curve)
```

### Pillar 2: Audio-Visual Pacing Synchronization
When generating voiceover scripts, visual animations are locked to the spoken audio duration using `manim-voiceover`:

```python
with self.voiceover(text="Observe the strange attractor geometry.") as trk:
    self.play(
        tracker.animate.set_value(len(points) - 1),
        run_time=trk.duration,
        rate_func=linear
    )
```

### Pillar 3: Chain-of-Thought Enforced Output
Target outputs in the SFT dataset must begin with a 5-step mathematical and visual plan before providing code, teaching the fine-tuned LLM to reason step-by-step.

---

## 4. How to Run the Automated Generator

The automated synthetic generator lives in `apps/agents/sft_data_gen/generate_scipy_sft.py`.

To run the verification pipeline:
```bash
# Test AST filter and sample generation
uv run python apps/agents/sft_data_gen/generate_scipy_sft.py --test-sample
```
