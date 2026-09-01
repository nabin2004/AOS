# ManiBench: Quick Start Guide

## What is ManiBench?

**ManiBench** is a specialized benchmark dataset for evaluating Large Language Model (LLM) performance in generating Manim code—animations that teach mathematics. It tests two critical failure modes:

1. **Syntactic Hallucinations**: Code that looks valid Python but uses non-existent Manim functions
2. **Visual-Logic Drift**: Code that runs but produces incorrect or incomplete animations

---

## Files Included

### 1. **ManiBench_Specification.md**
The main research paper. Contains:
- Abstract and introduction
- Problem definitions and metrics
- Full 12-problem pilot dataset descriptions
- Preliminary results and discussion

**Read this first** to understand the benchmark's goals and structure.

### 2. **ManiBench_Pilot_Dataset.json**
Structured JSON dataset (schema v2.0) with 12 pilot problems. Each includes:
- Problem ID, title, YouTube video source
- Category and difficulty level (1–5)
- Full problem prompt
- Required visual events (with weights, timing, criticality flags)
- Coverage requirements
- Common failure modes
- Pedagogical intent
- **Reference code analysis**: Scene class inventories, visual techniques, API patterns, and ManimGL→ManimCE version conflict notes (derived from 3Blue1Brown's original source code)
- Raw code collection status and file paths

**Use this** to generate problems for LLMs or to programmatically evaluate output.

### 3. **ManiBench_Evaluation_Rubric.md**
Detailed scoring methodology for the four metrics:
- **Executability**: Binary (code runs or fails)
- **Version-Conflict Error Rate**: Deprecated/mixed API usage
- **Alignment Score**: Required visual events present and timed correctly
- **Coverage Score**: Pedagogical elements (labels, formulas, numeric evidence)

Includes worked examples, disagreement resolution, and scoring procedures.

**Use this** when evaluating generated animations.

### 4. **ManiBench_QuickStart.md** (this file)
Quick reference and workflow guide.

---

## Workflow: Using ManiBench to Evaluate an LLM

### Step 1: Choose a Problem

Pick one from **ManiBench_Pilot_Dataset.json**. Example: MB-002 (Gradient Descent).

### Step 2: Prompt Your LLM

Use the `full_prompt` field from the JSON:

```
You are a Manim expert. Write Manim code to:
[Full problem prompt text here]
```

### Step 3: Generate and Execute

Run the generated code:
```bash
manim -ql scene_name.py OutputScene
```

Or in a Python environment:
```python
from manim import *
# [generated code]
config.media_dir = "output"
scene = YourScene()
scene.render()
```

### Step 4: Score Using Four Metrics

#### 4a. Executability
- Does it run? (Yes/No)
- Does it use deprecated imports? (Check against Manim CE API)
- **Score**: 1.0 if pass, 0.0 if fail

#### 4b. Version-Conflict Error Rate
- Does it use GL-specific syntax (if targeting CE)?
- Does it use renamed/moved functions?
- Check against the `version_conflict_notes.known_incompatibilities` field in the JSON for each problem (145 documented incompatibilities across all 12 problems)
- Common patterns: `CONFIG` dicts, `ShowCreation` (should be `Create`), `GraphScene` (should use `Axes`), `InteractiveScene`, `PiCreature` ecosystem
- **Score**: Percentage of runs with version conflicts

#### 4c. Alignment Score
1. Watch the rendered animation
2. Check off each "Required Visual Event" from JSON
3. For each event, score:
   - Present + correct timing: 1.0
   - Present + wrong timing: 0.75
   - Missing: 0.0
4. Compute weighted average:
   ```
   Alignment = Σ(weight_i × present_i × timing_i) / Σ(weight_i)
   ```

**Example**: If Gradient Descent has 5 events with weights [0.8, 0.9, 0.8, 0.7, 0.6]:
- All present and timed correctly: (0.8 + 0.9 + 0.8 + 0.7 + 0.6) / (0.8 + 0.9 + 0.8 + 0.7 + 0.6) = **1.0**
- Missing gradient arrows event: (0.8 + 0.9 + 0.8 + 0 + 0.6) / (0.8 + 0.9 + 0.8 + 0.7 + 0.6) = **0.88**

#### 4d. Coverage Score
1. Check presence of required pedagogical elements:
   - Math annotations (labels, formulas): count / required
   - Visual mapping (colors, hierarchy): count / required
   - Numeric evidence (numbers, axes): count / required
   - Structural clarity (organization): score 0–1

2. Weighted average:
   ```
   Coverage = 0.35×math_score + 0.30×visual_score + 0.20×numeric_score + 0.15×clarity_score
   ```

### Step 5: Aggregate Results

After 3 trials per problem, compute:
```
Executability = (# passed) / 3
Alignment_mean = mean(alignment scores)
Alignment_std = std(alignment scores)
Coverage_mean = mean(coverage scores)
Version_Conflict_Rate = (# with conflicts) / 3
```

### Step 6: Report

Example output for one problem:

```
Problem: MB-002 (Gradient Descent)
Model: Claude 3.5 Sonnet

Results (3 trials):
  Executability: 3/3 = 100%
  Alignment: 0.75 ± 0.05 (range: 0.70–0.80)
  Coverage: 0.82 ± 0.03 (range: 0.80–0.85)
  Version Conflicts: 0/3 = 0%

Interpretation: Model produces syntactically correct code with 
good temporal alignment and pedagogical coverage. No version compatibility issues.
```

---

## Difficulty Progression

Start with **easier problems** before tackling harder ones:

| Level | Problems | Examples | Difficulty |
|-------|----------|----------|------------|
| 2 | MB-005, MB-007 | The Determinant, Medical Test Paradox | Straightforward visualization |
| 3 | MB-002, MB-003, MB-006, MB-008, MB-009 | Gradient Descent, Convolution, CLT, Chain Rule, FTC | Requires temporal sync |
| 4 | MB-001, MB-004, MB-010, MB-012 | Colliding Blocks, Eigenvectors, Taylor, Windmill | Complex timing, multi-scene |
| 5 | MB-011 | Hairy Ball Theorem | Advanced topology, 3D graphics |

**Recommendation**: Start with Level 2–3 problems (MB-005, MB-007, MB-002) to debug your evaluation setup. Then scale to full 12 problems.

---

## Common Failure Patterns (Observed So Far)

Based on GPT-4o and Claude results:

1. **Executability Issues**
   - Missing imports: `from manim import Circle` → `MCircle` (hallucinated)
   - Deprecated methods: `mobject.scale()` → API changed
   - GL-specific calls in CE code: `InteractiveScene`, `ReconfigurableScene`, `GraphScene`
   - PiCreature ecosystem: `TeacherStudentsScene`, `Eyes`, `PiCreatureSays` (not in CE)
   - CONFIG dict pattern: Using class-level CONFIG instead of `__init__` parameters
   - Custom mobjects from GL: `NetworkMobject`, `Car`, `DieFace`, `GlowDot`, `Clock` (need reimplementation)

2. **Alignment Issues**
   - Temporal drift: Dot moves but loss curve doesn't update simultaneously
   - Missing events: Animation shows result without showing derivation
   - Wrong order: Events occur in wrong sequence (e.g., f applied before g in chain rule)

3. **Coverage Issues**
   - Missing labels: Axes without "x", "y", "z" labels
   - No numeric display: Determinant value computed but not shown
   - Cluttered layout: Multiple elements overlap or unreadable

---

## Tips for High Quality Evaluations

1. **Watch the full animation**, not just code. Visual timing is hard to detect from code.

2. **Use the rubric examples**. Refer to worked examples in `ManiBench_Evaluation_Rubric.md`.

3. **Standardize your rendering**:
   - Use `manim -ql` (low quality, faster)
   - Consistent frame rate (15 fps default)
   - Consistent resolution (720x1280 default)

4. **Two-reviewer agreement**: If evaluating with a team, have two reviewers score independently. If disagreement > 0.10, bring in a third reviewer.

5. **Document edge cases**:
   - Did code timeout? Note it.
   - Did rendering produce blank screen? Note it.
   - Did animation render partially? Score only rendered portion.

---

## Using the Reference Code Analysis

Each problem in the JSON includes a `reference_code_analysis` field with data derived from the original 3Blue1Brown source code. Use this to:

1. **Understand expected visual complexity**: Check `scene_classes` count and `visual_techniques` to gauge what a complete animation should include
2. **Evaluate version conflicts**: Compare LLM output against `version_conflict_notes.known_incompatibilities` — if the LLM uses any listed GL construct, it's a version conflict
3. **Verify visual events**: Cross-reference `visual_techniques` with what appears in the LLM's output
4. **Assess API patterns**: Check if the LLM uses appropriate CE equivalents for the `manim_api_patterns` listed

**Note**: The raw source code in `raw_code/` is for evaluator reference only. Do NOT share it with LLMs during evaluation.

---

## Extending ManiBench

### Adding More Problems

To expand from 12 to 150–200 problems:

1. **Identify candidate videos** from 3Blue1Brown's channel or other sources
2. **Extract required visual events** by watching the original animation
3. **Write problem prompt** in natural language
4. **Specify weights** (typically 0.6–0.9 for required events)
5. **List coverage requirements** (5–8 elements)
6. **Document failure modes** (common mistakes)

### Community Contribution

If contributing new problems:
- Follow JSON format in `ManiBench_Pilot_Dataset.json`
- Ensure required events are objective and testable
- Provide YouTube video link for reference
- Test prompt with at least one LLM to verify feasibility

---

## Citation

If using ManiBench in your work:

```bibtex
@article{ManiBench2026,
  title={ManiBench: A Benchmark for Testing Visual-Logic Drift 
         and Syntactic Hallucinations in Manim Code Generation},
  author={Oli, Nabin},
  year={2026},
  affiliation={Sunway College Kathmandu, Birmingham City University}
}
```

---

## FAQ

**Q: How long does it take to evaluate one problem?**  
A: ~10–15 minutes per trial (execution + viewing + scoring).

**Q: Can I automate alignment scoring?**  
A: Not fully. You need to watch the animation. However, you can:
- Detect missing imports (automatic)
- Check axis labels via screenshot comparison (semi-automatic)
- Approximate timing via scene objects (heuristic)

**Q: What if the LLM generates multi-scene code?**  
A: Score each scene separately, then average. See "Case 4" in the rubric.

**Q: Can I use a different version of Manim?**  
A: Benchmark targets **Manim CE**. If using GL, note version-specific errors separately.

---

## Resources

- **Manim CE Documentation**: https://docs.manim.community/
- **3Blue1Brown GitHub**: https://github.com/3b1b/videos
- **HuggingFace Dataset**: https://huggingface.co/datasets/nabin2004/ManiBench
- **Paper Preprint**: (insert arXiv link when published)

---

**ManiBench Version**: 1.1-pilot  
**Schema Version**: 2.0  
**Last Updated**: 2026-02-18  
**Status**: Pilot dataset complete with full reference code analysis
