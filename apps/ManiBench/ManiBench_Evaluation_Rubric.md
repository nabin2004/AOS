# ManiBench Evaluation Rubric

## Overview

This document provides the detailed scoring methodology for ManiBench. Each problem is evaluated on four metrics: Executability, Version-Conflict Error Rate, Alignment Score, and Coverage Score.

All 12 pilot problems now include `reference_code_analysis` in the JSON dataset, providing evaluators with scene class inventories, visual technique catalogs, and 145 documented ManimGL→ManimCE incompatibilities to assist in scoring.

---

## Metric 1: Executability (Pass@1)

**Definition**: Binary success/failure indicator. Does the generated code run without raising exceptions or using deprecated imports?

### Success Criteria

A submission PASSES if:
- Script runs without unhandled exceptions
- No deprecation warnings from Manim CE
- No invalid imports
- Rendering completes without error

A submission FAILS if:
- Runtime exception (AttributeError, TypeError, ValueError, etc.)
- Import error (missing module or class)
- Deprecated API call (e.g., using renamed function)
- Timeout during rendering (>30 seconds)

### Scoring

```
Executability_Score = (# passes) / (# total attempts)
```

### Detection Procedure

1. **Automatic Checks**:
   - Parse code and extract `from manim import ...` statements
   - Check against known deprecated/moved classes
   - Attempt to run code, capture stderr

2. **Deprecation Scan**:
   - Use Manim CE's deprecation registry
   - Flag imports not in Manim CE API
   - Flag function calls with incorrect signatures

3. **Manual Verification** (if needed):
   - Run against Manim CE in Docker or local environment
   - Record exception messages

---

## Metric 2: Version-Conflict Error Rate

**Definition**: What fraction of runs trigger errors specific to version constraints?

### Tracked Error Categories

1. **GL-specific syntax in CE code**: Using `from manim_gl import ...` when targeting CE
2. **Incompatible API**: Calling functions only available in GL (e.g., `render_to_movie_file(..., renderer="opengl")`)
3. **Renamed/moved functions**: Using outdated function names (e.g., `mobject.set_height()` vs `mobject.height = ...`)
4. **Signature mismatches**: Passing wrong arguments to functions
5. **Mixed imports**: Mixing CE and GL imports in same script

### Scoring

```
Version_Conflict_Error_Rate = (# version-specific errors) / (# total attempts)
```

### Detection Procedure

1. **Pattern Matching**:
   - Scan for `manim_gl` imports
   - Search for GL-only function calls (maintain allowlist of GL-only APIs)
   - Check function signatures against CE documentation

2. **Example GL-only constructs** (from reference code analysis):
   - `InteractiveScene` → `Scene` in CE
   - `GraphScene` → `Axes` object methods in CE  
   - `ReconfigurableScene` → no CE equivalent
   - `CONFIG` dict pattern → `__init__` parameters in CE
   - `ShowCreation` → `Create` in CE
   - `FadeInFrom(m, LEFT)` → `FadeIn(m, shift=LEFT)` in CE
   - `self.frame.reorient()` → `self.camera.frame` in CE
   - `apply_depth_test()` / `set_shading()` → GL renderer only
   - `TexturedSurface` / `.obj` loading → limited CE support
   - `PiCreature` / `TeacherStudentsScene` / `Eyes` → not in CE
   - `DieFace`, `GlowDot`, `Car`, `Clock`, `NetworkMobject` → custom implementation needed
   - `manim_imports_ext` → `from manim import *`
   - `OldTex`/`OldTexText` → `Tex`/`MathTex` in CE
   - `force_skipping` / `revert_to_original_skipping_status` → not in CE

   **Tip**: Check the `version_conflict_notes.known_incompatibilities` field for each problem in the JSON dataset for problem-specific incompatibilities.

3. **Manual Inspection**:
   - If automatic checks don't catch error, run code and note version-specific failures

### Reporting

Report as a percentage. Example:
- 0% version-conflict errors: All code compatible with CE
- 10% version-conflict errors: 1 in 10 submissions use GL syntax

---

## Metric 3: Alignment Score (0.0–1.0)

**Definition**: Weighted fraction of required visual events present and correctly timed.

### Formula

```
Alignment_Score = Σ(weight_i × is_present_i × is_correct_timing_i) / Σ(weight_i)
```

Where:
- `weight_i` = Importance weight of event i (typically 0.6–0.9 for required events)
- `is_present_i` = 1 if event i appears in output, else 0
- `is_correct_timing_i` = 1 if event timing matches expected, else 0 (or partial credit 0.5)

### Scoring Procedure

**Step 1: Review Problem Annotation**
- Identify all "Required Visual Events" for the problem
- Note weight and critical status (critical events weighted higher)
- Cross-reference with `reference_code_analysis.visual_techniques` in the JSON for the expected rendering approach

**Step 2: Watch Animation Output**
- Render generated code
- Observe each required event
- Note timing relative to other events

**Step 3: Score Each Event**

| is_present | Timing | Score | Interpretation |
|-----------|--------|-------|-----------------|
| ✓ | Correct | 1.0 | Event present at expected moment |
| ✓ | Early | 0.75 | Event present but occurs before expected |
| ✓ | Late | 0.75 | Event present but occurs after expected |
| ✓ | Way off | 0.5 | Event present but timing far from expected |
| ✗ | – | 0.0 | Event missing entirely |

**Step 4: Compute Alignment Score**

```python
# Pseudocode
score = 0.0
total_weight = 0.0

for event in required_events:
    present_score = 1.0 if event.is_present else 0.0
    timing_score = event.get_timing_score()  # 0.5, 0.75, 1.0, or 0.0
    
    event_score = event.weight * present_score * timing_score
    score += event_score
    total_weight += event.weight

alignment_score = score / total_weight
return alignment_score
```

### Examples

**Example 1: Gradient Descent**
```
Events:
- Surface visualized: present=✓, timing=correct → 0.8 × 1.0 × 1.0 = 0.80
- Dot moves: present=✓, timing=correct → 0.9 × 1.0 × 1.0 = 0.90
- Loss curve updates: present=✓, timing=late → 0.8 × 1.0 × 0.75 = 0.60
- Gradient arrows: present=✗ → 0.7 × 0.0 × 0.0 = 0.00

Alignment = (0.80 + 0.90 + 0.60 + 0.00) / (0.8 + 0.9 + 0.8 + 0.7) = 2.30 / 3.20 = 0.719
```

**Example 2: Convolution (Missing Window Movement)**
```
Events:
- Signal visualized: ✓, correct → 0.8 × 1.0 × 1.0 = 0.80
- Kernel visualized: ✓, correct → 0.8 × 1.0 × 1.0 = 0.80
- Window moves: ✗ [CRITICAL] → 0.9 × 0.0 × 0.0 = 0.00
- Product shown: ✓, correct → 0.7 × 1.0 × 1.0 = 0.70
- Output accumulates: ✗ → 0.8 × 0.0 × 0.0 = 0.00

Alignment = (0.80 + 0.80 + 0.00 + 0.70 + 0.00) / (0.8 + 0.8 + 0.9 + 0.7 + 0.8) = 2.30 / 4.00 = 0.575
```

**Example 3: Chain Rule (Wrong Order)**
```
Events:
- g(x) function plotted: ✓, correct → 0.7 × 1.0 × 1.0 = 0.70
- f(u) function plotted: ✓, correct → 0.7 × 1.0 × 1.0 = 0.70
- Change propagates through f: ✓, but should be g first (timing error) → 0.8 × 1.0 × 0.5 = 0.40
- Change propagates through g: ✓, but should be second (timing error) → 0.8 × 1.0 × 0.5 = 0.40
- Formula shown: ✗ → 0.7 × 0.0 × 0.0 = 0.00

Alignment = (0.70 + 0.70 + 0.40 + 0.40 + 0.00) / (0.7 + 0.7 + 0.8 + 0.8 + 0.7) = 2.20 / 3.70 = 0.595
```

### Interpretation

| Score | Interpretation |
|-------|-----------------|
| 0.90–1.0 | Excellent: All major events present and well-timed |
| 0.75–0.89 | Good: Most events present; minor timing issues |
| 0.60–0.74 | Fair: Core events present; some missing or misaligned |
| 0.45–0.59 | Poor: Multiple events missing or severely misaligned |
| <0.45 | Failed: Critical events missing; output doesn't match pedagogical intent |

---

## Metric 4: Coverage Score (0.0–1.0)

**Definition**: Density of pedagogical elements (labels, annotations, numeric evidence, visual clarity).

### Categories

1. **Mathematical Annotation** (weight: 0.35)
   - Are formulas displayed?
   - Are variable names labeled?
   - Are mathematical symbols/notation present?

2. **Visual Mapping** (weight: 0.30)
   - Is color coding used consistently?
   - Are objects/regions clearly distinguished?
   - Is layout organized (not cluttered)?

3. **Numeric Evidence** (weight: 0.20)
   - Are computed values displayed?
   - Are axes labeled with numbers?
   - Is a counter or progress indicator shown (if relevant)?

4. **Structural Clarity** (weight: 0.15)
   - Are multiple scenes/panels organized logically?
   - Is there a clear visual hierarchy?
   - Is text readable and well-positioned?

### Scoring Procedure

**Step 1: Check Requirements**

For each category, count elements:
- Present (1 point)
- Partially visible or unclear (0.5 points)
- Missing (0 points)

**Step 2: Compute Category Scores**

```
Math_annotation_score = (# present annotations) / (# required annotations)
Visual_mapping_score = (# present mappings) / (# required mappings)
Numeric_evidence_score = (# present numeric elements) / (# required numeric elements)
Clarity_score = (# well-organized scenes) / (# total scenes)
```

**Step 3: Weighted Average**

```
Coverage_Score = 
  0.35 × Math_annotation_score +
  0.30 × Visual_mapping_score +
  0.20 × Numeric_evidence_score +
  0.15 × Clarity_score
```

### Examples

**Example 1: Determinant**

Requirement checklist:
- [ ] Original parallelogram area labeled "1"
- [ ] Transformed parallelogram visualized
- [ ] New area labeled
- [ ] Determinant value displayed as a number
- [ ] Matrix displayed
- [ ] Axis labels

Scoring:
```
Math_annotation_score = 5/5 = 1.0
  (area labels, determinant label, matrix, axis labels all present)

Visual_mapping_score = 1.0
  (color or outline distinguishes original vs transformed)

Numeric_evidence_score = 1.0
  (determinant number, matrix values, area value all shown)

Clarity_score = 1.0
  (single scene, well-organized)

Coverage = 0.35×1.0 + 0.30×1.0 + 0.20×1.0 + 0.15×1.0 = 1.00
```

**Example 2: Gradient Descent (Missing Axis Labels)**

Requirement checklist:
- [✓] Loss surface labeled
- [✓] Dot shown
- [✗] Axis labels ('w₁', 'w₂', 'Loss')
- [✓] Gradient arrows shown
- [✓] Loss curve displayed
- [✓] Learning rate/step size indicated

Scoring:
```
Math_annotation_score = 5/6 = 0.83
  (missing axis labels)

Visual_mapping_score = 0.9
  (arrows color-coded, dot distinct, but could be clearer)

Numeric_evidence_score = 0.8
  (loss values shown, but step size not numeric)

Clarity_score = 1.0
  (surface and curve panels organized)

Coverage = 0.35×0.83 + 0.30×0.9 + 0.20×0.8 + 0.15×1.0 = 0.291 + 0.27 + 0.16 + 0.15 = 0.871
```

### Interpretation

| Score | Interpretation |
|-------|-----------------|
| 0.90–1.0 | Excellent: Rich annotations, clear visual hierarchy, all pedagogical elements |
| 0.75–0.89 | Good: Most annotations present; minor clarity issues |
| 0.60–0.74 | Fair: Basic annotations; some elements missing |
| <0.60 | Poor: Sparse annotations; pedagogical value reduced |

---

## Multi-Reviewer Workflow

### Disagreement Resolution

When two reviewers score the same output:

1. **If disagreement ≤ 0.10 (Alignment) or ≤ 0.10 (Coverage)**:
   - Use average of both scores

2. **If disagreement > 0.10**:
   - Bring in third reviewer
   - Take median of three scores
   - Document reason for disagreement

### Inter-rater Reliability

Report Krippendorff's α (or Fleiss' κ for multiple raters):
- α ≥ 0.80: Excellent agreement
- 0.60–0.79: Good agreement
- <0.60: Fair agreement; consider rubric revision

---

## Aggregation and Reporting

### Per-Problem Aggregation

For each problem, after N trials:
```
Executability = (# passed) / N
Alignment_avg = mean(alignment_scores)
Alignment_std = std(alignment_scores)
Coverage_avg = mean(coverage_scores)
Coverage_std = std(coverage_scores)
Version_conflict_rate = (# version errors) / N
```

### Benchmark-Level Aggregation

Across all 12 problems:
```
Macro_Executability = mean(all executability scores)
Macro_Alignment = mean(all alignment scores)
Macro_Coverage = mean(all coverage scores)
Macro_Version_Conflict = mean(all version conflict rates)
```

### Example Report

```
Problem: MB-002 (Gradient Descent)
Model: GPT-4o
Trials: 3

Executability: 3/3 = 100%
Alignment: 0.73 ± 0.08 (range: 0.68–0.82)
Coverage: 0.81 ± 0.05 (range: 0.76–0.87)
Version Conflicts: 0/3 = 0%

Interpretation: Model generates syntactically correct code with good alignment on 
timing and events. Coverage is strong (labels and annotations present). 
No version compatibility issues.
```

---

## Special Cases and Edge Cases

### Case 1: Partial Rendering (Timeout)

If animation renders partially (e.g., only first 3 of 8 scenes):
- **Executability**: FAIL (incomplete execution)
- **Alignment**: Score only rendered portion (may be partial credit)
- **Coverage**: Score only rendered portion

### Case 2: Syntax Valid but Non-executable

Code has valid Python syntax but fails at runtime (e.g., `mobject.nonexistent_method()`):
- **Executability**: FAIL
- **Version-Conflict**: May be flagged as undefined method

### Case 3: Animation Runs But Blank Screen

Code runs without error but renders nothing visible:
- **Executability**: PASS (no exception)
- **Alignment**: 0.0 (no visual events)
- **Coverage**: 0.0 (no elements visible)

### Case 4: Multiple Scenes, Some Wrong

Code has Scene1 (correct), Scene2 (incorrect timing), Scene3 (correct):
- **Alignment**: Weighted average across all scenes (Scene2 scored lower)
- **Executability**: PASS (no exception)

---

## Appendix: Checklist for Reviewers

Before scoring:

- [ ] Problem specification read and understood
- [ ] Required visual events list consulted
- [ ] Coverage requirements checklist prepared
- [ ] Code executed or animation rendered
- [ ] No technical issues with rendering (not the code's fault)
- [ ] Alignment events checked in sequence
- [ ] Coverage elements counted systematically
- [ ] Score justified with specific examples

---

**Rubric Version**: 1.1  
**Schema Version**: 2.0  
**Last Updated**: 2026-02-18
