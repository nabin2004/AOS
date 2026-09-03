# Contracts: Harness Tools & API Interfaces

## 1. Tool: `manim_api_lookup`

### Signature
```python
async def manim_api_lookup(
    ctx: RunContext[AgentDeps],
    query: str,
    kind: str = "all",  # "all" | "class" | "animation" | "kwargs"
) -> str
```

### Input Arguments
- `query` (`str`): Class, animation name, or keyword parameter to search (e.g., `"MathTex"`, `"Transform"`, `"voiceover"`).
- `kind` (`str`): Optional filter for symbol type.

### Return Format
Returns formatted markdown snippet with class signature, valid kwargs, and code example.

---

## 2. Tool: `visual_qc_check`

### Signature
```python
async def visual_qc_check(
    ctx: RunContext[AgentDeps],
    video_path: str,
    extract_interval_sec: float = 2.0,
) -> str
```

### Input Arguments
- `video_path` (`str`): Path to rendered MP4 video in the workspace.
- `extract_interval_sec` (`float`): Keyframe extraction interval.

### Return Format
Returns JSON string representing `VisualQCReport` detailing keyframe analysis, detected overlaps, edge truncations, and remediation recommendations.

---

## 3. Tool: `manim_concat_scenes`

### Signature
```python
async def manim_concat_scenes(
    ctx: RunContext[AgentDeps],
    scene_files: list[str],
    output_filename: str = "final_lecture.mp4",
) -> str
```

### Input Arguments
- `scene_files` (`list[str]`): List of relative paths to rendered scene MP4 files.
- `output_filename` (`str`): Output MP4 filename inside workspace.

### Return Format
Returns status message indicating success and final concatenated video output path.

---

## 4. CLI Extension: `educlaw animate` Options

### New Flags
- `--theme`: Select visual theme (`dark_glass`, `solarized`, `pastel`, `neon`).
- `--inspect-visual`: Enable multimodal keyframe inspection after compilation (`true` / `false`).
- `--concat`: Automatically concatenate multi-scene outputs into a single lecture video.
