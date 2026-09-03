# Phase 0 Research: Complete EduClaw Harness & Manim Animation Engine

## Research Decisions & Technical Architecture

### 1. Manim API Knowledge Base & Tool Integration
- **Decision**: Build a lightweight, local ManimCE API reflection & pattern index (`educlaw/animateworkflow/manim_kb.py`) and register `manim_api_lookup` on the Pydantic AI agent.
- **Rationale**: LLMs frequently hallucinate Manim parameters (e.g. `Background(...)` instead of `BackgroundRectangle`, or invalid kwargs on `ParametricFunction`). A local schema lookup tool resolves signatures instantly without network overhead.
- **Alternatives Considered**: 
  - Dynamic web search (slow, fails in offline/airgapped environments).
  - Pure prompt rules (prone to token context drift).

### 2. Multimodal Visual Quality Control (Visual Inspector Agent)
- **Decision**: Implement keyframe extraction (`ffmpeg -i scene.mp4 -vf fps=1 frame_%03d.png`) and a visual inspection tool (`visual_qc_check`).
- **Rationale**: AST checks catch syntax errors but miss visual defects like overlapping text, LaTeX rendering overflows off-screen edges, or poor color contrast. Vision inspection converts rendered MP4 frames into actionable feedback for the repair loop.
- **Alternatives Considered**: 
  - Pure SVG parsing (complex and misses composite rendering effects).
  - Manual human review (not scalable for autonomous generation).

### 3. Native Voiceover Synchronization & Timestamp Alignment
- **Decision**: Embed `ManimVoiceoverService` adapter in Docker sandbox and inject bookmark context manager patterns (`with self.voiceover(...) as tracker:`) into `CodeGeneratorAgent`.
- **Rationale**: `manim-voiceover` provides native bookmark markers (`<bookmark mark='B1'/>`) mapped to `self.wait_until_bookmark("B1")`, ensuring millisecond-accurate sync between spoken text and animation transitions.
- **Alternatives Considered**: 
  - Independent audio generation stitched post-render (inevitably leads to visual-audio drift).

### 4. Pedagogical Theme Engine & Visual Component Gallery
- **Decision**: Create a standardized `EduClawTheme` module (`educlaw/animateworkflow/theme.py`) providing curated palettes (Dark Glass, Solarized Math, Clean Pastel, Cyber Neon) and reusable layout snippets (Math Callout Cards, Step-by-Step Proof Containers, Code Highlighters).
- **Rationale**: Modern visual design wows users and enhances learning retention. Standardized components prevent basic/generic visual output and guarantee consistent typography and color contrast.
- **Alternatives Considered**: 
  - Freeform LLM color generation (produces inconsistent and unreadable color combinations).

### 5. Multi-Scene Video & Audio Assembly (`manim_concat_scenes`)
- **Decision**: Add a sandbox tool `manim_concat_scenes` that uses ffmpeg concat demuxer (`ffmpeg -f concat -i filelist.txt -c copy output.mp4`) to merge multi-scene lectures into a single seamless video.
- **Rationale**: Complex lectures are composed of multiple distinct Manim scenes. Assembling them inside Docker guarantees smooth transitions and single-file output.
- **Alternatives Considered**: 
  - Single monolithic Manim `Scene` class (susceptible to render timeouts and high memory usage).
