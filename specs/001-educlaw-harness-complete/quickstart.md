# Quickstart & End-to-End Validation Guide: Complete EduClaw Harness

This document outlines runnable validation scenarios that prove the enhanced EduClaw harness, tool ecosystem, visual theme system, and multimodal visual inspection end-to-end.

---

## 1. Prerequisites & Setup

```bash
# 1. Sync dependencies with dev and durable extras
uv sync --package educlaw --extra dev --extra durable

# 2. Activate test mode (for offline unit/smoke testing)
$env:EDUCLAW_TEST_MODEL="1"
$env:EDUCLAW_MEMORY_STUB="1"
```

---

## 2. Validation Scenario 1: Theme & Component System Verification

Validate that `EduClawTheme` and component templates load properly into the code generator context.

```bash
# Run unit tests for theme engine and component library
.venv\Scripts\python.exe -m pytest tests/test_theme_and_components.py
```

**Expected Outcome**: All theme color tokens (Dark Glass, Solarized Math, Clean Pastel, Cyber Neon) and component snippets load cleanly without errors.

---

## 3. Validation Scenario 2: Manim API Lookup Tool Test

Validate that `manim_api_lookup` accurately returns symbol signatures and valid kwargs.

```bash
# Test API lookup tool directly via python invocation
.venv\Scripts\python.exe -c "
from educlaw.animateworkflow.manim_kb import lookup_symbol
print(lookup_symbol('MathTex'))
"
```

**Expected Outcome**: Output includes `MathTex` class definition, signature, valid parameter kwargs, and code usage snippet.

---

## 4. Validation Scenario 3: Multimodal Keyframe Visual Inspection

Validate keyframe extraction and visual inspection report generation.

```bash
# Run visual inspection evaluation test
.venv\Scripts\python.exe -m pytest tests/test_visual_qc.py
```

**Expected Outcome**: Keyframes are extracted from test MP4 videos, analyzed for bounding box collisions, and a structured `VisualQCReport` is generated.

---

## 5. Validation Scenario 4: End-to-End Animate Pipeline Run

Execute the full 6-stage pipeline with theme selection and multi-scene concatenation.

```bash
# Run single-shot CLI command with theme selection
.venv\Scripts\python.exe -m educlaw.cli animate "Explain Fourier Transform visually" --theme dark_glass --quality l
```

**Expected Outcome**: 
1. Request classified and scene plan constructed.
2. Code generated utilizing Dark Glass theme palette and component templates.
3. Code compiled in Docker sandbox (`manimcommunity/manim:stable`).
4. Keyframe snapshots extracted and passed visual QC gate.
5. Ingested into Dagestan temporal memory graph (`.aos/memory/graph.json`).
