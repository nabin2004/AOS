---
name: manim-spatial-rules
description: Hard constraints, bounding coordinates, LaTeX rules, and spatial layout guardrails for Manim Community Edition scenes.
---

# Manim Coordinate System Constraints
- Standard 16:9 viewport bounds:
  - Width: 14.22 units (x ∈ [-7.11, 7.11])
  - Height: 8.0 units (y ∈ [-4.0, 4.0])

# Spatial Hierarchy Guardrails
1. **Title Header Zone**: Reserved for y ∈ [3.0, 3.8]. Always place using `.to_edge(UP, buff=0.4)`.
2. **Workspace / Derivation Zone**: Reserved for y ∈ [-2.5, 2.5] and x ∈ [-6.0, 6.0].
3. **Relative Positioning**: Never use hardcoded absolute coordinates `[x, y, 0]` for text labels. Always chain relative anchors:
   - `target.next_to(anchor, DOWN, buff=MED_SMALL_BUFF)`
   - `target.align_to(anchor, LEFT)`
4. **Overlap Mitigation**:
   - When introducing multiple equations, group preceding elements into a `VGroup` and shift them (`group.animate.shift(UP * 1.5)`) or clear them (`FadeOut(group)`) before writing new steps.
5. **LaTeX Formatting**:
   - Always use raw string literals for LaTeX expressions: `MathTex(r"...")` or `Tex(r"...")`.
   - Ensure all braces `{}` and LaTeX commands (e.g. `\frac`, `\times`, `\theta`) are escaped properly inside raw strings.
