# Manim Pipeline & Intermediate Representation (IR) Rules

## Intermediate Representation (IR) Architecture
- The core data structures live in `packages/ir/src/ir/manim_ir.py`.
- **`LectureIR`**: Root document containing metadata, storyboard, scenes, beats, and narration tracks.
- **`SceneObject`**:
  - Use `obj.content: str` for all text and LaTeX formulas (`math_tex`, `text`).
  - Do NOT put LaTeX/text in `params["tex"]` or `params["text"]`.
  - Empty `content` on text/LaTeX objects will cause validation failures.
- **`Beat`**: Represents granular visual actions. Ensure timestamps, target objects, and animation types (`Write`, `FadeIn`, `Transform`, `Indicate`, etc.) are well-formed.

## Manim Code Compilation & Rendering
- **Compiler**: `apps/agents/tools/compile.py` transforms `LectureIR` into valid Manim Python source code (`lecture.py`).
- **Render Engine**: `apps/agents/tools/render.py` invokes Docker with the `manimcommunity/manim` container.
- **Docker Persistence**: Render containers are kept alive for fast reuse under the name pattern `aos-manim-<hash>`.
- **Quality Flags**: Default to `-ql` (480p 15fps) for quick validation, `-qh` (1080p 60fps) for high quality.

## Audio Narration & Muxing
- Narration is generated beat-by-beat via `apps/audio_service` (Kyutai Pocket TTS).
- `apps/agents/tools/assemble.py` combines rendered video clips and beat audio tracks using `ffmpeg`.
- Ensure `ffmpeg` and `ffprobe` are available in system PATH.
