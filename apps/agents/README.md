# AOS Agents

## Scene content: `content` vs `params`

`SceneObject` (`packages/ir/src/ir/manim_ir.py`) has a dedicated `content: str`
field for the literal text/LaTeX shown by `math_tex`/`text` entities. It used
to live in the free-form `params` dict (`params={"tex": "..."}`), but
open-ended `dict[str, Any]` fields are unreliable for structured-output
models — nothing in the JSON schema tells the model the key `"tex"` is
expected, so smaller models (e.g. `gemini-2.5-flash-lite`) would routinely
leave it out, compiling to a blank `MathTex("")`. A declared string field
gets filled far more consistently.

- `scene_planner_agent`'s output validator (`_require_scene_per_step` in
  `scene_planner_agent.py`) rejects any `math_tex`/`text` object with empty
  `content` and retries with feedback — cheap to fix there vs. downstream
  where there's no scene graph left to repair against.
- `tools/compile.py` reads `obj.content` first, falling back to the legacy
  `params["tex"]`/`params["text"]` for any already-generated IR.
- `SceneObject.model_config` is `extra="allow"` (was `extra="forbid"`) — a
  stopgap so a model that drifts slightly (extra keys, minor shape
  mismatches) doesn't hard-fail into a `ModelRetry` loop. A tighter,
  better-fitted schema is the real long-term fix.

## Manim render performance

Rendering is the slowest part of the pipeline (`tools/render.py`, Docker +
`manimcommunity/manim`). These are the levers that actually move wall-clock
time in production, roughly in order of impact.

### Implemented in `tools/render.py`

- **Persistent container, `docker exec` instead of `docker run`.**
  `docker run --rm` pays for a fresh container filesystem/network namespace
  on every call; for short scenes that startup cost can exceed the render
  itself. `render_manim_scene`/`render_manim_scenes` keep one idle container
  per workspace alive (`tail -f /dev/null`, named by a hash of the mounted
  volume) and `docker exec` into it. Disable with
  `ToolDeps(persistent_container=False)` if you need fully isolated one-off
  runs.
- **Parallel scene rendering.** Manim/Cairo rendering is single-threaded per
  scene. `render_manim_scenes` fans independent scenes in a lecture out
  across a `ThreadPoolExecutor` (bounded by CPU count), each as its own
  `manim` process via `docker exec`, so a multi-scene lecture scales
  ~linearly with cores instead of rendering scene-by-scene.
- **`-v WARNING` logging.** Cuts per-frame progress-bar/log chatter, which
  keeps stdout small (cheaper `_parse_output_path` regex work) and avoids
  needless I/O in the container.
- **Manim's own frame cache stays on.** We never pass `--disable_caching` or
  `--flush_cache`. Because the workspace is bind-mounted (not copied into
  the container), `media/videos/.../partial_movie_files` persists across
  renders, so re-rendering a scene after only editing later beats is fast —
  unedited beats replay from cache instead of re-rendering.

### Additional tips (needs to apply per scene/project as needed)

- **Render at `-qh`/1080p @ 30fps for iteration, not `-qk`/4K @ 60fps.**
  Only use the top of the `Quality` ladder (`PRODUCTION`/`FOURK`) for the
  final pass; drafts should use `LOW`/`MEDIUM`.
- **Pre-render LaTeX to SVG where possible.** Every `Tex`/`MathTex` call
  invokes LaTeX; for static formulas, compiling once to SVG and loading via
  `SVGMobject` removes LaTeX from the hot path entirely.
- **Prefer `SVGMobject` over `ImageMobject`** for graphics — Cairo redraws
  raster images per frame at full resolution, while SVGs are vector paths.
  Keep SVGs simple (low path count).
- **Batch animations into one `self.play(...)`/`AnimationGroup`** instead of
  many sequential `play()` calls — `compile.py` already does this via
  `with_previous` grouping in `_compile_beat`.
- **Cache static backgrounds as a single pre-rendered image** instead of
  redrawing many static `VMobject`s every frame.
- **`docker pull manimcommunity/manim` ahead of time** in production so the
  first `_ensure_container` call doesn't block on a registry pull.

### Cleaning up persistent render containers

Containers created by `_ensure_container` are named `aos-manim-<hash>` and
are left running intentionally (that's the point — reuse). To reclaim them:

```bash
docker ps --filter "name=aos-manim-" -q | xargs -r docker rm -f
```


#########################################################

Fields to fill:
  topic             — the lecture title (from classification)
  subject           — "math", "cs", "ai", or "unknown"
  greeting          — Add a greeting message to the viewer. Keep it short and friendly. for eg: welcome to this lecture on {topic}!
  assumptions       — 2-4 things the viewer is expected to already know.
  objectives        — 3-5 bullets starting with action verbs (Understand, Derive,Apply, Visualize, Prove). These are promises to the viewer.
  opener            — The opener should feel like the beginning of an exceptional educational video,similar in spirit to the strongest science and mathematics explainers not sensational, but intellectually irresistible. learning_outcomes — 3-5 specific skills the viewer will walk away with.
  learning_outcomes: list[str] = Field(default_factory=list)
