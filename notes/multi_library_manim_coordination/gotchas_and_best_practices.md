# Gotchas, Failure Modes, and Best Practices for Multi-Library Coordination

When fine-tuning or prompting LLMs to combine **Manim Community Edition**, **NumPy**, **SciPy**, and **manim-voiceover**, standard models encounter specific, reproducible failure modes. This document formalizes these failure modes, explains the underlying runtime causes, and defines strict patterns and AST rules to prevent them.

---

## 1. SciPy Differential Equation Solving Inside Updaters (Performance Crash)

### The Trap
LLMs frequently attempt to compute numerical integration inside the per-frame updater callback:
```python
# ❌ ANTI-PATTERN: SciPy called inside an updater function
def bad_updater(mob):
    # This executes 60 times per second!
    sol = solve_ivp(lorenz, (0, tracker.get_value()), [1.0, 1.0, 1.0])
    mob.set_points_as_corners([axes.c2p(*p) for p in sol.y.T])

curve.add_updater(bad_updater)
```

### Why It Fails
- Manim renders at 30 to 60 FPS. If an updater solves an initial value problem (`solve_ivp`), runs an optimization sweep (`minimize`), or computes an FFT on every frame, render speed collapses from real-time to `< 0.2 FPS`.
- In headless CI/CD, Colab, or RunPod batches, the render process runs out of CPU time and times out, resulting in corrupted datasets.

### Correct Pattern: Separation of Concerns
Compute the entire trajectory in dense array format **before** defining animation objects, and use the updater **only** for indexing into the pre-computed array:
```python
# ✅ CORRECT: Pre-compute upfront, slice in updater
t_span = (0, 25)
t_eval = np.linspace(t_span[0], t_span[1], 2500)
sol = solve_ivp(lorenz_system, t_span, [1.0, 1.0, 1.0], t_eval=t_eval)
points = np.vstack(sol.y).T * 0.1  # Rescale for camera viewport

tracker = ValueTracker(0)

def update_curve(mob):
    idx = int(tracker.get_value())
    if idx > 1:
        mob.set_points_as_corners([axes.c2p(*p) for p in points[:idx + 1]])

curve.add_updater(update_curve)
```

---

## 2. Audio Context Manager Scoping & Audio Stacking

### The Trap
Placing `self.play()` calls outside or after the `with self.voiceover(...)` block:
```python
# ❌ ANTI-PATTERN: Animation placed outside voiceover context
with self.voiceover(text="Here is the chaotic trajectory.") as tracker:
    pass

self.play(tracker.animate.set_value(100), run_time=5)
```

### Why It Fails
`manim-voiceover`'s context manager triggers audio playback during its `__exit__`. If no animations occur inside the `with` block, Manim plays the audio over a static frame, and then runs the animation in dead silence afterwards.

### Correct Pattern
All visual events that accompany speech must remain indented within the context block:
```python
# ✅ CORRECT: Play call inside context manager
with self.voiceover(text="Here is the chaotic trajectory.") as tracker:
    self.play(
        path_tracker.animate.set_value(len(points) - 1),
        run_time=tracker.duration,
        rate_func=linear
    )
```

---

## 3. Cumulative Sub-Animation Timing Mismatch

### The Trap
Assigning full `tracker.duration` to multiple successive animations inside a single voiceover:
```python
# ❌ ANTI-PATTERN: Multiple animations each using full duration
with self.voiceover(text="We draw the axis and plot the function.") as tracker:
    self.play(Create(axes), run_time=tracker.duration)       # Takes full duration
    self.play(Create(graph), run_time=tracker.duration)      # Takes another full duration!
```

### Why It Fails
The total video segment runs for `2 * tracker.duration`. The audio finishes halfway through, leaving the second half of the visual sequence completely silent.

### Correct Pattern: Proportional Duration Partitioning
Explicitly partition the total `tracker.duration`:
```python
# ✅ CORRECT: Partition duration proportionally
with self.voiceover(text="We draw the axis and plot the function.") as tracker:
    self.play(Create(axes), run_time=tracker.duration * 0.35)
    self.play(Create(graph), run_time=tracker.duration * 0.65)
```

---

## 4. Python Method Resolution Order (MRO) in Multiple Inheritance

### The Trap
Inheriting `ThreeDScene` or `MovingCameraScene` before `VoiceoverScene`:
```python
# ❌ ANTI-PATTERN: Wrong inheritance order
class MyVisualLecture(ThreeDScene, VoiceoverScene):
    ...
```

### Why It Fails
Python evaluates method overrides from left to right. `ThreeDScene` initializes its own camera hooks and `construct` lifecycle without invoking `VoiceoverScene`'s speech service listeners if placed first, leading to unattached audio streams or silent export crashes.

### Correct Pattern
Always declare `VoiceoverScene` leftmost:
```python
# ✅ CORRECT: VoiceoverScene first in MRO
class MyVisualLecture(VoiceoverScene, ThreeDScene):
    def construct(self):
        self.set_speech_service(GTTSService())
        ...
```

---

## 5. Empty Geometry / Zero-Length Indexing on Frame 0

### The Trap
Initializing `tracker = ValueTracker(0)` and immediately slicing `points[:idx + 1]` without bounds checks when `idx == 0`:
```python
# ❌ ANTI-PATTERN: Slicing 1 or 0 points
def update_trajectory(mob):
    idx = int(tracker.get_value())
    # When idx == 0, points[:1] has only 1 point.
    # set_points_as_corners requires at least 2 points!
    mob.set_points_as_corners([axes.c2p(*p) for p in points[:idx + 1]])
```

### Why It Fails
Manim's `VMobject.set_points_as_corners` throws an internal geometry exception or silent empty bezier curve failure if given fewer than 2 points on the initial frame.

### Correct Pattern
Guard with `if idx > 1:`:
```python
# ✅ CORRECT: Safe index guard
def update_trajectory(mob):
    idx = int(tracker.get_value())
    if idx > 1:
        current_pts = [axes.c2p(*p) for p in points[:idx + 1]]
        mob.set_points_as_corners(current_pts)
```

---

## 6. 2D vs. 3D Camera Coordinate Conflicts

### The Trap
Adding 2D HUD text (like `Title` or `MathTex`) into a `ThreeDScene` without anchoring:
```python
# ❌ ANTI-PATTERN: Unanchored 2D titles in 3D camera
title = Title("Phase Space Dynamics")
self.add(title)
self.move_camera(phi=75 * DEGREES, theta=45 * DEGREES) # Title tilts into 3D space!
```

### Why It Fails
Standard `Mobjects` default to the world coordinate plane `z=0`. Rotating the 3D camera projects the text in 3D perspective, making titles distorted, clipped, or unreadable.

### Correct Pattern
Either fade out the 2D elements before transitioning to 3D, or use `add_fixed_in_frame_mobjects`:
```python
# ✅ CORRECT OPTION A: Fixed in camera HUD
title = Title("Phase Space Dynamics")
self.add_fixed_in_frame_mobjects(title)

# ✅ CORRECT OPTION B: Transition cleanly
self.play(FadeOut(title), run_time=tracker.duration * 0.3)
self.move_camera(phi=75 * DEGREES, theta=45 * DEGREES, run_time=tracker.duration * 0.7)
```

---

## 7. Coordinate Space Translation (`c2p`)

### The Trap
Passing raw NumPy coordinates directly to Manim `Mobjects`:
```python
# ❌ ANTI-PATTERN: Direct numpy coordinates
dot.move_to(points[idx]) # Places point in Manim frame units, not mathematical axes units!
```

### Why It Fails
SciPy solves differential equations in mathematical state space (e.g., $x \in [-20, 20], z \in [0, 50]$). Manim's screen default coordinates range roughly from $[-7, 7]$ on the X axis and $[-4, 4]$ on the Y axis. Without conversion, the animation renders completely off-screen.

### Correct Pattern
Always map via `axes.c2p(*point)` (coordinates to point):
```python
# ✅ CORRECT: Explicit axes mapping
dot.move_to(axes.c2p(*points[idx]))
```

---

## 8. Static AST Linting Rules for SFT Data Quality

Before any candidate Python script enters the SFT dataset, enforce the following AST rules programmatically:

| Rule ID | Check Description | AST Assertion |
|---------|-------------------|---------------|
| `AST-01` | No SciPy/NumPy compute calls inside updaters | Walk AST: No `Call` with `id` in `{'solve_ivp', 'odeint', 'minimize', 'curve_fit', 'fft'}` inside any `FunctionDef` whose name contains `'update'` or is passed to `add_updater`. |
| `AST-02` | MRO Ordering for Voiceover | In `ClassDef.bases`, if `VoiceoverScene` is present, it must precede `ThreeDScene` or `MovingCameraScene`. |
| `AST-03` | Speech Service Instantiation | If class inherits `VoiceoverScene`, `construct()` must contain a call to `self.set_speech_service(...)`. |
| `AST-04` | Non-empty Voiceover Context | `With` statements targeting `self.voiceover` must contain at least one `self.play(...)` call. |
| `AST-05` | ValueTracker updater boundary check | Updaters indexing coordinate arrays must contain an `If` comparison checking index > 0 or > 1. |
