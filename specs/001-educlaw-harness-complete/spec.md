# Feature Specification: Complete EduClaw Harness & Manim Animation Engine

**Feature Name**: `001-educlaw-harness-complete`  
**Status**: Draft  
**Target Module**: `apps/educlaw`  

## Overview & Goal

The **EduClaw Harness** is the multi-agent execution framework for generating educational Manim animations, synchronized voiceover narration, and structured learning experiences. While initial pipeline components (classification, scene planning, sandboxed Docker compilation, basic audio synthesis, and Dagestan memory) exist, key missing components hinder production-grade animation output and pedagogical clarity.

This specification outlines the complete set of features, tools, visual inspection capabilities, theme systems, and audio-visual timing mechanisms needed to turn EduClaw into an elite Manim animation harness.

## Clarifications

### Session 2026-09-03
- Q: Which primary multimodal model should the Visual QC inspector use to analyze Manim keyframes? → A: Provider agnostic (Configured via EDUCLAW_VISION_MODEL env var)
- Q: If `ffmpeg` concatenation of multiple scenes fails (e.g., due to resolution or audio codec mismatch), what is the expected fallback behavior? → A: Return the individual unstitched scene MP4 files instead
- Q: Where should agent interaction trajectory logs be persisted for downstream GEPA/DSPy optimization? → A: Local file system as JSONL (.aos/trajectories/)

---

## Key Functional Requirements

### 1. Pedagogical Visual Design & Theme System
- **Theme Engine**: Provide a declarative Manim theme engine (`EduClawTheme`) supporting pre-designed color palettes (Dark Glass, Solarized Math, Clean Pastel, Cyber Neon) and typography defaults.
- **Visual Component Library**: Expose reusable visual templates (Math Callout Cards, Step-by-Step Proof Containers, Code Syntax Highlighters, Dynamic Number Lines, Vector Field Displays) injected into the coder prompt context.
- **Micro-Pacing & Pacing Rules**: Enforce automated narration-to-wait calculation rules based on syllable count, ensuring animations stay synchronized with voiceover without abrupt cuts.

### 2. Multimodal Visual Quality Control (Visual Inspector)
- **Frame Extraction**: Extract keyframe snapshots (`.png`) from rendered MP4 videos at beat transitions.
- **Vision Model**: The visual inspection agent is provider-agnostic and configured via the `EDUCLAW_VISION_MODEL` environment variable to support both cloud and local testing.
- **Visual QA Gate**: Introduce a multimodal visual inspection tool (`visual_qc_check`) that analyzes keyframe images for:
  - Off-screen or clipped LaTeX formulas / text elements.
  - Element overlap or collision.
  - Poor color contrast against background.
- **Visual Repair Loop**: Inject visual inspection feedback directly into the `step_generate_and_compile` failure classification loop.

### 3. Native Manim Voiceover & Timestamp Aligner
- **PocketTTS & DSM Voiceover Service**: Provide a native `ManimVoiceoverService` binding within the Docker sandbox connecting Pocket TTS and Kyutai DSM word-level timestamps.
- **Bookmark Synchronization**: Support precise `<bookmark mark='B1'/>` tag injection and `self.wait_until_bookmark("B1")` context managers in generated `VoiceoverScene` Python code.

### 4. Advanced Harness Tooling & API Inspection
- **Manim API Knowledge Base Tool (`manim_api_lookup`)**: Allow agents to query valid ManimCE classes, animation methods, transform primitives, and keyword arguments to eliminate hallucinated syntax.
- **Multi-Scene Video Assembly Tool (`manim_concat_scenes`)**: Automatically stitch multiple scene video outputs into a single cohesive lecture MP4 with seamless audio mixing via ffmpeg. If concatenation fails (e.g., due to format mismatch), it gracefully falls back to returning the individual unstitched scene MP4 files.
- **Trajectory Logging & DSPy Prompt Optimizer Hook**: Record agent interaction trajectories to feed into GEPA / DSPy prompt optimization loops. Trajectories will be persisted locally as JSONL files in `.aos/trajectories/`.

---

## Success Criteria

1. **Zero Visual Collisions**: Rendered animations pass automated visual QA with 0 element overlaps or boundary truncations.
2. **Audio-Visual Alignment**: Narration bookmarks align with visual transitions within a 100ms tolerance.
3. **Compilation First-Pass Success Rate**: High-quality Manim code generation success rate improves significantly via API lookup tools and AST preflight validation.
4. **Pedagogical Engagement**: Generated scenes feature structured layouts, smooth camera framing, and clear visual hierarchy.
