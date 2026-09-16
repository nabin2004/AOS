# Manim Community Edition (ManimCE) — Complete Unified Skill Guide

> **Source:** Synthesized and unified from [`adithya-s-k/manim_skill`](https://github.com/adithya-s-k/manim_skill) (`manimce-best-practices`).
> **Target Engine:** Manim Community Edition (`manim` / ManimCE `>= v0.18.0`).
> **Purpose:** Single-file comprehensive cheatsheet and best-practices reference for creating high-quality, executable mathematical animations.

---

## Table of Contents

1. [Overview & Core Principles](#1-overview--core-principles)
2. [Scene Fundamentals & Runtime Configuration](#2-scene-fundamentals--runtime-configuration)
   - [2.1 Scene Construction (`rules/scenes.md`)](#21-scene-construction)
   - [2.2 Configuration & Flags (`rules/config.md`)](#22-configuration--flags)
   - [2.3 CLI Usage & Output Management (`rules/cli.md`)](#23-cli-usage--output-management)
   - [2.4 Timing, Pacing & Audio Sync (`rules/timing.md`)](#24-timing-pacing--audio-sync)
3. [Mobjects, Geometry & Styling](#3-mobjects-geometry--styling)
   - [3.1 Mobject Fundamentals (`rules/mobjects.md`)](#31-mobject-fundamentals)
   - [3.2 Positioning, Alignment & Coordinates (`rules/positioning.md`)](#32-positioning-alignment--coordinates)
   - [3.3 Grouping with VGroup (`rules/grouping.md`)](#33-grouping-with-vgroup)
   - [3.4 Colors & Palettes (`rules/colors.md`)](#34-colors--palettes)
   - [3.5 Visual Styling & Strokes (`rules/styling.md`)](#35-visual-styling--strokes)
   - [3.6 2D Shapes & Geometry (`rules/shapes.md`)](#36-2d-shapes--geometry)
   - [3.7 Lines, Vectors & Arrows (`rules/lines.md`)](#37-lines-vectors--arrows)
4. [Typography & Mathematical Notation](#4-typography--mathematical-notation)
   - [4.1 Plain Text & Fonts (`rules/text.md`)](#41-plain-text--fonts)
   - [4.2 LaTeX & MathTex (`rules/latex.md`)](#42-latex--mathtex)
   - [4.3 Text Animations & Highlighting (`rules/text-animations.md`)](#43-text-animations--highlighting)
5. [Coordinate Systems & Data Visualization](#5-coordinate-systems--data-visualization)
   - [5.1 Axes, NumberPlanes & Coordinate Conversion (`rules/axes.md`)](#51-axes-numberplanes--coordinate-conversion)
   - [5.2 Function Graphing, Plotting & Shading (`rules/graphing.md`)](#52-function-graphing-plotting--shading)
6. [3D Visualizations & Dynamic Camera](#6-3d-visualizations--dynamic-camera)
   - [6.1 ThreeDScene & 3D Objects (`rules/3d.md`)](#61-threedscene--3d-objects)
   - [6.2 MovingCameraScene & Viewport Control (`rules/camera.md`)](#62-movingcamerascene--viewport-control)
7. [Animation Engine & Dynamic Behaviors](#7-animation-engine--dynamic-behaviors)
   - [7.1 Core Animation Patterns (`rules/animations.md`)](#71-core-animation-patterns)
   - [7.2 Creation & Revealing Animations (`rules/creation-animations.md`)](#72-creation--revealing-animations)
   - [7.3 Transformations & Interpolations (`rules/transform-animations.md`)](#73-transformations--interpolations)
   - [7.4 Animation Groups, Successions & Staggering (`rules/animation-groups.md`)](#74-animation-groups-successions--staggering)
   - [7.5 Updaters & Continuous Value Tracking (`rules/updaters.md`)](#75-updaters--continuous-value-tracking)
8. [Starter Templates](#8-starter-templates)
   - [8.1 Basic Scene Template (`templates/basic_scene.py`)](#81-basic-scene-template)
   - [8.2 Camera Control Scene Template (`templates/camera_scene.py`)](#82-camera-control-scene-template)
   - [8.3 3D ThreeDScene Template (`templates/threed_scene.py`)](#83-3d-threedscene-template)
9. [End-to-End Implementation Examples](#9-end-to-end-implementation-examples)
   - [9.1 Basic Animation Sequences (`examples/basic_animations.py`)](#91-basic-animation-sequences)
   - [9.2 Mathematical Visualization (`examples/math_visualization.py`)](#92-mathematical-visualization)
   - [9.3 Function & Curve Plotting (`examples/graph_plotting.py`)](#93-function--curve-plotting)
   - [9.4 3D Mathematical Surfaces (`examples/3d_visualization.py`)](#94-3d-mathematical-surfaces)
   - [9.5 Dynamic Updaters & Tracker Patterns (`examples/updater_patterns.py`)](#95-dynamic-updaters--tracker-patterns)
   - [9.6 Lorenz Attractor Simulation (`examples/lorenz_attractor.py`)](#96-lorenz-attractor-simulation)

---

## 1. Overview & Core Principles

## How to use

Read individual rule files for detailed explanations and code examples:

### Core Concepts
- [rules/scenes.md](rules/scenes.md) - Scene structure, construct method, and scene types
- [rules/mobjects.md](rules/mobjects.md) - Mobject types, VMobject, Groups, and positioning
- [rules/animations.md](rules/animations.md) - Animation classes, playing animations, and timing

### Creation & Transformation
- [rules/creation-animations.md](rules/creation-animations.md) - Create, Write, FadeIn, DrawBorderThenFill
- [rules/transform-animations.md](rules/transform-animations.md) - Transform, ReplacementTransform, morphing
- [rules/animation-groups.md](rules/animation-groups.md) - AnimationGroup, LaggedStart, Succession

### Text & Math
- [rules/text.md](rules/text.md) - Text mobjects, fonts, and styling
- [rules/latex.md](rules/latex.md) - MathTex, Tex, LaTeX rendering, and coloring formulas
- [rules/text-animations.md](rules/text-animations.md) - Write, AddTextLetterByLetter, TypeWithCursor

### Styling & Appearance
- [rules/colors.md](rules/colors.md) - Color constants, gradients, and color manipulation
- [rules/styling.md](rules/styling.md) - Fill, stroke, opacity, and visual properties

### Positioning & Layout
- [rules/positioning.md](rules/positioning.md) - move_to, next_to, align_to, shift methods
- [rules/grouping.md](rules/grouping.md) - VGroup, Group, arrange, and layout patterns

### Coordinate Systems & Graphing
- [rules/axes.md](rules/axes.md) - Axes, NumberPlane, coordinate systems
- [rules/graphing.md](rules/graphing.md) - Plotting functions, parametric curves
- [rules/3d.md](rules/3d.md) - ThreeDScene, 3D axes, surfaces, camera orientation

### Animation Control
- [rules/timing.md](rules/timing.md) - Rate functions, easing, run_time, lag_ratio
- [rules/updaters.md](rules/updaters.md) - Updaters, ValueTracker, dynamic animations
- [rules/camera.md](rules/camera.md) - MovingCameraScene, zoom, pan, frame manipulation

### Configuration & CLI
- [rules/cli.md](rules/cli.md) - Command-line interface, rendering options, quality flags
- [rules/config.md](rules/config.md) - Configuration system, manim.cfg, settings

### Shapes & Geometry
- [rules/shapes.md](rules/shapes.md) - Circle, Square, Rectangle, Polygon, and geometric primitives
- [rules/lines.md](rules/lines.md) - Line, Arrow, Vector, DashedLine, and connectors

## Working Examples

Complete, tested example files demonstrating common patterns:

- [examples/basic_animations.py](examples/basic_animations.py) - Shape creation, text, lagged animations, path movement
- [examples/math_visualization.py](examples/math_visualization.py) - LaTeX equations, color-coded math, derivations
- [examples/updater_patterns.py](examples/updater_patterns.py) - ValueTracker, dynamic animations, physics simulations
- [examples/graph_plotting.py](examples/graph_plotting.py) - Axes, functions, areas, Riemann sums, polar plots
- [examples/3d_visualization.py](examples/3d_visualization.py) - ThreeDScene, surfaces, 3D camera, parametric curves

## Scene Templates

Copy and modify these templates to start new projects:

- [templates/basic_scene.py](templates/basic_scene.py) - Standard 2D scene template
- [templates/camera_scene.py](templates/camera_scene.py) - MovingCameraScene with zoom/pan
- [templates/threed_scene.py](templates/threed_scene.py) - 3D scene with surfaces and camera rotation

## Quick Reference

### Basic Scene Structure
```python
from manim import *

class MyScene(Scene):
    def construct(self):
        # Create mobjects
        circle = Circle()

        # Add to scene (static)
        self.add(circle)

        # Or animate
        self.play(Create(circle))

        # Wait
        self.wait(1)
```

### Render Command
```bash
# Basic render with preview
manim -pql scene.py MyScene

# Quality flags: -ql (low), -qm (medium), -qh (high), -qk (4k)
manim -pqh scene.py MyScene
```

### Key Differences from 3b1b/ManimGL

| Feature | Manim Community | 3b1b/ManimGL |
|---------|-----------------|--------------|
| Import | `from manim import *` | `from manimlib import *` |
| CLI | `manim` | `manimgl` |
| Math text | `MathTex(r"\pi")` | `Tex(R"\pi")` |
| Scene | `Scene` | `InteractiveScene` |
| Package | `manim` (PyPI) | `manimgl` (PyPI) |

### Jupyter Notebook Support

Use the `%%manim` cell magic:

```python
%%manim -qm MyScene
class MyScene(Scene):
    def construct(self):
        self.play(Create(Circle()))
```

### Common Pitfalls to Avoid

1. **Version confusion** - Ensure you're using `manim` (Community), not `manimgl` (3b1b version)
2. **Check imports** - `from manim import *` is ManimCE; `from manimlib import *` is ManimGL
3. **Outdated tutorials** - Video tutorials may be outdated; prefer official documentation
4. **manimpango issues** - If text rendering fails, check manimpango installation requirements
5. **PATH issues (Windows)** - If `manim` command not found, use `python -m manim` or check PATH

### Installation

```bash
# Install Manim Community
pip install manim

# Check installation
manim checkhealth
```

### Useful Commands

```bash
manim -pql scene.py Scene    # Preview low quality (development)
manim -pqh scene.py Scene    # Preview high quality
manim --format gif scene.py  # Output as GIF
manim checkhealth            # Verify installation
manim plugins -l             # List plugins
```

---

## 2. Scene Fundamentals & Runtime Configuration

### 2.1 Scene Construction

*Source: `rules/scenes.md`*

# Scenes in Manim

A Scene is the canvas where all animations take place. Every Manim animation is defined within a Scene class.

## Basic Scene Structure

All animation code resides within the `construct()` method of a Scene subclass.

```python
from manim import *

class MyScene(Scene):
    def construct(self):
        circle = Circle()
        self.play(Create(circle))
        self.wait(1)
```

## Scene Lifecycle Methods

### construct()
The main method where you define your animation. Called automatically when rendering.

### setup()
Called before `construct()`. Use for initialization that should happen before animation logic.

```python
class MyScene(Scene):
    def setup(self):
        self.camera.background_color = BLUE_E

    def construct(self):
        circle = Circle()
        self.play(Create(circle))
```

## Scene Methods

### Adding and Removing Objects

```python
# Add without animation (instant)
self.add(mobject)
self.add(mobject1, mobject2, mobject3)

# Remove without animation
self.remove(mobject)

# Clear all mobjects
self.clear()
```

### Playing Animations

```python
# Play a single animation
self.play(Create(circle))

# Play multiple animations simultaneously
self.play(Create(circle), FadeIn(square))

# With run_time
self.play(Create(circle), run_time=2)
```

### Waiting

```python
# Wait for 1 second (default)
self.wait()

# Wait for specific duration
self.wait(2)
```

## Scene Types

### Scene (Default)
Standard 2D scene for most animations.

### ThreeDScene
For 3D animations with camera orientation control.

```python
class My3DScene(ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=75 * DEGREES, theta=-45 * DEGREES)
        axes = ThreeDAxes()
        sphere = Sphere()
        self.add(axes, sphere)
```

### MovingCameraScene
For animations that require camera movement (zoom, pan).

```python
class ZoomScene(MovingCameraScene):
    def construct(self):
        circle = Circle()
        self.add(circle)
        self.play(self.camera.frame.animate.scale(0.5).move_to(circle))
```

## Multiple Scenes in One File

Render specific scene:
```bash
manim -pql file.py Scene1
```

Render all scenes:
```bash
manim -pql -a file.py
```

### 2.2 Configuration & Flags

*Source: `rules/config.md`*

# Configuration

Configure Manim's behavior through files and code.

## Configuration Hierarchy

Manim reads configuration from (in order of precedence):
1. Command-line arguments (highest priority)
2. User's `manim.cfg` in current directory
3. User's global config
4. Default values (lowest priority)

## manim.cfg File

Create a `manim.cfg` file in your project directory:

```ini
[CLI]
# Preview after rendering
preview = True

# Default quality
quality = medium_quality

# Output format
format = mp4

# Frame rate
frame_rate = 30

[output]
# Custom output directory
media_dir = ./media

# Save last frame as PNG
save_last_frame = False

[renderer]
# Background color
background_color = BLACK

[style]
# Default font
font = Arial
```

## Common Configuration Options

### CLI Section

```ini
[CLI]
# Quality presets: low_quality, medium_quality, high_quality, production_quality, fourk_quality
quality = medium_quality

# Preview video after rendering
preview = True

# Frame rate
frame_rate = 30

# Output format: mp4, gif, mov, webm, png
format = mp4

# Transparent background
transparent = False

# Progress bar: display, leave, none
progress_bar = display
```

### Rendering Section

```ini
[renderer]
# Background color (hex or color name)
background_color = #1e1e1e

# Renderer type: cairo, opengl
renderer = cairo
```

### Resolution

```ini
[CLI]
# Frame dimensions
pixel_width = 1920
pixel_height = 1080
```

## Programmatic Configuration

Access and modify config in your Python code:

```python
# Access config values
config.pixel_width  # e.g., 1920
config.frame_rate  # e.g., 30
config.background_color  # e.g., BLACK

# Modify config (before creating scenes)
config.pixel_width = 1920
config.pixel_height = 1080
config.frame_rate = 60
config.background_color = BLUE_E
```

### In Scene

```python
class MyScene(Scene):
    def construct(self):
        # Access frame dimensions
        width = config.frame_width
        height = config.frame_height

        # Create rectangle matching frame size
        frame_rect = Rectangle(
            width=width,
            height=height,
            stroke_color=WHITE
        )
        self.add(frame_rect)
```

## Background Color

### In Config File

```ini
[renderer]
background_color = BLACK
# Or hex color
background_color = #1a1a2e
```

### In Code

```python
class DarkBackground(Scene):
    def construct(self):
        self.camera.background_color = "#1a1a2e"
        # ... rest of scene
```

## Output Directory Structure

Default media directory structure:
```
media/
├── videos/
│   └── scene_file/
│       ├── 480p15/       # Low quality
│       ├── 720p30/       # Medium quality
│       ├── 1080p60/      # High quality
│       └── 2160p60/      # 4K quality
├── images/
│   └── scene_file/
│       └── SceneName.png
└── Tex/                  # LaTeX cache
```

### Custom Output Directory

```ini
[output]
media_dir = ./output
```

Or via CLI:
```bash
manim --media_dir ./output file.py Scene
```

## Tex Configuration

For LaTeX rendering:

```ini
[tex]
# Custom preamble
preamble = \usepackage{amsmath}\usepackage{amssymb}

# Tex compiler
tex_compiler = latex
```

## Caching

```ini
[CLI]
# Disable caching (useful for debugging)
disable_caching = True

# Max cached files
max_files_cached = 100
```

## Viewing Current Config

```bash
# Show all config values
manim cfg show

# Show specific section
manim cfg show CLI

# Write current config to file
manim cfg write
```

## Project-Specific Config

Create `manim.cfg` in your project root:

```ini
[CLI]
quality = high_quality
preview = True
frame_rate = 60

[renderer]
background_color = #0d1117

[output]
media_dir = ./renders
```

## Plugins

Manim has an extensible plugin system:

```bash
# List installed plugins
manim plugins -l

# Install a plugin
pip install manim-pluginname
```

Enable plugins in `manim.cfg`:

```ini
[CLI]
plugins = manim-pluginname
# For multiple plugins:
plugins = plugin1,plugin2
```

## Best Practices

1. **Use manim.cfg for project defaults** - Consistent settings across team
2. **Keep quality low during development** - Faster iteration
3. **Set background_color in config** - Not in every scene
4. **Use custom media_dir** - Keep renders organized
5. **Commit manim.cfg to version control** - Share settings with collaborators

### 2.3 CLI Usage & Output Management

*Source: `rules/cli.md`*

# Manim CLI

The `manim` command-line interface for rendering scenes.

## Basic Usage

```bash
# Render a scene
manim file.py SceneName

# With preview (opens video after rendering)
manim -p file.py SceneName

# Preview with low quality (fast)
manim -pql file.py SceneName
```

## Quality Flags

Quality presets for different use cases:

```bash
# Low Quality: 854x480, 15fps (fast for testing)
manim -ql file.py SceneName

# Medium Quality: 1280x720, 30fps
manim -qm file.py SceneName

# High Quality: 1920x1080, 60fps
manim -qh file.py SceneName

# 2K Quality: 2560x1440, 60fps
manim -qp file.py SceneName

# 4K Quality: 3840x2160, 60fps
manim -qk file.py SceneName
```

### Common Combinations

```bash
# Preview + Low Quality (development workflow)
manim -pql file.py SceneName

# Preview + High Quality (final check)
manim -pqh file.py SceneName
```

## Preview Flag

```bash
# -p: Open video after rendering
manim -p file.py SceneName

# Without -p: Render only (no auto-open)
manim file.py SceneName
```

## Rendering Multiple Scenes

```bash
# Render all scenes in file
manim -a file.py

# Render specific scenes
manim file.py Scene1 Scene2 Scene3
```

## Output Options

### Save Last Frame Only

```bash
# -s: Save only the last frame as PNG
manim -s file.py SceneName

# With quality
manim -sql file.py SceneName
```

### Output Format

```bash
# GIF output
manim --format gif file.py SceneName

# PNG sequence
manim --format png file.py SceneName

# WebM (default is MP4)
manim --format webm file.py SceneName
```

### Custom Output Directory

```bash
manim -o custom_name file.py SceneName
manim --media_dir /path/to/output file.py SceneName
```

## Frame Control

```bash
# Start from specific animation number
manim -n 5 file.py SceneName

# Render frames from animation 3 to 7
manim -n 3,7 file.py SceneName
```

## Resolution and FPS

```bash
# Custom resolution
manim -r 1920,1080 file.py SceneName

# Custom frame rate
manim --fps 24 file.py SceneName

# Both
manim -r 1280,720 --fps 30 file.py SceneName
```

## Transparency

```bash
# Render with transparent background
manim -t file.py SceneName
```

## Renderer Selection

```bash
# Cairo renderer (default, 2D)
manim --renderer cairo file.py SceneName

# OpenGL renderer (3D, faster preview)
manim --renderer opengl file.py SceneName
```

## Other Useful Flags

```bash
# Verbose output
manim -v DEBUG file.py SceneName

# Quiet mode
manim -v WARNING file.py SceneName

# Show progress bar
manim --progress_bar display file.py SceneName

# Disable caching
manim --disable_caching file.py SceneName

# Write to movie even if no animations
manim --write_to_movie file.py SceneName
```

## Help

```bash
# Show all options
manim --help

# Show render command options
manim render --help
```

## Other Commands

```bash
# Check installation and dependencies
manim checkhealth

# Initialize new project
manim init

# Show config values
manim cfg show

# Write current config to file
manim cfg write

# List installed plugins
manim plugins -l
```

## Jupyter Notebook Support

Use the `%%manim` cell magic in Jupyter notebooks:

```python
%%manim -qm -v WARNING MyScene
class MyScene(Scene):
    def construct(self):
        circle = Circle()
        self.play(Create(circle))
```

Flags work the same as CLI (`-qm`, `-ql`, etc.).

## Typical Development Workflow

```bash
# 1. Develop with fast preview
manim -pql scene.py MyScene

# 2. Check at medium quality
manim -pqm scene.py MyScene

# 3. Final render at high quality
manim -qh scene.py MyScene

# 4. Create GIF for sharing
manim --format gif -qm scene.py MyScene
```

## Best Practices

1. **Use -pql for development** - Fast iteration cycle
2. **Use -qh for final output** - Good quality, reasonable render time
3. **Use -s for thumbnails** - Quick last-frame capture
4. **Use -a sparingly** - Renders everything, can be slow
5. **Use --format gif for demos** - Easy to share and embed

### 2.4 Timing, Pacing & Audio Sync

*Source: `rules/timing.md`*

# Animation Timing

Control the speed and feel of animations with timing parameters.

## run_time

Controls how long an animation takes in seconds.

```python
from manim import *

class RunTimeExample(Scene):
    def construct(self):
        circle = Circle()

        # Default (1 second)
        self.play(Create(circle))

        # Longer animation
        self.play(circle.animate.shift(RIGHT), run_time=3)

        # Quick animation
        self.play(circle.animate.set_color(RED), run_time=0.5)
```

## Rate Functions

Rate functions control how the animation progresses over time (easing).

### Using Rate Functions

```python
self.play(
    circle.animate.shift(RIGHT),
    rate_func=smooth
)
```

### Common Rate Functions

```python
# Smooth start and end (default for most animations)
smooth

# Constant speed
linear

# Start slow, end fast
rush_into

# Start fast, end slow
rush_from

# Go there and back
there_and_back

# Go there and back with pause
there_and_back_with_pause

# Double smooth (extra smooth)
double_smooth

# Stay put (useful for delays in AnimationGroup)
lingering
```

### Ease Functions (CSS-like)

```python
# Ease in (start slow)
ease_in_sine
ease_in_quad
ease_in_cubic
ease_in_expo
ease_in_circ
ease_in_back    # Slight overshoot at start

# Ease out (end slow)
ease_out_sine
ease_out_quad
ease_out_cubic
ease_out_expo
ease_out_circ
ease_out_back   # Slight overshoot at end
ease_out_bounce # Bouncy ending

# Ease in-out (slow at both ends)
ease_in_out_sine
ease_in_out_quad
ease_in_out_cubic
ease_in_out_expo
ease_in_out_circ
ease_in_out_back
```

## Visual Comparison

```python
class RateFuncComparison(Scene):
    def construct(self):
        funcs = [linear, smooth, rush_into, rush_from, there_and_back]
        names = ["linear", "smooth", "rush_into", "rush_from", "there_and_back"]

        dots = VGroup()
        labels = VGroup()

        for i, (func, name) in enumerate(zip(funcs, names)):
            dot = Dot().shift(LEFT * 4 + DOWN * i)
            label = Text(name, font_size=24).next_to(dot, LEFT)
            dots.add(dot)
            labels.add(label)

        self.add(dots, labels)

        self.play(*[
            dot.animate(rate_func=func).shift(RIGHT * 8)
            for dot, func in zip(dots, funcs)
        ], run_time=3)
```

## Combining run_time and rate_func

```python
self.play(
    square.animate.shift(RIGHT * 3),
    run_time=2,
    rate_func=ease_out_bounce
)
```

## there_and_back

Animation goes forward then reverses.

```python
class ThereAndBackExample(Scene):
    def construct(self):
        square = Square()
        self.add(square)

        # Moves right then back to start
        self.play(
            square.animate.shift(RIGHT * 2),
            rate_func=there_and_back,
            run_time=2
        )
```

## Custom Rate Functions

Create your own rate function (takes t from 0 to 1, returns progress 0 to 1):

```python
def my_rate_func(t):
    # Quadratic ease
    return t ** 2

self.play(
    circle.animate.shift(RIGHT),
    rate_func=my_rate_func
)
```

## wait() Timing

```python
# Wait for default time (1 second)
self.wait()

# Wait for specific duration
self.wait(2)    # 2 seconds
self.wait(0.5)  # Half second
```

## Animation Speed Multiplier

Using `run_time` on AnimationGroup affects all children:

```python
self.play(AnimationGroup(
    Create(circle),
    Create(square),
    lag_ratio=0.5
), run_time=3)  # Total duration is 3 seconds
```

## Best Practices

1. **Use smooth for most animations** - Looks natural
2. **Use linear for constant motion** - Mechanical/precise movement
3. **Use ease_out_bounce for playful effects** - Attention-grabbing
4. **Keep run_time between 0.5-3 seconds** - Maintain viewer attention
5. **Use there_and_back for emphasis** - Show something temporarily
6. **Match rate_func to content** - Smooth for elegant, bouncy for fun

---

## 3. Mobjects, Geometry & Styling

### 3.1 Mobject Fundamentals

*Source: `rules/mobjects.md`*

# Mobjects in Manim

Mobject (Mathematical Object) is the base class for all displayable objects in Manim.

## Mobject Hierarchy

```
Mobject (base class)
├── VMobject (Vectorized Mobject - most common)
│   ├── Circle, Square, Rectangle, Polygon
│   ├── Line, Arrow, Vector
│   ├── Text, MathTex, Tex
│   ├── Axes, NumberPlane
│   └── VGroup
├── ImageMobject (for images)
├── PMobject (point clouds)
└── Group (for non-VMobject collections)
```

## VMobject (Vectorized Mobject)

Most shapes you'll use are VMobjects - they're defined by Bézier curves.

```python
# Common VMobjects
circle = Circle()
square = Square()
rect = Rectangle(width=4, height=2)
triangle = Triangle()
polygon = Polygon(ORIGIN, RIGHT, UP)
line = Line(LEFT, RIGHT)
arrow = Arrow(LEFT, RIGHT)
```

## Creating Custom VMobjects

```python
class CustomShape(VMobject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Define points using set_points_as_corners or set_points_smoothly
        self.set_points_as_corners([
            LEFT, UP, RIGHT, DOWN, LEFT
        ])
```

## Mobject Properties

### Position and Size

```python
mobject.get_center()      # Returns center point
mobject.get_width()       # Returns width
mobject.get_height()      # Returns height
mobject.get_top()         # Top edge center point
mobject.get_bottom()      # Bottom edge center point
mobject.get_left()        # Left edge center point
mobject.get_right()       # Right edge center point
```

### Bounding Box Corners

```python
mobject.get_corner(UL)    # Upper left corner
mobject.get_corner(UR)    # Upper right corner
mobject.get_corner(DL)    # Lower left corner
mobject.get_corner(DR)    # Lower right corner
```

## Submobjects

Mobjects can contain other mobjects as submobjects.

```python
# Access submobjects
group = VGroup(Circle(), Square())
group.submobjects      # List of child mobjects
group[0]               # First submobject (Circle)
group[1]               # Second submobject (Square)

# Iterate over submobjects
for mob in group:
    mob.set_color(RED)
```

## Copying Mobjects

```python
# Create a copy
circle_copy = circle.copy()

# Copy and position
circle_copy = circle.copy().shift(RIGHT * 2)
```

## Method Chaining

Most mobject methods return `self`, allowing method chaining:

```python
circle = Circle().set_color(RED).shift(LEFT).scale(2)
```

## Best Practices

1. **Use VMobject for custom shapes** - Better rendering and animation support
2. **Prefer VGroup over Group** - VGroup works better with most animations
3. **Use copy() when reusing** - Avoid unintended modifications to original
4. **Chain methods for readability** - But break into lines if too long

### 3.2 Positioning, Alignment & Coordinates

*Source: `rules/positioning.md`*

# Positioning in Manim

Methods for placing and moving mobjects in the scene.

## Coordinate System

Manim uses a coordinate system where:
- Origin (0, 0, 0) is at the center of the screen
- X-axis: LEFT (-) to RIGHT (+)
- Y-axis: DOWN (-) to UP (+)
- Z-axis: IN (-) to OUT (+) (for 3D)

### Direction Constants
```python
UP = np.array([0, 1, 0])
DOWN = np.array([0, -1, 0])
LEFT = np.array([-1, 0, 0])
RIGHT = np.array([1, 0, 0])
ORIGIN = np.array([0, 0, 0])

# Diagonals
UL = UP + LEFT      # Upper left
UR = UP + RIGHT     # Upper right
DL = DOWN + LEFT    # Lower left
DR = DOWN + RIGHT   # Lower right
```

## move_to

Move to an absolute position.

```python
from manim import *

class MoveToExample(Scene):
    def construct(self):
        circle = Circle()

        # Move to origin
        circle.move_to(ORIGIN)

        # Move to specific coordinates
        circle.move_to(RIGHT * 2 + UP * 1)

        # Move to another mobject's position
        square = Square().shift(LEFT * 2)
        circle.move_to(square)

        # Move to a specific point of another mobject
        circle.move_to(square.get_top())
```

## shift

Move relative to current position.

```python
class ShiftExample(Scene):
    def construct(self):
        circle = Circle()

        # Shift in one direction
        circle.shift(RIGHT)
        circle.shift(UP * 2)

        # Shift in multiple directions
        circle.shift(RIGHT * 2 + UP * 1)

        # Chain shifts
        circle.shift(LEFT).shift(DOWN)
```

## next_to

Position relative to another mobject.

```python
class NextToExample(Scene):
    def construct(self):
        square = Square()
        circle = Circle()
        triangle = Triangle()

        # Place circle to the right of square
        circle.next_to(square, RIGHT)

        # With buffer (spacing)
        triangle.next_to(square, DOWN, buff=0.5)

        # Aligned to specific edge
        circle.next_to(square, RIGHT, aligned_edge=UP)
```

### buff Parameter
```python
# Default buffer
circle.next_to(square, RIGHT)  # Uses DEFAULT_MOBJECT_TO_MOBJECT_BUFFER

# Custom buffer
circle.next_to(square, RIGHT, buff=0)    # No gap
circle.next_to(square, RIGHT, buff=1)    # 1 unit gap
circle.next_to(square, RIGHT, buff=0.5)  # Half unit gap
```

## align_to

Align edges with another mobject.

```python
class AlignToExample(Scene):
    def construct(self):
        square = Square().shift(LEFT)
        circle = Circle().shift(RIGHT)

        # Align circle's left edge with square's left edge
        circle.align_to(square, LEFT)

        # Align tops
        circle.align_to(square, UP)

        # Align to a point
        circle.align_to(ORIGIN, DOWN)
```

## Edge Methods

Position at screen edges.

```python
class EdgeExample(Scene):
    def construct(self):
        # To screen edges
        text1 = Text("Top").to_edge(UP)
        text2 = Text("Bottom").to_edge(DOWN)
        text3 = Text("Left").to_edge(LEFT)
        text4 = Text("Right").to_edge(RIGHT)

        # With buffer
        text5 = Text("Buffered").to_edge(UP, buff=1)
```

## Corner Methods

Position at screen corners.

```python
class CornerExample(Scene):
    def construct(self):
        t1 = Text("UL").to_corner(UL)
        t2 = Text("UR").to_corner(UR)
        t3 = Text("DL").to_corner(DL)
        t4 = Text("DR").to_corner(DR)

        # With buffer
        t5 = Text("Buffered").to_corner(UL, buff=0.5)
```

## center

Center on screen or another mobject.

```python
mobject.center()           # Center on screen
mobject.center_on(other)   # Center on another mobject (custom helper)
```

## Getting Positions

```python
circle = Circle()

# Get various points
circle.get_center()        # Center point
circle.get_top()           # Top edge center
circle.get_bottom()        # Bottom edge center
circle.get_left()          # Left edge center
circle.get_right()         # Right edge center
circle.get_corner(UL)      # Upper left corner
circle.get_corner(DR)      # Lower right corner
circle.get_start()         # Start of path
circle.get_end()           # End of path
```

## Animated Positioning

```python
class AnimatedPosition(Scene):
    def construct(self):
        square = Square()
        self.add(square)

        # Animate movement
        self.play(square.animate.shift(RIGHT * 2))
        self.play(square.animate.move_to(UP * 2))
        self.play(square.animate.to_edge(LEFT))
```

## Best Practices

1. **Use next_to for relative positioning** - Maintains relationships
2. **Use move_to for absolute positioning** - Precise coordinates
3. **Use shift for relative adjustments** - Quick tweaks
4. **Use to_edge/to_corner for screen positioning** - Responsive layouts
5. **Adjust buff for visual spacing** - Don't let elements crowd

### 3.3 Grouping with VGroup

*Source: `rules/grouping.md`*

# Grouping Mobjects

Organize multiple mobjects into groups for collective manipulation.

## VGroup

VGroup (Vectorized Group) is for grouping VMobjects. Most commonly used.

```python
from manim import *

class VGroupExample(Scene):
    def construct(self):
        # Create a group
        group = VGroup(
            Circle(),
            Square(),
            Triangle()
        )

        # Operations apply to all members
        group.set_color(RED)
        group.shift(UP)

        self.add(group)
```

## Group

Group is for mixing different mobject types (VMobjects, ImageMobjects, etc.).

```python
class GroupExample(Scene):
    def construct(self):
        # Mix different types
        text = Text("Hello")
        group = Group(
            Circle(),
            text
        )
        self.add(group)
```

## Creating Groups

```python
# From individual mobjects
group = VGroup(circle, square, triangle)

# From a list
shapes = [Circle(), Square(), Triangle()]
group = VGroup(*shapes)

# Using list comprehension
group = VGroup(*[Circle() for _ in range(5)])

# Empty group, add later
group = VGroup()
group.add(Circle())
group.add(Square())
```

## arrange

Arrange mobjects in a line.

```python
class ArrangeExample(Scene):
    def construct(self):
        # Horizontal arrangement (default)
        row = VGroup(*[Circle().scale(0.3) for _ in range(5)])
        row.arrange(RIGHT, buff=0.5).shift(UP * 2)

        # Vertical arrangement
        column = VGroup(*[Square().scale(0.3) for _ in range(4)])
        column.arrange(DOWN, buff=0.5).shift(LEFT * 2)

        # With custom buffer
        spaced = VGroup(*[Triangle().scale(0.3) for _ in range(3)])
        spaced.arrange(RIGHT, buff=1).shift(DOWN * 2)

        self.add(row, column, spaced)
```

### Direction Options
```python
group.arrange(RIGHT)      # Left to right
group.arrange(LEFT)       # Right to left
group.arrange(UP)         # Bottom to top
group.arrange(DOWN)       # Top to bottom
```

## arrange_in_grid

Arrange in a grid pattern.

```python
class GridExample(Scene):
    def construct(self):
        # Auto grid
        grid = VGroup(*[Square().scale(0.3) for _ in range(20)])
        grid.arrange_in_grid()

        # Specify rows and columns
        grid = VGroup(*[Circle().scale(0.2) for _ in range(12)])
        grid.arrange_in_grid(rows=3, cols=4)

        # With spacing
        grid.arrange_in_grid(rows=3, cols=4, buff=0.5)

        self.add(grid)
```

## Accessing Group Members

```python
group = VGroup(Circle(), Square(), Triangle())

# By index
first = group[0]          # Circle
second = group[1]         # Square
last = group[-1]          # Triangle

# Slicing
first_two = group[0:2]    # VGroup with Circle and Square

# Iteration
for mob in group:
    mob.set_color(random_color())

# Length
num_items = len(group)
```

## Modifying Groups

```python
group = VGroup(Circle(), Square())

# Add mobjects
group.add(Triangle())
group.add(Star(), Pentagon())

# Remove mobjects
group.remove(circle)

# Insert at position
group.insert(0, new_mobject)

# Submobjects list
group.submobjects  # List of all children
```

## Group Transformations

```python
group = VGroup(Circle(), Square(), Triangle()).arrange(RIGHT)

# All transformations apply to entire group
group.shift(UP * 2)
group.scale(0.5)
group.rotate(PI / 4)
group.set_color(BLUE)

# But can target individuals
group[0].set_color(RED)  # Just the circle
```

## Nested Groups

```python
class NestedGroups(Scene):
    def construct(self):
        # Create sub-groups
        row1 = VGroup(*[Circle() for _ in range(3)]).arrange(RIGHT)
        row2 = VGroup(*[Square() for _ in range(3)]).arrange(RIGHT)
        row3 = VGroup(*[Triangle() for _ in range(3)]).arrange(RIGHT)

        # Group of groups
        all_rows = VGroup(row1, row2, row3).arrange(DOWN)

        self.add(all_rows)
```

## Useful Group Methods

```python
group = VGroup(Circle(), Square(), Triangle())

# Get bounding box info
group.get_center()
group.get_width()
group.get_height()

# Set position for whole group
group.move_to(ORIGIN)
group.to_edge(LEFT)

# Copy entire group
group_copy = group.copy()

# Match layout of another group
group1.match_height(group2)
group1.match_width(group2)
```

## Best Practices

1. **Use VGroup for VMobjects** - Better performance and compatibility
2. **Use arrange after creating** - Don't position individually then group
3. **Name your groups semantically** - `equation_parts` not `group1`
4. **Use nested groups for structure** - Rows within columns, etc.
5. **Copy groups when needed** - Avoid unintended modifications

### 3.4 Colors & Palettes

*Source: `rules/colors.md`*

# Colors in Manim

Manim provides predefined color constants and supports custom colors.

## Color Constants

### Primary Colors
```python
RED, GREEN, BLUE
YELLOW, ORANGE, PINK, PURPLE
WHITE, BLACK, GREY (or GRAY)
```

### Color Variants (Shades)
Most colors have variants from `_A` (lightest) to `_E` (darkest):
```python
BLUE_A, BLUE_B, BLUE_C, BLUE_D, BLUE_E
RED_A, RED_B, RED_C, RED_D, RED_E
GREEN_A, GREEN_B, GREEN_C, GREEN_D, GREEN_E
GREY_A, GREY_B, GREY_C, GREY_D, GREY_E
```

### Common Named Colors
```python
TEAL, TEAL_A, TEAL_B, TEAL_C, TEAL_D, TEAL_E
GOLD, GOLD_A, GOLD_B, GOLD_C, GOLD_D, GOLD_E
MAROON, MAROON_A, MAROON_B, MAROON_C, MAROON_D, MAROON_E
PURPLE, PURPLE_A, PURPLE_B, PURPLE_C, PURPLE_D, PURPLE_E
```

### Special Colors
```python
PURE_RED, PURE_GREEN, PURE_BLUE  # RGB primaries
LIGHT_GREY, DARK_GREY
LIGHTER_GREY, DARKER_GREY
LIGHT_BROWN, DARK_BROWN
```

## Using Colors

### Setting Color on Creation
```python
circle = Circle(color=RED)
square = Square(color=BLUE, fill_color=GREEN, fill_opacity=0.5)
text = Text("Hello", color=YELLOW)
```

### Setting Color After Creation
```python
circle = Circle()
circle.set_color(RED)
```

## Hex Colors

```python
# Use hex strings
circle = Circle(color="#FF5733")
square = Square(color="#2ECC71")

# RGB values (0-1 range)
from manim import rgb_to_color
custom = rgb_to_color([0.5, 0.2, 0.8])
```

## Fill vs Stroke Color

```python
square = Square()
square.set_fill(RED, opacity=0.8)      # Interior color
square.set_stroke(BLUE, width=4)       # Border color
```

### Combined Styling
```python
square = Square(
    color=BLUE,            # Sets both fill and stroke
    fill_opacity=0.5,      # Fill transparency
    stroke_width=4         # Border thickness
)
```

## Gradients

### Color Gradient on Mobject
```python
text = Text("GRADIENT")
text.set_color_by_gradient(RED, YELLOW, GREEN)
```

### Gradient Along Path
```python
line = Line(LEFT * 3, RIGHT * 3)
line.set_color_by_gradient(BLUE, GREEN, YELLOW)
```

## Color Interpolation

Create colors between two colors:

```python
from manim import interpolate_color

# Get color halfway between RED and BLUE
mid_color = interpolate_color(RED, BLUE, 0.5)

# Create a range of colors
colors = [interpolate_color(RED, BLUE, alpha) for alpha in np.linspace(0, 1, 10)]
```

## ManimColor Class

For advanced color manipulation, use ManimColor directly:

```python
from manim import ManimColor

# Create from various formats
color1 = ManimColor("#FF0000")           # From hex
color2 = ManimColor((0.0, 1.0, 0.5))     # From RGB floats (0-1)
color3 = ManimColor([255, 165, 0])       # From RGB ints (0-255)

# Color manipulation methods
lighter = color1.lighter()               # Lighter version
darker = color1.darker()                 # Darker version
inverted = color1.invert()               # Inverted color
with_alpha = color1.opacity(0.5)         # With 50% opacity

# Convert formats
hex_str = color1.to_hex()                # To hex string
rgb = color1.to_rgb()                    # To RGB float array
hsv = color1.to_hsv()                    # To HSV array

# Interpolation
mixed = color1.interpolate(color2, 0.5)  # Blend two colors
```

## Opacity

```python
# Set opacity (0 = transparent, 1 = opaque)
circle = Circle(fill_opacity=0.5, stroke_opacity=0.8)

# Modify opacity
circle.set_opacity(0.5)         # Both fill and stroke
circle.set_fill_opacity(0.7)    # Fill only
circle.set_stroke_opacity(0.3)  # Stroke only
```

## Color by Value

Color mobjects based on a value (useful for data visualization):

```python
class ColorByValue(Scene):
    def construct(self):
        dots = VGroup(*[Dot() for _ in range(10)]).arrange(RIGHT)

        for i, dot in enumerate(dots):
            # Color from blue (cold) to red (hot)
            dot.set_color(interpolate_color(BLUE, RED, i / 9))

        self.add(dots)
```

## Random Colors

```python
from manim import random_color, random_bright_color

circle = Circle(color=random_color())
square = Square(color=random_bright_color())
```

## Color Lists for Animations

```python
class ColorCycle(Scene):
    def construct(self):
        circle = Circle()
        self.add(circle)

        colors = [RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE]
        for color in colors:
            self.play(circle.animate.set_color(color), run_time=0.5)
```

## Best Practices

1. **Use color variants for depth** - `BLUE_E` for shadows, `BLUE_A` for highlights
2. **Maintain color consistency** - Use the same colors for related concepts
3. **Use opacity for layering** - Semi-transparent fills show overlapping
4. **Consider colorblind accessibility** - Avoid red-green only distinctions
5. **Use gradients sparingly** - They can be distracting

### 3.5 Visual Styling & Strokes

*Source: `rules/styling.md`*

# Styling Mobjects

Control the visual appearance of mobjects with fill, stroke, and opacity settings.

## Fill Properties

Fill controls the interior of shapes.

```python
from manim import *

class FillExample(Scene):
    def construct(self):
        # Set fill on creation
        circle = Circle(fill_color=BLUE, fill_opacity=0.8)

        # Set fill after creation
        square = Square()
        square.set_fill(RED, opacity=0.5)

        self.add(circle, square)
```

### Fill Methods
```python
mobject.set_fill(color=RED)                    # Color only
mobject.set_fill(RED, opacity=0.5)             # Color and opacity
mobject.set_fill(opacity=0.5)                  # Opacity only
mobject.set_fill_color(RED)                    # Color only (alternative)
mobject.set_fill_opacity(0.5)                  # Opacity only (alternative)
```

## Stroke Properties

Stroke controls the outline/border of shapes.

```python
class StrokeExample(Scene):
    def construct(self):
        # Set stroke on creation
        circle = Circle(stroke_color=BLUE, stroke_width=4)

        # Set stroke after creation
        square = Square()
        square.set_stroke(RED, width=8)

        self.add(circle, square)
```

### Stroke Methods
```python
mobject.set_stroke(color=RED)                  # Color only
mobject.set_stroke(RED, width=4)               # Color and width
mobject.set_stroke(width=4)                    # Width only
mobject.set_stroke(opacity=0.5)                # Opacity only
mobject.set_stroke_color(RED)                  # Color only (alternative)
mobject.set_stroke_width(4)                    # Width only (alternative)
mobject.set_stroke_opacity(0.5)                # Opacity only (alternative)
```

### Stroke Width Reference
```python
# Common stroke widths
DEFAULT_STROKE_WIDTH = 4
thin = 1
normal = 4
thick = 8
very_thick = 12
```

## Combined Styling

```python
class CombinedStyling(Scene):
    def construct(self):
        square = Square()
        square.set_fill(BLUE, opacity=0.5)
        square.set_stroke(YELLOW, width=6)
        self.add(square)
```

### Method Chaining
```python
square = Square().set_fill(RED, 0.5).set_stroke(WHITE, 4)
```

## The set_style Method

Set multiple style properties at once:

```python
square = Square()
square.set_style(
    fill_color=BLUE,
    fill_opacity=0.5,
    stroke_color=WHITE,
    stroke_width=4,
    stroke_opacity=1
)
```

## Opacity

Control transparency of mobjects:

```python
# Overall opacity
mobject.set_opacity(0.5)  # Affects both fill and stroke

# Separate opacities
mobject.set_fill_opacity(0.8)
mobject.set_stroke_opacity(0.3)

# Fade effect
mobject.fade(0.5)  # 0.5 = 50% faded (opposite of opacity)
```

## Background Rectangle

Add a background behind text or other mobjects:

```python
class BackgroundExample(Scene):
    def construct(self):
        text = Text("Important!")
        bg = BackgroundRectangle(text, fill_opacity=0.8, buff=0.1)
        group = VGroup(bg, text)
        self.add(group)
```

## Applying Style to Submobjects

```python
# Apply to all submobjects (family=True, default)
group.set_fill(RED, opacity=0.5, family=True)

# Apply only to parent, not submobjects
group.set_fill(RED, opacity=0.5, family=False)
```

## Style Based on Position

```python
class GradientFill(Scene):
    def construct(self):
        squares = VGroup(*[Square() for _ in range(5)]).arrange(RIGHT)

        for i, sq in enumerate(squares):
            opacity = (i + 1) / 5
            sq.set_fill(BLUE, opacity=opacity)

        self.add(squares)
```

## Copying Style

```python
# Copy style from another mobject
source = Circle().set_fill(RED, 0.5).set_stroke(WHITE, 4)
target = Square()
target.match_style(source)  # Now has same fill and stroke
```

## Best Practices

1. **Use fill_opacity for shapes** - Fully opaque fills can hide other elements
2. **Consistent stroke width** - Pick a width and stick with it
3. **Contrast fill and stroke** - Different colors help definition
4. **Use BackgroundRectangle for readability** - Behind text on busy backgrounds
5. **Chain methods for concise code** - But break lines if too long

### 3.6 2D Shapes & Geometry

*Source: `rules/shapes.md`*

# Geometric Shapes

Basic geometric primitives in Manim.

## Circle

```python
from manim import *

class CircleExample(Scene):
    def construct(self):
        # Default circle
        c1 = Circle()

        # With parameters
        c2 = Circle(
            radius=2,
            color=BLUE,
            fill_opacity=0.5,
            stroke_width=4
        )

        self.add(c1, c2)
```

### Circle Methods

```python
circle = Circle()

# Get properties
circle.get_radius()
circle.get_center()

# Create from points
Circle.from_three_points(p1, p2, p3)

# Surround another mobject
triangle = Triangle()
circle = Circle().surround(triangle)  # Circle wraps around triangle
circle = Circle().surround(triangle, buffer_factor=1.5)  # With padding
circle = Circle().surround(triangle, stretch=True)  # Stretch to fit
```

## Ellipse

```python
class EllipseExample(Scene):
    def construct(self):
        ellipse = Ellipse(
            width=4,
            height=2,
            color=GREEN
        )
        self.add(ellipse)
```

## Square

```python
class SquareExample(Scene):
    def construct(self):
        # Default square
        s1 = Square()

        # With parameters
        s2 = Square(
            side_length=2,
            color=RED,
            fill_opacity=0.8
        )

        self.add(s1, s2)
```

## Rectangle

```python
class RectangleExample(Scene):
    def construct(self):
        rect = Rectangle(
            width=4,
            height=2,
            color=YELLOW,
            fill_opacity=0.5
        )
        self.add(rect)
```

### RoundedRectangle

```python
class RoundedRectExample(Scene):
    def construct(self):
        rounded = RoundedRectangle(
            width=4,
            height=2,
            corner_radius=0.5,
            color=BLUE,
            fill_opacity=0.8
        )
        self.add(rounded)
```

## Triangle

```python
class TriangleExample(Scene):
    def construct(self):
        # Equilateral triangle
        tri = Triangle(color=PURPLE)

        # Custom triangle (using Polygon)
        custom_tri = Polygon(
            ORIGIN, RIGHT * 2, UP * 3,
            color=GREEN
        )

        self.add(tri, custom_tri.shift(RIGHT * 3))
```

## Polygon

Create any polygon from vertices.

```python
class PolygonExample(Scene):
    def construct(self):
        # Pentagon
        pentagon = RegularPolygon(n=5, color=ORANGE)

        # Hexagon
        hexagon = RegularPolygon(n=6, color=TEAL)

        # Custom polygon
        custom = Polygon(
            [-2, -1, 0],
            [2, -1, 0],
            [2, 1, 0],
            [0, 2, 0],
            [-2, 1, 0],
            color=PINK
        )

        VGroup(pentagon, hexagon, custom).arrange(RIGHT, buff=1)
        self.add(pentagon, hexagon, custom)
```

## RegularPolygon

```python
class RegularPolygonExamples(Scene):
    def construct(self):
        shapes = VGroup(
            RegularPolygon(n=3),   # Triangle
            RegularPolygon(n=4),   # Square
            RegularPolygon(n=5),   # Pentagon
            RegularPolygon(n=6),   # Hexagon
            RegularPolygon(n=8),   # Octagon
        ).arrange(RIGHT)
        self.add(shapes)
```

## Star

```python
class StarExample(Scene):
    def construct(self):
        star = Star(
            n=5,                    # Number of points
            outer_radius=2,
            inner_radius=1,         # Optional: auto-calculated if not specified
            density=2,              # How vertices connect (affects shape)
            color=YELLOW,
            fill_opacity=1
        )
        self.add(star)

        # Different densities create different star patterns
        star_d2 = Star(7, outer_radius=2, density=2, color=RED)
        star_d3 = Star(7, outer_radius=2, density=3, color=PURPLE)
```

## RegularPolygram

Star-like shapes with vertices connected by density.

```python
class PolygramExample(Scene):
    def construct(self):
        # Pentagram (5-pointed star pattern)
        pentagram = RegularPolygram(5, radius=2)
        self.add(pentagram)
```

## Annulus (Ring)

```python
class AnnulusExample(Scene):
    def construct(self):
        ring = Annulus(
            inner_radius=1,
            outer_radius=2,
            color=BLUE,
            fill_opacity=0.5
        )
        self.add(ring)
```

## Sector and Arc

```python
class SectorArcExample(Scene):
    def construct(self):
        # Sector (pie slice)
        sector = Sector(
            radius=2,
            angle=PI/2,
            start_angle=0,
            color=RED,
            fill_opacity=0.8
        ).shift(LEFT * 2)

        # Arc (just the curve)
        arc = Arc(
            radius=2,
            angle=PI/2,
            start_angle=PI,
            color=BLUE
        ).shift(RIGHT * 2)

        self.add(sector, arc)
```

## ArcBetweenPoints

```python
class ArcBetweenPointsExample(Scene):
    def construct(self):
        arc = ArcBetweenPoints(
            start=LEFT * 2,
            end=RIGHT * 2,
            angle=PI/2,  # Curvature
            color=GREEN
        )
        self.add(arc)
```

## Dot

```python
class DotExample(Scene):
    def construct(self):
        # Default dot
        d1 = Dot()

        # Customized
        d2 = Dot(
            point=RIGHT * 2,
            radius=0.2,
            color=YELLOW
        )

        self.add(d1, d2)
```

## Common Shape Operations

```python
shape = Square()

# Transform
shape.scale(2)
shape.rotate(PI/4)
shape.stretch(2, dim=0)  # Stretch horizontally

# Style
shape.set_fill(RED, opacity=0.5)
shape.set_stroke(WHITE, width=4)

# Position
shape.move_to(ORIGIN)
shape.shift(UP * 2)
shape.next_to(other, RIGHT)
```

## Best Practices

1. **Use RegularPolygon for regular shapes** - More precise than manual Polygon
2. **Set fill_opacity for visibility** - Default is often 0 (transparent)
3. **Use Dot for points** - Better than Circle with small radius
4. **Use RoundedRectangle for UI elements** - More polished look
5. **Combine shapes with VGroup** - For complex figures

### 3.7 Lines, Vectors & Arrows

*Source: `rules/lines.md`*

# Lines and Arrows

Connect points and show relationships with lines and arrows.

## Line

Basic line between two points.

```python
from manim import *

class LineExample(Scene):
    def construct(self):
        # Line from two points
        line = Line(LEFT * 2, RIGHT * 2)

        # With styling
        styled_line = Line(
            UP * 2, DOWN * 2,
            color=BLUE,
            stroke_width=4
        )

        self.add(line, styled_line)
```

### Line Properties

```python
line = Line(LEFT, RIGHT)

# Get points
line.get_start()
line.get_end()
line.get_center()
line.get_length()
line.get_angle()

# Modify
line.put_start_and_end_on(new_start, new_end)
line.set_length(3)  # Keep direction, change length
```

## Arrow

Line with an arrowhead.

```python
class ArrowExample(Scene):
    def construct(self):
        # Basic arrow
        arrow = Arrow(LEFT * 2, RIGHT * 2)

        # Styled arrow
        styled = Arrow(
            start=UP,
            end=DOWN,
            color=RED,
            stroke_width=6,
            tip_length=0.4,
            max_tip_length_to_length_ratio=0.5
        )

        self.add(arrow, styled)
```

### Arrow Variations

```python
# Double-headed arrow
double = DoubleArrow(LEFT * 2, RIGHT * 2)

# Arrow with custom tip
arrow = Arrow(LEFT, RIGHT)
arrow.tip  # Access the tip mobject
```

## Vector

Arrow starting from origin (useful for physics/math).

```python
class VectorExample(Scene):
    def construct(self):
        # Vector from origin
        v1 = Vector([2, 1, 0], color=YELLOW)
        v2 = Vector([-1, 2, 0], color=GREEN)

        self.add(v1, v2)
```

## DashedLine

```python
class DashedLineExample(Scene):
    def construct(self):
        dashed = DashedLine(
            LEFT * 2, RIGHT * 2,
            dash_length=0.2,
            dashed_ratio=0.5,  # Ratio of dash to gap
            color=WHITE
        )
        self.add(dashed)
```

## TangentLine

Line tangent to a curve at a point.

```python
class TangentLineExample(Scene):
    def construct(self):
        circle = Circle(radius=2)

        # Tangent at specific point (t parameter 0-1 along curve)
        tangent = TangentLine(circle, alpha=0.25, length=3, color=YELLOW)

        self.add(circle, tangent)
```

## Brace

Curly brace for highlighting.

```python
class BraceExample(Scene):
    def construct(self):
        rect = Rectangle(width=4, height=1)

        # Brace under the rectangle
        brace = Brace(rect, DOWN)

        # With label
        brace_text = brace.get_text("Width")

        # Alternative: BraceLabel
        brace_label = BraceLabel(rect, "Width", DOWN)

        self.add(rect, brace, brace_text)
```

### Brace Directions

```python
brace_down = Brace(mobject, DOWN)
brace_up = Brace(mobject, UP)
brace_left = Brace(mobject, LEFT)
brace_right = Brace(mobject, RIGHT)
```

## CurvedArrow

Curved arrow between points.

```python
class CurvedArrowExample(Scene):
    def construct(self):
        curved = CurvedArrow(
            start_point=LEFT * 2,
            end_point=RIGHT * 2,
            angle=PI/2  # Curvature
        )
        self.add(curved)
```

## Elbow

Right-angle connector.

```python
class ElbowExample(Scene):
    def construct(self):
        elbow = Elbow(width=2, angle=PI/2)
        self.add(elbow)
```

## NumberLine Ticks

```python
class TicksExample(Scene):
    def construct(self):
        line = NumberLine(x_range=[-3, 3, 1])
        self.add(line)
```

## Connecting Mobjects

### Line Between Mobjects

```python
class ConnectMobjects(Scene):
    def construct(self):
        c1 = Circle().shift(LEFT * 2)
        c2 = Circle().shift(RIGHT * 2)

        # Line connecting centers
        line = Line(c1.get_center(), c2.get_center())

        # Arrow between edges
        arrow = Arrow(
            c1.get_right(),  # Right edge of c1
            c2.get_left(),   # Left edge of c2
            buff=0.1         # Small gap from edges
        )

        self.add(c1, c2, line, arrow)
```

### Dynamic Connections with Updaters

```python
class DynamicLine(Scene):
    def construct(self):
        dot1 = Dot(LEFT * 2)
        dot2 = Dot(RIGHT * 2)

        # Line that follows dots
        line = always_redraw(lambda: Line(
            dot1.get_center(),
            dot2.get_center(),
            color=YELLOW
        ))

        self.add(dot1, dot2, line)
        self.play(dot1.animate.shift(UP * 2), run_time=2)
```

## Best Practices

1. **Use Arrow for direction** - Clearer than plain lines
2. **Use Vector for physics/math** - Semantically meaningful
3. **Use Brace for labeling dimensions** - Professional look
4. **Use DashedLine for auxiliary lines** - Distinguishes from main content
5. **Use always_redraw for dynamic lines** - Updates with moving endpoints

---

## 4. Typography & Mathematical Notation

### 4.1 Plain Text & Fonts

*Source: `rules/text.md`*

# Text in Manim

The `Text` class renders text using Pango/Cairo, supporting various fonts and styles.

## Basic Text

```python
from manim import *

class TextExample(Scene):
    def construct(self):
        text = Text("Hello World")
        self.play(Write(text))
```

## Text Parameters

```python
text = Text(
    "Hello World",
    font_size=48,           # Size (default: 48)
    color=BLUE,             # Text color
    font="Arial",           # Font family
    weight=BOLD,            # NORMAL, BOLD, etc.
    slant=ITALIC,           # NORMAL, ITALIC, OBLIQUE
    line_spacing=1.5,       # Space between lines
)
```

## Font Size

```python
# Using font_size parameter
small = Text("Small", font_size=24)
medium = Text("Medium", font_size=48)
large = Text("Large", font_size=72)

# Using scale after creation
text = Text("Hello").scale(2)
```

## Custom Fonts

```python
# Use any installed system font
text = Text("Custom Font", font="Comic Sans MS")
text = Text("Monospace", font="Courier New")
text = Text("Serif", font="Times New Roman")
```

## Text Styling with MarkupText

Use Pango markup for mixed styling within one Text object:

```python
class MarkupExample(Scene):
    def construct(self):
        text = MarkupText(
            f'all in red <span fgcolor="{YELLOW}">except this</span>',
            color=RED
        )
        self.play(Write(text))
```

### Available Markup Tags

```python
# Bold and italic
text = MarkupText('<b>Bold</b> and <i>Italic</i>')

# Colors using fgcolor
text = MarkupText('<span fgcolor="yellow">Yellow</span>')

# Subscripts and superscripts
text = MarkupText('H<sub>2</sub>O and x<sup>2</sup>')

# Font size
text = MarkupText('<big>Big</big> and <small>small</small>')

# Underline and strikethrough
text = MarkupText('<u>Underline</u> and <s>Strike</s>')

# Double underline with color
text = MarkupText('<span underline="double" underline_color="green">text</span>')

# Monospace
text = MarkupText('type <tt>help</tt> for help')
```

### Gradients in MarkupText

```python
# Global gradient
text = MarkupText("nice gradient", gradient=(BLUE, GREEN))

# Inline gradient
text = MarkupText(
    'nice <gradient from="RED" to="YELLOW">colored</gradient> text'
)
```

### Escaping Special Characters

```python
# Must escape these characters:
# > as &gt;
# < as &lt;
# & as &amp;
text = MarkupText("5 &gt; 3 and 2 &lt; 4")
```

## Multi-line Text

```python
# Using \n for line breaks
text = Text("Line 1\nLine 2\nLine 3")

# Using Paragraph for better control
from manim import Paragraph

para = Paragraph(
    "This is a longer text",
    "that spans multiple lines",
    "with automatic alignment",
    line_spacing=0.5
)
```

## Coloring Parts of Text

```python
class ColoredText(Scene):
    def construct(self):
        text = Text("Hello World")
        text[0:5].set_color(RED)    # "Hello" in red
        text[6:11].set_color(BLUE)  # "World" in blue
        self.play(Write(text))
```

## Text with Gradients

```python
text = Text("Gradient Text")
text.set_color_by_gradient(RED, YELLOW, GREEN)
```

## Accessing Characters

```python
text = Text("ABCDE")

# Individual characters
text[0]  # 'A'
text[1]  # 'B'

# Slices
text[0:3]  # 'ABC'
text[-1]   # 'E'

# Iterate
for char in text:
    char.set_color(random_color())
```

## Text Positioning

```python
# Standard positioning methods work
text = Text("Hello")
text.to_edge(UP)
text.to_corner(UL)
text.move_to(ORIGIN)
text.next_to(other_mobject, DOWN)
```

## Best Practices

1. **Use Text for regular text** - Simple and fast
2. **Use MarkupText for mixed styles** - When you need multiple colors/weights
3. **Use MathTex for math** - Text doesn't render LaTeX
4. **Install fonts system-wide** - Manim uses system fonts
5. **Keep font_size consistent** - Use the same size for related text

### 4.2 LaTeX & MathTex

*Source: `rules/latex.md`*

# LaTeX in Manim

Manim uses LaTeX to render mathematical expressions and formatted text.

## MathTex vs Tex

- **MathTex**: Automatically wraps content in math mode (`align*` environment)
- **Tex**: Raw LaTeX - you control the mode

```python
from manim import *

class LaTeXComparison(Scene):
    def construct(self):
        # MathTex - auto math mode
        math = MathTex(r"E = mc^2")

        # Tex - need explicit math delimiters
        tex = Tex(r"$E = mc^2$")

        # Both render the same
        VGroup(math, tex).arrange(DOWN)
        self.add(math, tex)
```

## Basic MathTex

```python
class MathTexExample(Scene):
    def construct(self):
        # Simple equation
        eq1 = MathTex(r"x^2 + y^2 = z^2")

        # Fractions
        eq2 = MathTex(r"\frac{a}{b}")

        # Square roots
        eq3 = MathTex(r"\sqrt{2}")

        # Greek letters
        eq4 = MathTex(r"\alpha + \beta = \gamma")

        # Integrals
        eq5 = MathTex(r"\int_0^\infty e^{-x} dx")

        # Summations
        eq6 = MathTex(r"\sum_{n=1}^{\infty} \frac{1}{n^2}")

        equations = VGroup(eq1, eq2, eq3, eq4, eq5, eq6).arrange_in_grid(2, 3)
        self.add(equations)
```

## Coloring Parts of Equations

### Using set_color_by_tex

```python
class ColoredEquation(Scene):
    def construct(self):
        eq = MathTex(r"e^{i\pi} + 1 = 0")
        eq.set_color_by_tex("e", RED)
        eq.set_color_by_tex(r"\pi", BLUE)
        eq.set_color_by_tex("i", GREEN)
        self.add(eq)
```

### Using substrings_to_isolate

For precise coloring, isolate substrings first:

```python
class IsolatedColoring(Scene):
    def construct(self):
        eq = MathTex(
            r"e^x = x^0 + x^1 + \frac{1}{2}x^2 + \cdots",
            substrings_to_isolate=["x"]
        )
        eq.set_color_by_tex("x", YELLOW)
        self.add(eq)
```

### Using index_labels for debugging

```python
class DebugLabels(Scene):
    def construct(self):
        eq = MathTex(r"\frac{a}{b}")
        # Add index labels to see which index is which part
        self.add(index_labels(eq[0]))
        self.add(eq)
```

### Direct indexing

```python
eq = MathTex(r"a + b = c")
eq[0][0].set_color(RED)   # 'a'
eq[0][2].set_color(BLUE)  # 'b'
eq[0][4].set_color(GREEN) # 'c'
```

## Multi-part Equations

Split equations into parts for individual control:

```python
class MultiPartEquation(Scene):
    def construct(self):
        eq = MathTex("a", "^2", "+", "b", "^2", "=", "c", "^2")

        eq[0].set_color(RED)    # a
        eq[3].set_color(BLUE)   # b
        eq[6].set_color(GREEN)  # c

        self.play(Write(eq))
```

## Text with Math (Tex)

```python
class MixedContent(Scene):
    def construct(self):
        # Mix text and math
        tex = Tex(r"The area is $A = \pi r^2$")
        self.play(Write(tex))
```

## Custom LaTeX Packages

```python
class CustomPackage(Scene):
    def construct(self):
        template = TexTemplate()
        template.add_to_preamble(r"\usepackage{mathrsfs}")

        eq = Tex(
            r"$\mathscr{L}$",
            tex_template=template
        )
        self.add(eq)
```

## Equation Alignment

```python
class AlignedEquations(Scene):
    def construct(self):
        eqs = MathTex(
            r"a &= b + c \\",
            r"d &= e + f + g \\",
            r"h &= i"
        )
        self.add(eqs)
```

## Common LaTeX Symbols

```python
# Greek letters
MathTex(r"\alpha \beta \gamma \delta \epsilon")
MathTex(r"\Gamma \Delta \Theta \Lambda \Pi")

# Operators
MathTex(r"\times \div \pm \mp \cdot")

# Relations
MathTex(r"\leq \geq \neq \approx \equiv")

# Arrows
MathTex(r"\rightarrow \leftarrow \Rightarrow \Leftrightarrow")

# Sets
MathTex(r"\in \notin \subset \supset \cup \cap")

# Calculus
MathTex(r"\int \iint \oint \partial \nabla")
```

## Font Size

```python
# Using font_size parameter
eq = MathTex(r"E = mc^2", font_size=72)

# Using scale
eq = MathTex(r"E = mc^2").scale(2)
```

## Best Practices

1. **Use raw strings** - Always use `r"..."` for LaTeX
2. **Use MathTex for pure math** - Simpler than adding `$...$`
3. **Use Tex for mixed content** - When combining text and math
4. **Split for animation control** - Separate parts you'll animate differently
5. **Use substrings_to_isolate** - For reliable coloring of repeated elements

### 4.3 Text Animations & Highlighting

*Source: `rules/text-animations.md`*

# Text Animations

Animations specifically designed for text and equations.

## Write

The most common text animation. Simulates handwriting.

```python
from manim import *

class WriteExample(Scene):
    def construct(self):
        text = Text("Hello World")
        equation = MathTex(r"E = mc^2")

        self.play(Write(text))
        self.wait()
        self.play(Write(equation))
```

### Write Parameters

```python
self.play(Write(
    text,
    run_time=2,           # Override auto-calculated time
    rate_func=linear,     # Timing curve
    reverse=False,        # Write backwards if True
))
```

Write automatically adjusts `run_time` based on text length.

## AddTextLetterByLetter

Types text one character at a time.

```python
class LetterByLetterExample(Scene):
    def construct(self):
        text = Text("Typing effect")

        self.play(AddTextLetterByLetter(
            text,
            time_per_char=0.1  # Speed of typing
        ))
```

**Note:** Only works with `Text`, not `MathTex`.

## RemoveTextLetterByLetter

Reverse of AddTextLetterByLetter - removes character by character.

```python
class RemoveLetterByLetter(Scene):
    def construct(self):
        text = Text("Disappearing text")
        self.add(text)

        self.play(RemoveTextLetterByLetter(
            text,
            time_per_char=0.05
        ))
```

## TypeWithCursor

Types text with a visible cursor.

```python
class TypeWithCursorExample(Scene):
    def construct(self):
        text = Text("Typing with cursor")

        # Create cursor
        cursor = Rectangle(
            color=GREY_A,
            fill_color=GREY_A,
            fill_opacity=1.0,
            height=1.1,
            width=0.1,
        )

        self.play(TypeWithCursor(text, cursor))

        # Optional: blink cursor after typing
        self.play(Blink(cursor, blinks=3))
```

### Cursor Customization

```python
# Line cursor
cursor = Line(UP * 0.5, DOWN * 0.5, color=WHITE, stroke_width=2)

# Block cursor
cursor = Rectangle(width=0.5, height=1, fill_opacity=0.8, color=WHITE)

# Custom cursor position
self.play(TypeWithCursor(
    text,
    cursor,
    buff=0.05,           # Space between text and cursor
    keep_cursor_y=True,  # Keep cursor at consistent height
    leave_cursor_on=True # Show cursor after animation
))
```

## Blink (for cursors)

```python
class BlinkExample(Scene):
    def construct(self):
        cursor = Rectangle(height=1, width=0.1, fill_opacity=1)
        self.add(cursor)

        self.play(Blink(cursor, blinks=5, time_on=0.3, time_off=0.3))
```

## Word by Word Animation

Using LaggedStart for word-by-word appearance:

```python
class WordByWord(Scene):
    def construct(self):
        # Split into individual Text objects
        words = VGroup(
            Text("Hello"),
            Text("World"),
            Text("!")
        ).arrange(RIGHT, buff=0.3)

        self.play(LaggedStart(
            *[Write(word) for word in words],
            lag_ratio=0.5
        ))
```

## Equation Transformations

Animate between equations:

```python
class EquationTransform(Scene):
    def construct(self):
        eq1 = MathTex(r"a^2 + b^2 = c^2")
        eq2 = MathTex(r"c = \sqrt{a^2 + b^2}")

        self.play(Write(eq1))
        self.wait()
        self.play(TransformMatchingTex(eq1, eq2))
```

## Highlighting Text

```python
class HighlightText(Scene):
    def construct(self):
        text = Text("Important message")
        self.add(text)

        # Circumscribe (draw around)
        self.play(Circumscribe(text, color=YELLOW))

        # Indicate (pulse)
        self.play(Indicate(text, color=RED))

        # Flash
        self.play(Flash(text.get_center(), color=WHITE))
```

## Replacing Text

```python
class ReplaceText(Scene):
    def construct(self):
        text1 = Text("Before")
        text2 = Text("After")

        self.play(Write(text1))
        self.wait()

        # Transform text
        self.play(Transform(text1, text2))

        # Or replacement transform
        self.play(ReplacementTransform(text1, text2))
```

## Colored Text Animation

```python
class ColoredTextAnimation(Scene):
    def construct(self):
        text = Text("Colorful")
        self.play(Write(text))

        # Animate color change per letter
        self.play(LaggedStart(
            *[char.animate.set_color(random_bright_color()) for char in text],
            lag_ratio=0.1
        ))
```

## Best Practices

1. **Use Write for most text** - Natural and smooth
2. **Use AddTextLetterByLetter for "typing" effect** - Terminal/code aesthetics
3. **Use TypeWithCursor for interactive feel** - Good for tutorials
4. **Use TransformMatchingTex for equations** - Smooth mathematical transitions
5. **Adjust time_per_char for pacing** - 0.05-0.1 is usually good
6. **Only use Text (not MathTex) for letter-by-letter** - API limitation

---

## 5. Coordinate Systems & Data Visualization

### 5.1 Axes, NumberPlanes & Coordinate Conversion

*Source: `rules/axes.md`*

# Coordinate Systems

Create axes, grids, and number lines for mathematical visualizations.

## Axes

Basic 2D coordinate axes.

```python
from manim import *

class AxesExample(Scene):
    def construct(self):
        # Default axes
        axes = Axes()
        self.add(axes)
```

### Customizing Axes

```python
class CustomAxes(Scene):
    def construct(self):
        axes = Axes(
            x_range=[-5, 5, 1],      # [min, max, step]
            y_range=[-3, 3, 1],
            x_length=10,              # Physical length on screen
            y_length=6,
            axis_config={
                "color": BLUE,
                "include_tip": True,
                "include_numbers": True,
            },
            x_axis_config={
                "numbers_to_include": [-4, -2, 0, 2, 4],
            },
            y_axis_config={
                "numbers_to_include": [-2, 0, 2],
            },
        )
        self.add(axes)
```

### Adding Labels

```python
class AxesLabels(Scene):
    def construct(self):
        axes = Axes(x_range=[-5, 5], y_range=[-3, 3])

        # Add axis labels
        x_label = axes.get_x_axis_label("x")
        y_label = axes.get_y_axis_label("y")

        # Custom labels
        x_label = axes.get_x_axis_label(MathTex(r"\theta"))
        y_label = axes.get_y_axis_label(MathTex(r"f(\theta)"))

        self.add(axes, x_label, y_label)
```

## NumberPlane

Grid with axes - shows coordinate lines.

```python
class NumberPlaneExample(Scene):
    def construct(self):
        # Default plane
        plane = NumberPlane()
        self.add(plane)
```

### Customizing NumberPlane

```python
class CustomPlane(Scene):
    def construct(self):
        plane = NumberPlane(
            x_range=[-4, 4, 1],
            y_range=[-3, 3, 1],
            x_length=8,
            y_length=6,
            background_line_style={
                "stroke_color": BLUE_D,
                "stroke_width": 1,
                "stroke_opacity": 0.5,
            },
            axis_config={
                "color": WHITE,
            },
        )
        self.add(plane)
```

## ComplexPlane

For visualizing complex numbers.

```python
class ComplexPlaneExample(Scene):
    def construct(self):
        plane = ComplexPlane()

        # Plot complex number
        z = complex(2, 1)  # 2 + i
        dot = Dot(plane.n2p(z), color=YELLOW)
        label = MathTex("2+i").next_to(dot, UR)

        self.add(plane, dot, label)
```

## NumberLine

Single axis line.

```python
class NumberLineExample(Scene):
    def construct(self):
        line = NumberLine(
            x_range=[-5, 5, 1],
            length=10,
            include_numbers=True,
            include_tip=True,
        )
        self.add(line)
```

## Coordinate Conversions

```python
class CoordinateConversion(Scene):
    def construct(self):
        axes = Axes(x_range=[-5, 5], y_range=[-3, 3])

        # Convert coordinates to screen position
        point = axes.c2p(2, 1)  # coords_to_point: (2, 1) -> screen position

        # Convert screen position to coordinates
        coords = axes.p2c(point)  # point_to_coords: screen -> (x, y)

        dot = Dot(point, color=RED)
        self.add(axes, dot)
```

### Shorthand Methods

```python
axes = Axes()

# c2p = coords_to_point
axes.c2p(x, y)

# p2c = point_to_coords
axes.p2c(point)

# i2gp = input_to_graph_point (for graphs)
axes.i2gp(x, graph)

# For NumberPlane/ComplexPlane
plane.n2p(complex_number)  # number_to_point
plane.p2n(point)           # point_to_number
```

## ThreeDAxes

For 3D visualizations.

```python
class ThreeDAxesExample(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes(
            x_range=[-4, 4, 1],
            y_range=[-4, 4, 1],
            z_range=[-4, 4, 1],
            x_length=8,
            y_length=8,
            z_length=6,
        )

        self.set_camera_orientation(phi=75 * DEGREES, theta=-45 * DEGREES)
        self.add(axes)
```

## Plotting Points

```python
class PlotPoints(Scene):
    def construct(self):
        axes = Axes(x_range=[-5, 5], y_range=[-3, 3])

        points = [(1, 2), (-2, 1), (3, -1), (0, 2)]
        dots = VGroup(*[
            Dot(axes.c2p(x, y), color=YELLOW)
            for x, y in points
        ])

        self.add(axes, dots)
```

## Best Practices

1. **Set appropriate ranges** - Don't include unnecessary empty space
2. **Match x_length/y_length to range ratio** - Prevents distortion
3. **Use NumberPlane for transformations** - Grid shows distortion clearly
4. **Use c2p for all coordinate work** - Don't manually convert
5. **Include numbers sparingly** - Too many numbers clutter the display

### 5.2 Function Graphing, Plotting & Shading

*Source: `rules/graphing.md`*

# Graphing Functions

Plot mathematical functions and curves.

## Plotting Functions on Axes

```python
from manim import *

class BasicPlot(Scene):
    def construct(self):
        axes = Axes(x_range=[-3, 3], y_range=[-2, 8])

        # Plot a function
        graph = axes.plot(lambda x: x**2, color=BLUE)

        self.add(axes, graph)
```

## plot() Parameters

```python
class PlotParameters(Scene):
    def construct(self):
        axes = Axes(x_range=[-5, 5], y_range=[-2, 2])

        graph = axes.plot(
            lambda x: np.sin(x),
            x_range=[-PI, PI],    # Limit domain
            color=YELLOW,
            stroke_width=4,
        )

        self.add(axes, graph)
```

## Multiple Functions

```python
class MultiplePlots(Scene):
    def construct(self):
        axes = Axes(x_range=[-3, 3], y_range=[-2, 10])

        sin_graph = axes.plot(lambda x: np.sin(x), color=BLUE)
        cos_graph = axes.plot(lambda x: np.cos(x), color=RED)
        quad_graph = axes.plot(lambda x: x**2, color=GREEN)

        self.add(axes, sin_graph, cos_graph, quad_graph)
```

## Adding Labels to Graphs

```python
class GraphLabels(Scene):
    def construct(self):
        axes = Axes(x_range=[-3, 3], y_range=[-2, 10])
        graph = axes.plot(lambda x: x**2, color=BLUE)

        # Add label to graph
        label = axes.get_graph_label(
            graph,
            label=MathTex("y = x^2"),
            x_val=2,
            direction=UR
        )

        self.add(axes, graph, label)
```

## Parametric Curves

Plot curves defined by parametric equations.

```python
class ParametricExample(Scene):
    def construct(self):
        axes = Axes(x_range=[-3, 3], y_range=[-3, 3])

        # Circle: x = cos(t), y = sin(t)
        curve = axes.plot_parametric_curve(
            lambda t: np.array([np.cos(t), np.sin(t), 0]),
            t_range=[0, 2 * PI],
            color=YELLOW
        )

        self.add(axes, curve)
```

### Parametric Curve Examples

```python
# Lissajous curve
curve = axes.plot_parametric_curve(
    lambda t: np.array([np.sin(3*t), np.sin(2*t), 0]),
    t_range=[0, 2*PI],
)

# Spiral
curve = axes.plot_parametric_curve(
    lambda t: np.array([t*np.cos(t), t*np.sin(t), 0]),
    t_range=[0, 4*PI],
)

# Heart curve
curve = axes.plot_parametric_curve(
    lambda t: np.array([
        16 * np.sin(t)**3,
        13*np.cos(t) - 5*np.cos(2*t) - 2*np.cos(3*t) - np.cos(4*t),
        0
    ]) / 10,
    t_range=[0, 2*PI],
)
```

## ParametricFunction (standalone)

Create parametric curves without axes:

```python
class StandaloneParametric(Scene):
    def construct(self):
        curve = ParametricFunction(
            lambda t: np.array([np.cos(t), np.sin(t), 0]),
            t_range=[0, 2*PI],
            color=BLUE
        )
        self.add(curve)
```

## Area Under Curve

```python
class AreaUnderCurve(Scene):
    def construct(self):
        axes = Axes(x_range=[-1, 5], y_range=[-1, 10])
        graph = axes.plot(lambda x: x**2, x_range=[0, 3], color=BLUE)

        # Shade area under curve
        area = axes.get_area(
            graph,
            x_range=[0, 2],
            color=BLUE,
            opacity=0.5
        )

        self.add(axes, graph, area)
```

## Riemann Rectangles

```python
class RiemannRectangles(Scene):
    def construct(self):
        axes = Axes(x_range=[-1, 5], y_range=[-1, 10])
        graph = axes.plot(lambda x: x**2, color=BLUE)

        rects = axes.get_riemann_rectangles(
            graph,
            x_range=[0, 3],
            dx=0.5,
            color=YELLOW,
            stroke_width=1
        )

        self.add(axes, graph, rects)
```

## Animated Graphing

```python
class AnimatedGraph(Scene):
    def construct(self):
        axes = Axes(x_range=[-3, 3], y_range=[-2, 2])
        self.add(axes)

        graph = axes.plot(lambda x: np.sin(x), color=BLUE)

        # Animate the graph being drawn
        self.play(Create(graph), run_time=3)
```

## Moving Point on Graph

```python
class MovingPointOnGraph(Scene):
    def construct(self):
        axes = Axes(x_range=[-3, 3], y_range=[-2, 2])
        graph = axes.plot(lambda x: np.sin(x), color=BLUE)

        # Point that follows graph
        x_tracker = ValueTracker(-3)

        dot = always_redraw(lambda: Dot(
            axes.i2gp(x_tracker.get_value(), graph),
            color=YELLOW
        ))

        self.add(axes, graph, dot)
        self.play(x_tracker.animate.set_value(3), run_time=4)
```

## 3D Surface Plots

```python
class SurfacePlot(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes()

        surface = axes.plot_surface(
            lambda u, v: np.sin(u) * np.cos(v),
            u_range=[-PI, PI],
            v_range=[-PI, PI],
            colorscale=[BLUE, GREEN, YELLOW],
        )

        self.set_camera_orientation(phi=75*DEGREES, theta=-45*DEGREES)
        self.add(axes, surface)
```

## Best Practices

1. **Set x_range on plot for discontinuities** - Avoid graphing undefined regions
2. **Use get_graph_label for clarity** - Label functions on the graph
3. **Match graph color to concept** - Consistent color coding
4. **Use i2gp for points on graphs** - Automatically handles conversion
5. **Animate graph creation** - More engaging than static display

---

## 6. 3D Visualizations & Dynamic Camera

### 6.1 ThreeDScene & 3D Objects

*Source: `rules/3d.md`*

# 3D Graphics in Manim

Create 3D visualizations with ThreeDScene.

## ThreeDScene Basics

```python
from manim import *

class Basic3D(ThreeDScene):
    def construct(self):
        # Set camera angle
        self.set_camera_orientation(phi=75 * DEGREES, theta=-45 * DEGREES)

        # Add 3D axes
        axes = ThreeDAxes()
        self.add(axes)
```

## Camera Orientation

```python
class CameraOrientation(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes()

        # phi: angle from z-axis (0 = top view, 90 = side view)
        # theta: rotation around z-axis
        # gamma: roll angle

        self.set_camera_orientation(
            phi=75 * DEGREES,
            theta=-45 * DEGREES,
            gamma=0
        )

        self.add(axes)
```

### Animated Camera Movement

```python
class AnimatedCamera(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes()
        self.add(axes)

        self.set_camera_orientation(phi=75*DEGREES, theta=0)

        # Animate camera movement
        self.move_camera(phi=45*DEGREES, theta=90*DEGREES, run_time=3)
```

### Continuous Camera Rotation

```python
class RotatingCamera(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes()
        self.add(axes)

        self.set_camera_orientation(phi=75*DEGREES, theta=0)

        # Start ambient rotation
        self.begin_ambient_camera_rotation(rate=0.2)
        self.wait(5)
        self.stop_ambient_camera_rotation()
```

## 3D Primitives

### Sphere

```python
class SphereExample(ThreeDScene):
    def construct(self):
        sphere = Sphere(radius=1, resolution=(20, 20))
        sphere.set_color(BLUE)

        self.set_camera_orientation(phi=75*DEGREES, theta=-45*DEGREES)
        self.add(sphere)
```

### Cube / Prism

```python
class CubeExample(ThreeDScene):
    def construct(self):
        cube = Cube(side_length=2, fill_opacity=0.8)
        cube.set_color(RED)

        # Rectangular prism
        prism = Prism(dimensions=[3, 1, 2])

        self.set_camera_orientation(phi=75*DEGREES, theta=-45*DEGREES)
        self.add(cube)
```

### Cylinder / Cone

```python
class CylinderCone(ThreeDScene):
    def construct(self):
        cylinder = Cylinder(radius=1, height=2, fill_opacity=0.8)
        cone = Cone(base_radius=1, height=2, fill_opacity=0.8)

        cylinder.shift(LEFT * 2)
        cone.shift(RIGHT * 2)

        self.set_camera_orientation(phi=75*DEGREES, theta=-45*DEGREES)
        self.add(cylinder, cone)
```

### Torus

```python
class TorusExample(ThreeDScene):
    def construct(self):
        torus = Torus(major_radius=2, minor_radius=0.5)

        self.set_camera_orientation(phi=75*DEGREES, theta=-45*DEGREES)
        self.add(torus)
```

## 3D Axes

```python
class ThreeDAxesExample(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes(
            x_range=[-4, 4, 1],
            y_range=[-4, 4, 1],
            z_range=[-4, 4, 1],
            x_length=8,
            y_length=8,
            z_length=6,
        )

        # Add axis labels
        x_label = axes.get_x_axis_label("x")
        y_label = axes.get_y_axis_label("y")
        z_label = axes.get_z_axis_label("z")

        self.set_camera_orientation(phi=75*DEGREES, theta=-45*DEGREES)
        self.add(axes, x_label, y_label, z_label)
```

## Surface Plots

```python
class SurfacePlot(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes(x_range=[-3, 3], y_range=[-3, 3], z_range=[-2, 2])

        # Function z = f(x, y)
        surface = axes.plot_surface(
            lambda u, v: np.sin(u) * np.cos(v),
            u_range=[-3, 3],
            v_range=[-3, 3],
            resolution=(30, 30),
            colorscale=[BLUE, GREEN, YELLOW, RED],
        )

        self.set_camera_orientation(phi=75*DEGREES, theta=-45*DEGREES)
        self.add(axes, surface)
```

### Surface Class (standalone)

```python
class SurfaceExample(ThreeDScene):
    def construct(self):
        def param_func(u, v):
            x = u
            y = v
            z = np.sin(np.sqrt(u**2 + v**2))
            return np.array([x, y, z])

        surface = Surface(
            param_func,
            u_range=[-3, 3],
            v_range=[-3, 3],
            resolution=(30, 30),
            fill_opacity=0.8,
        )
        surface.set_color_by_gradient(BLUE, GREEN)

        self.set_camera_orientation(phi=75*DEGREES, theta=-45*DEGREES)
        self.add(surface)
```

## 3D Parametric Curves

```python
class ParametricCurve3D(ThreeDScene):
    def construct(self):
        # Helix
        curve = ParametricFunction(
            lambda t: np.array([
                np.cos(t),
                np.sin(t),
                t * 0.2
            ]),
            t_range=[-4*PI, 4*PI],
            color=YELLOW
        )
        curve.set_shade_in_3d(True)

        self.set_camera_orientation(phi=75*DEGREES, theta=-45*DEGREES)
        self.add(ThreeDAxes(), curve)
```

## Shading in 3D

```python
class Shading3D(ThreeDScene):
    def construct(self):
        sphere = Sphere()

        # Enable shading for realistic lighting
        sphere.set_shade_in_3d(True)

        self.set_camera_orientation(phi=75*DEGREES, theta=-45*DEGREES)
        self.add(sphere)
```

## Arrow3D and Line3D

```python
class Vectors3D(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes()

        arrow = Arrow3D(ORIGIN, [2, 1, 2], color=RED)
        line = Line3D(ORIGIN, [-2, 1, 1], color=BLUE)

        self.set_camera_orientation(phi=75*DEGREES, theta=-45*DEGREES)
        self.add(axes, arrow, line)
```

## Best Practices

1. **Always set camera orientation** - Default view may not show 3D well
2. **Use set_shade_in_3d for realism** - Adds depth perception
3. **Use ambient camera rotation sparingly** - Can be disorienting
4. **Match resolution to detail needed** - Higher res = slower render
5. **Use colorscale for surfaces** - Shows elevation/value changes

### 6.2 MovingCameraScene & Viewport Control

*Source: `rules/camera.md`*

# Camera Control

Control what the viewer sees with camera manipulation.

## MovingCameraScene

For 2D scenes with camera movement (zoom, pan).

```python
from manim import *

class CameraExample(MovingCameraScene):
    def construct(self):
        circle = Circle()
        square = Square().shift(RIGHT * 3)
        self.add(circle, square)

        # Access camera frame
        # self.camera.frame is the viewable area
```

## Zooming

### Zoom In/Out by Scaling Frame

```python
class ZoomExample(MovingCameraScene):
    def construct(self):
        dots = VGroup(*[Dot() for _ in range(100)])
        dots.arrange_in_grid(10, 10, buff=0.3)
        self.add(dots)

        # Zoom in (make frame smaller)
        self.play(self.camera.frame.animate.scale(0.5))
        self.wait()

        # Zoom out (make frame larger)
        self.play(self.camera.frame.animate.scale(4))
```

### Zoom to Specific Width

```python
class ZoomToWidth(MovingCameraScene):
    def construct(self):
        text = Text("Focus on me!")
        self.add(text)

        # Zoom to fit text with padding
        self.play(
            self.camera.frame.animate.set(width=text.width * 1.5)
        )
```

## Panning

### Move Camera to Location

```python
class PanExample(MovingCameraScene):
    def construct(self):
        c1 = Circle().shift(LEFT * 3)
        c2 = Circle().shift(RIGHT * 3)
        self.add(c1, c2)

        # Pan to first circle
        self.play(self.camera.frame.animate.move_to(c1))
        self.wait()

        # Pan to second circle
        self.play(self.camera.frame.animate.move_to(c2))
```

### Combined Zoom and Pan

```python
class ZoomAndPan(MovingCameraScene):
    def construct(self):
        square = Square().shift(LEFT * 2)
        triangle = Triangle().shift(RIGHT * 2)
        self.add(square, triangle)

        # Zoom in and pan simultaneously
        self.play(
            self.camera.frame.animate.scale(0.5).move_to(square)
        )
        self.wait()

        # Move to triangle (still zoomed)
        self.play(self.camera.frame.animate.move_to(triangle))
```

## Save and Restore Camera State

```python
class SaveRestoreCamera(MovingCameraScene):
    def construct(self):
        circle = Circle()
        self.add(circle)

        # Save current state
        self.camera.frame.save_state()

        # Make changes
        self.play(self.camera.frame.animate.scale(0.3).move_to(circle))
        self.wait()

        # Restore to saved state
        self.play(Restore(self.camera.frame))
```

## auto_zoom

Automatically zoom to fit mobjects.

```python
class AutoZoomExample(MovingCameraScene):
    def construct(self):
        squares = VGroup(*[
            Square().shift(RIGHT * i + UP * j)
            for i in range(-2, 3) for j in range(-2, 3)
        ])
        self.add(squares)

        # Zoom to fit specific mobject
        self.play(self.camera.auto_zoom(squares[0]))
        self.wait()

        # Zoom to fit all with margin
        self.play(self.camera.auto_zoom(squares, margin=1))
```

## 3D Camera (ThreeDScene)

```python
class ThreeDCameraExample(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes()
        sphere = Sphere()
        self.add(axes, sphere)

        # Set initial camera orientation
        self.set_camera_orientation(
            phi=75 * DEGREES,    # Angle from z-axis
            theta=-45 * DEGREES  # Angle around z-axis
        )
```

### Animated Camera Rotation

```python
class RotatingCamera(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes()
        self.add(axes)

        self.set_camera_orientation(phi=75 * DEGREES, theta=0)

        # Continuous rotation
        self.begin_ambient_camera_rotation(rate=0.2)
        self.wait(5)
        self.stop_ambient_camera_rotation()
```

### Move 3D Camera

```python
class Move3DCamera(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes()
        self.add(axes)

        self.set_camera_orientation(phi=75 * DEGREES, theta=-45 * DEGREES)

        # Animate camera movement
        self.move_camera(
            phi=45 * DEGREES,
            theta=45 * DEGREES,
            run_time=3
        )
```

## Camera Background

```python
class CameraBackground(Scene):
    def construct(self):
        # Set background color
        self.camera.background_color = BLUE_E

        circle = Circle()
        self.add(circle)
```

## Best Practices

1. **Use MovingCameraScene for zoom/pan** - Regular Scene camera is static
2. **Save state before complex movements** - Easy to restore
3. **Use auto_zoom for dynamic content** - Automatically fits content
4. **Keep camera movements smooth** - Don't make viewers dizzy
5. **Use 3D camera rotation sparingly** - Can be disorienting

---

## 7. Animation Engine & Dynamic Behaviors

### 7.1 Core Animation Patterns

*Source: `rules/animations.md`*

# Animations in Manim

Animations interpolate mobjects between states over time. They are played using `self.play()`.

## The .animate Syntax

The most common way to animate is using the `.animate` property:

```python
# Move a square to the right
self.play(square.animate.shift(RIGHT))

# Scale up
self.play(circle.animate.scale(2))

# Change color
self.play(text.animate.set_color(RED))

# Chain multiple changes
self.play(square.animate.shift(RIGHT).rotate(PI/4).set_color(BLUE))
```

## Animation Parameters

### run_time
Controls animation duration in seconds (default: 1).

```python
self.play(Create(circle), run_time=2)  # 2 second animation
self.play(Create(circle), run_time=0.5)  # Half second
```

### rate_func
Controls the animation's timing curve (easing).

```python
from manim import smooth, linear, there_and_back

self.play(square.animate.shift(RIGHT), rate_func=smooth)
self.play(square.animate.shift(RIGHT), rate_func=linear)
self.play(square.animate.shift(RIGHT), rate_func=there_and_back)
```

## Playing Multiple Animations

### Simultaneously

```python
# All play at the same time
self.play(
    Create(circle),
    FadeIn(square),
    Write(text)
)
```

### Sequentially

```python
# One after another
self.play(Create(circle))
self.play(FadeIn(square))
self.play(Write(text))

# Or use Succession
self.play(Succession(
    Create(circle),
    FadeIn(square),
    Write(text)
))
```

## Common Animation Classes

### Creation Animations
```python
Create(mobject)           # Draw the mobject progressively
Write(text)               # Write text/equations
FadeIn(mobject)           # Fade in from transparent
DrawBorderThenFill(mob)   # Draw outline, then fill
GrowFromCenter(mobject)   # Grow from center point
```

### Removal Animations
```python
FadeOut(mobject)          # Fade to transparent
Uncreate(mobject)         # Reverse of Create
ShrinkToCenter(mobject)   # Shrink to center and disappear
```

### Transform Animations
```python
Transform(mob1, mob2)              # Morph mob1 into mob2
ReplacementTransform(mob1, mob2)   # Replace mob1 with mob2
TransformFromCopy(mob1, mob2)      # Keep mob1, create mob2
```

### Movement Animations
```python
MoveToTarget(mobject)     # Move to preset target
Rotate(mobject, angle)    # Rotate by angle
Circumscribe(mobject)     # Draw attention with circle
```

## Animation vs Instant Changes

```python
# Animated change (visible transition)
self.play(circle.animate.set_color(RED))

# Instant change (no animation)
circle.set_color(RED)
self.add(circle)
```

## Best Practices

1. **Use .animate for simple transformations** - Cleaner than explicit Animation classes
2. **Keep run_time reasonable** - 0.5-2 seconds for most animations
3. **Use rate_func for polish** - `smooth` is usually better than `linear`
4. **Group related animations** - Play simultaneously when conceptually related

### 7.2 Creation & Revealing Animations

*Source: `rules/creation-animations.md`*

# Creation Animations

Animations that introduce mobjects to the scene.

## Create

Draws a VMobject progressively along its path.

```python
from manim import *

class CreateExample(Scene):
    def construct(self):
        circle = Circle()
        self.play(Create(circle))
```

Best for: Geometric shapes, lines, arrows.

## Write

Simulates handwriting. Best for text and equations.

```python
class WriteExample(Scene):
    def construct(self):
        text = Text("Hello World")
        equation = MathTex(r"E = mc^2")

        self.play(Write(text))
        self.wait()
        self.play(Write(equation))
```

Write automatically sets appropriate timing based on text length.

## DrawBorderThenFill

Draws the outline first, then fills in the shape.

```python
class DrawBorderExample(Scene):
    def construct(self):
        square = Square(fill_opacity=0.8, color=BLUE)
        self.play(DrawBorderThenFill(square))
```

Best for: Shapes with fills where you want to emphasize the outline first.

## FadeIn / FadeOut

Simple opacity transitions.

```python
class FadeExample(Scene):
    def construct(self):
        circle = Circle()

        # Fade in
        self.play(FadeIn(circle))
        self.wait()

        # Fade out
        self.play(FadeOut(circle))
```

### Directional Fades

```python
# Fade in from a direction
self.play(FadeIn(square, shift=UP))      # Fade in while moving up
self.play(FadeIn(square, shift=LEFT))    # Fade in from right

# Fade out to a direction
self.play(FadeOut(square, shift=DOWN))   # Fade out while moving down
```

### Scale Fades

```python
self.play(FadeIn(circle, scale=0.5))   # Fade in while growing
self.play(FadeOut(circle, scale=2))    # Fade out while shrinking
```

## GrowFromCenter / ShrinkToCenter

```python
class GrowExample(Scene):
    def construct(self):
        circle = Circle()

        self.play(GrowFromCenter(circle))
        self.wait()
        self.play(ShrinkToCenter(circle))
```

## GrowFromPoint

Grow from a specific point.

```python
self.play(GrowFromPoint(circle, ORIGIN))
self.play(GrowFromPoint(circle, LEFT * 3))
```

## GrowFromEdge

Grow from a specific edge.

```python
self.play(GrowFromEdge(square, LEFT))   # Grow from left edge
self.play(GrowFromEdge(square, DOWN))   # Grow from bottom edge
```

## SpinInFromNothing

Object spins in while growing.

```python
self.play(SpinInFromNothing(circle))
```

## Uncreate

Reverse of Create - erases the mobject.

```python
self.play(Create(circle))
self.wait()
self.play(Uncreate(circle))  # Erases in reverse
```

## AddTextLetterByLetter

Types text one character at a time.

```python
class TypingExample(Scene):
    def construct(self):
        text = Text("Hello World")
        self.play(AddTextLetterByLetter(text, time_per_char=0.1))
```

Note: Only works with `Text`, not `MathTex`.

## Best Practices

1. **Use Write for text** - Looks more natural than Create
2. **Use Create for shapes** - Clean progressive drawing
3. **Use FadeIn for quick introductions** - When drawing isn't important
4. **Match removal to creation** - If you Create, use Uncreate; if FadeIn, use FadeOut

### 7.3 Transformations & Interpolations

*Source: `rules/transform-animations.md`*

# Transform Animations

Animations that morph one mobject into another.

## Transform

Morphs the source mobject into the shape of the target. The source mobject is modified.

```python
class TransformExample(Scene):
    def construct(self):
        square = Square()
        circle = Circle()

        self.play(Create(square))
        self.play(Transform(square, circle))
        # Note: 'square' now looks like 'circle' but is still 'square'
```

**Important:** After Transform, the original variable still references the mobject, even though it looks like the target.

## ReplacementTransform

Morphs source into target and replaces the reference. More intuitive for most uses.

```python
class ReplacementTransformExample(Scene):
    def construct(self):
        square = Square()
        circle = Circle()
        triangle = Triangle()

        self.play(Create(square))
        self.play(ReplacementTransform(square, circle))
        # 'square' is removed, 'circle' is now in the scene
        self.play(ReplacementTransform(circle, triangle))
        # 'circle' is removed, 'triangle' is now in the scene
```

## Transform vs ReplacementTransform

```python
# Transform - source variable changes appearance
self.play(Transform(A, B))
# A is still in scene (but looks like B)
# B is NOT in scene

# ReplacementTransform - source is replaced by target
self.play(ReplacementTransform(A, B))
# A is removed from scene
# B is now in scene
```

## TransformFromCopy

Creates a copy of source and morphs it to target. Original remains unchanged.

```python
class TransformFromCopyExample(Scene):
    def construct(self):
        square = Square().shift(LEFT * 2)
        circle = Circle().shift(RIGHT * 2)

        self.add(square)
        self.play(TransformFromCopy(square, circle))
        # Both square and circle are now visible
```

## TransformMatchingShapes

Intelligently matches and transforms corresponding parts.

```python
class MatchingShapesExample(Scene):
    def construct(self):
        source = Text("ABC")
        target = Text("ABCD")

        self.play(Write(source))
        self.play(TransformMatchingShapes(source, target))
```

## TransformMatchingTex

Matches LaTeX parts by their TeX strings.

```python
class MatchingTexExample(Scene):
    def construct(self):
        eq1 = MathTex("a", "^2", "+", "b", "^2")
        eq2 = MathTex("a", "^2", "+", "2ab", "+", "b", "^2")

        self.play(Write(eq1))
        self.play(TransformMatchingTex(eq1, eq2))
```

## MoveToTarget

Pre-set a target state and animate to it.

```python
class MoveToTargetExample(Scene):
    def construct(self):
        square = Square()
        self.add(square)

        # Generate and modify target
        square.generate_target()
        square.target.shift(RIGHT * 2)
        square.target.set_color(RED)
        square.target.scale(2)

        self.play(MoveToTarget(square))
```

## Path Arc Transforms

Control the path of transformation with `path_arc`.

```python
class PathArcExample(Scene):
    def construct(self):
        dot1 = Dot(LEFT * 2)
        dot2 = Dot(RIGHT * 2)

        self.add(dot1)
        # Transform along an arc
        self.play(Transform(dot1, dot2, path_arc=PI/2))
```

## Chained Transformations

```python
class ChainedExample(Scene):
    def construct(self):
        shape = Square()
        self.play(Create(shape))

        # Chain of transformations
        for target in [Circle(), Triangle(), Star()]:
            self.play(Transform(shape, target))
            self.wait(0.5)
```

## Best Practices

1. **Use ReplacementTransform for clarity** - More intuitive variable behavior
2. **Use TransformFromCopy to preserve original** - When you need both visible
3. **Use TransformMatchingTex for equations** - Better alignment of matching parts
4. **Set path_arc for visual interest** - Curved paths look more dynamic

### 7.4 Animation Groups, Successions & Staggering

*Source: `rules/animation-groups.md`*

# Animation Groups

Control how multiple animations play together.

## AnimationGroup

Play multiple animations with controlled timing.

```python
from manim import *

class AnimationGroupExample(Scene):
    def construct(self):
        circles = VGroup(*[Circle() for _ in range(5)]).arrange(RIGHT)

        # All animations play simultaneously (lag_ratio=0)
        self.play(AnimationGroup(
            *[Create(c) for c in circles],
            lag_ratio=0
        ))
```

### lag_ratio Parameter

Controls the delay between animation starts:
- `lag_ratio=0`: All start simultaneously
- `lag_ratio=0.5`: Each starts when previous is 50% complete
- `lag_ratio=1`: Each starts when previous finishes (sequential)

```python
class LagRatioDemo(Scene):
    def construct(self):
        squares = VGroup(*[Square() for _ in range(4)]).arrange(RIGHT)

        # Staggered start - each begins when previous is 25% done
        self.play(AnimationGroup(
            *[FadeIn(s) for s in squares],
            lag_ratio=0.25,
            run_time=2
        ))
```

## LaggedStart

Convenience class with default `lag_ratio=0.05` (5% overlap).

```python
class LaggedStartExample(Scene):
    def construct(self):
        dots = VGroup(*[Dot() for _ in range(10)]).arrange(RIGHT)

        # Rapid staggered animation
        self.play(LaggedStart(
            *[GrowFromCenter(d) for d in dots],
            lag_ratio=0.1
        ))
```

### Common LaggedStart Patterns

```python
# Staggered fade in
self.play(LaggedStart(*[FadeIn(m) for m in mobjects], lag_ratio=0.2))

# Wave effect
self.play(LaggedStart(
    *[m.animate.shift(UP * 0.5) for m in mobjects],
    lag_ratio=0.1
))

# Staggered color change
self.play(LaggedStart(
    *[m.animate.set_color(RED) for m in mobjects],
    lag_ratio=0.15
))
```

## Succession

Play animations one after another (equivalent to `lag_ratio=1`).

```python
class SuccessionExample(Scene):
    def construct(self):
        circle = Circle().shift(LEFT * 2)
        square = Square()
        triangle = Triangle().shift(RIGHT * 2)

        # Animations play in sequence
        self.play(Succession(
            Create(circle),
            Create(square),
            Create(triangle)
        ))
```

### Succession vs Multiple play() Calls

```python
# These are equivalent:

# Using Succession
self.play(Succession(
    Create(circle),
    Create(square)
))

# Using separate play calls
self.play(Create(circle))
self.play(Create(square))
```

Succession is useful when you want to treat sequential animations as a single unit.

## Combining Group Types

```python
class CombinedExample(Scene):
    def construct(self):
        group1 = VGroup(*[Circle() for _ in range(3)]).arrange(RIGHT).shift(UP)
        group2 = VGroup(*[Square() for _ in range(3)]).arrange(RIGHT).shift(DOWN)

        # First group appears with stagger, then second group
        self.play(Succession(
            LaggedStart(*[Create(c) for c in group1], lag_ratio=0.2),
            LaggedStart(*[Create(s) for s in group2], lag_ratio=0.2)
        ))
```

## LaggedStartMap

Apply an animation to all submobjects of a mobject with staggered timing.

```python
class LaggedStartMapExample(Scene):
    def construct(self):
        dots = VGroup(*[Dot(radius=0.16) for _ in range(35)]).arrange_in_grid(rows=5, cols=7)

        # Apply FadeIn to all dots with stagger
        self.play(LaggedStartMap(FadeIn, dots, lag_ratio=0.1))
        self.wait(0.5)

        # Change color with stagger using LaggedStart
        self.play(LaggedStart(
            *[dot.animate.set_color(YELLOW) for dot in dots],
            lag_ratio=0.05
        ))
```

LaggedStartMap is cleaner for applying the same animation to each submobject. For property changes, use LaggedStart with `.animate`.

## AnimationGroup with run_time

The total `run_time` is distributed among animations based on `lag_ratio`.

```python
self.play(AnimationGroup(
    *[Create(c) for c in circles],
    lag_ratio=0.5,
    run_time=4  # Total duration is 4 seconds
))
```

## Practical Examples

### Text Appearing Word by Word

```python
class WordByWord(Scene):
    def construct(self):
        words = VGroup(
            Text("Hello"),
            Text("World"),
            Text("!")
        ).arrange(RIGHT)

        self.play(LaggedStart(
            *[Write(w) for w in words],
            lag_ratio=0.5
        ))
```

### Grid Animation

```python
class GridAnimation(Scene):
    def construct(self):
        grid = VGroup(*[
            Square().scale(0.3)
            for _ in range(25)
        ]).arrange_in_grid(5, 5)

        # Diagonal wave effect
        self.play(LaggedStart(
            *[GrowFromCenter(s) for s in grid],
            lag_ratio=0.05
        ))
```

## Best Practices

1. **Use LaggedStart for visual polish** - Staggered animations look more dynamic
2. **Keep lag_ratio small (0.05-0.2)** - Too high feels slow
3. **Use Succession for distinct steps** - When animations are conceptually separate
4. **Adjust run_time with lag_ratio** - More items may need longer total time

### 7.5 Updaters & Continuous Value Tracking

*Source: `rules/updaters.md`*

# Updaters and Dynamic Animations

Updaters allow mobjects to automatically update based on other values or mobjects.

## Basic Updaters

Add a function that runs every frame.

```python
from manim import *

class UpdaterExample(Scene):
    def construct(self):
        dot = Dot()
        label = Text("Follow me").next_to(dot, UP)

        # Label always follows the dot
        label.add_updater(lambda m: m.next_to(dot, UP))

        self.add(dot, label)
        self.play(dot.animate.shift(RIGHT * 3), run_time=2)
        self.play(dot.animate.shift(DOWN * 2), run_time=2)
```

## Updater Syntax

```python
# Lambda function
mobject.add_updater(lambda m: m.move_to(target.get_center()))

# Named function
def follow_target(mob):
    mob.next_to(target, RIGHT)

mobject.add_updater(follow_target)

# With dt (delta time) parameter
def time_based_update(mob, dt):
    mob.rotate(dt * PI)  # Rotate based on time elapsed

mobject.add_updater(time_based_update)
```

## ValueTracker

A mobject that holds a numeric value. Perfect for animating parameters.

```python
class ValueTrackerExample(Scene):
    def construct(self):
        # Create tracker
        tracker = ValueTracker(0)

        # Create number display
        number = DecimalNumber(0, num_decimal_places=2)
        number.add_updater(lambda m: m.set_value(tracker.get_value()))

        # Create circle that grows with tracker
        circle = Circle()
        circle.add_updater(lambda m: m.set_width(tracker.get_value()))

        self.add(number, circle)

        # Animate the tracker
        self.play(tracker.animate.set_value(4), run_time=3)
        self.play(tracker.animate.set_value(1), run_time=2)
```

### ValueTracker Operations

```python
tracker = ValueTracker(5)

# Get and set value
current = tracker.get_value()
tracker.set_value(10)

# Increment
tracker.increment_value(2.5)

# Arithmetic operators (direct manipulation, no animation)
tracker += 1
tracker -= 2
tracker *= 3
tracker /= 2

# Animate changes
self.play(tracker.animate.set_value(100))
self.play(tracker.animate.increment_value(-50))
```

## DecimalNumber with ValueTracker

Display a changing number:

```python
class NumberDisplay(Scene):
    def construct(self):
        tracker = ValueTracker(0)

        number = DecimalNumber(
            0,
            num_decimal_places=2,
            include_sign=True,
            font_size=72
        )
        number.add_updater(lambda m: m.set_value(tracker.get_value()))
        number.add_updater(lambda m: m.move_to(ORIGIN))

        self.add(number)
        self.play(tracker.animate.set_value(100), run_time=3)
```

## always_redraw

Recreate a mobject every frame based on current values.

```python
class AlwaysRedrawExample(Scene):
    def construct(self):
        tracker = ValueTracker(1)

        # Line that always connects two points based on tracker
        line = always_redraw(
            lambda: Line(
                LEFT * 2,
                RIGHT * 2 * tracker.get_value()
            )
        )

        self.add(line)
        self.play(tracker.animate.set_value(2), run_time=2)
        self.play(tracker.animate.set_value(0.5), run_time=2)
```

## Common Updater Patterns

### Following Another Mobject
```python
follower.add_updater(lambda m: m.move_to(leader.get_center()))
follower.add_updater(lambda m: m.next_to(leader, RIGHT))
```

### Pointing at Another Mobject
```python
arrow = Arrow(ORIGIN, RIGHT)
arrow.add_updater(lambda m: m.put_start_and_end_on(
    start.get_center(),
    end.get_center()
))
```

### Rotating Continuously
```python
mobject.add_updater(lambda m, dt: m.rotate(dt * PI))
```

### Matching Properties
```python
# Match color
follower.add_updater(lambda m: m.set_color(leader.get_color()))

# Match position with offset
follower.add_updater(lambda m: m.move_to(leader.get_center() + UP))
```

## Removing Updaters

```python
# Remove specific updater
mobject.remove_updater(updater_function)

# Remove all updaters
mobject.clear_updaters()

# Suspend temporarily
mobject.suspend_updating()
mobject.resume_updating()
```

## Updaters with Animations

Updaters continue running during animations:

```python
class UpdaterDuringAnimation(Scene):
    def construct(self):
        dot = Dot()
        trail = TracedPath(dot.get_center, stroke_color=YELLOW)

        self.add(dot, trail)
        self.play(dot.animate.shift(RIGHT * 3 + UP * 2), run_time=3)
```

## TracedPath

Built-in updater for drawing paths:

```python
class TracedPathExample(Scene):
    def construct(self):
        dot = Dot()
        path = TracedPath(dot.get_center, stroke_width=2, stroke_color=BLUE)

        self.add(dot, path)
        self.play(
            dot.animate.shift(RIGHT * 2),
            dot.animate.shift(UP * 2),
            run_time=3
        )
```

## Best Practices

1. **Use ValueTracker for animated parameters** - Clean and controllable
2. **Use always_redraw for complex shapes** - When updaters get complicated
3. **Clear updaters when done** - Prevent performance issues
4. **Keep updater functions simple** - Complex logic can slow rendering
5. **Use dt for time-based animations** - Frame-rate independent

---

## 8. Starter Templates

### 8.1 Basic Scene Template

*File: `templates/basic_scene.py`*

```python
"""
Basic Scene Template for Manim Community

Copy this file and modify to create your own scene.

Render: manim -pql your_file.py YourScene
"""

from manim import *


class YourScene(Scene):
    """
    Basic scene template.

    Attributes to configure:
        - background_color: Scene background (default: BLACK)
    """

    def construct(self):
        # ============================================================
        # SETUP: Configure scene, create initial objects
        # ============================================================

        # Optional: Set background color
        # self.camera.background_color = "#1a1a2e"

        # Create your mobjects
        title = Text("Your Animation Title", font_size=48)
        shape = Circle(color=BLUE, fill_opacity=0.5)

        # Position objects
        title.to_edge(UP)
        shape.move_to(ORIGIN)

        # ============================================================
        # ANIMATION: Animate your objects
        # ============================================================

        # Write title
        self.play(Write(title))
        self.wait(0.5)

        # Create shape
        self.play(Create(shape))
        self.wait(0.5)

        # Transform or animate
        self.play(shape.animate.scale(1.5).set_color(RED))
        self.wait()

        # ============================================================
        # CLEANUP: Final animations, fade out
        # ============================================================

        self.play(
            FadeOut(title),
            FadeOut(shape),
        )
        self.wait()


# Run this specific scene:
# manim -pql basic_scene.py YourScene
```

### 8.2 Camera Control Scene Template

*File: `templates/camera_scene.py`*

```python
"""
Moving Camera Scene Template for Manim Community

Use this for scenes that require zooming, panning, or following objects.

Render: manim -pql your_file.py YourCameraScene
"""

from manim import *


class YourCameraScene(MovingCameraScene):
    """
    Template for scenes with camera movement.

    Inherits from MovingCameraScene which provides:
        - self.camera.frame: The camera frame mobject
        - Ability to zoom, pan, and follow objects
    """

    def construct(self):
        # ============================================================
        # SETUP: Create objects to showcase camera movement
        # ============================================================

        # Create a grid of shapes to demonstrate camera movement
        shapes = VGroup(*[
            Circle(radius=0.3, color=color, fill_opacity=0.5)
            for color in [RED, BLUE, GREEN, YELLOW, PURPLE]
        ]).arrange(RIGHT, buff=1)

        # Add labels
        labels = VGroup(*[
            Text(str(i + 1), font_size=24).move_to(shape)
            for i, shape in enumerate(shapes)
        ])

        # Title
        title = Text("Camera Movement Demo", font_size=36).to_edge(UP)

        self.add(shapes, labels)
        self.play(Write(title))
        self.wait()

        # ============================================================
        # CAMERA OPERATIONS: Zoom, pan, follow
        # ============================================================

        # --- ZOOM IN ---
        # Save original camera state
        self.camera.frame.save_state()

        # Zoom into first shape
        self.play(
            self.camera.frame.animate.set(width=4).move_to(shapes[0])
        )
        self.wait()

        # --- PAN ---
        # Move camera to another shape
        self.play(
            self.camera.frame.animate.move_to(shapes[2])
        )
        self.wait()

        # --- ZOOM OUT ---
        # Restore original camera
        self.play(Restore(self.camera.frame))
        self.wait()

        # --- FOLLOW OBJECT ---
        # Create moving dot
        dot = Dot(color=RED, radius=0.15).move_to(LEFT * 5)
        self.add(dot)

        # Set camera to follow the dot
        self.camera.frame.add_updater(
            lambda m: m.move_to(dot.get_center())
        )

        # Move the dot (camera follows automatically)
        self.play(dot.animate.move_to(RIGHT * 5), run_time=3)
        self.wait()

        # Stop following
        self.camera.frame.clear_updaters()

        # ============================================================
        # CLEANUP: Reset and fade out
        # ============================================================

        self.play(
            self.camera.frame.animate.move_to(ORIGIN).set(width=14)
        )
        self.play(FadeOut(shapes, labels, title, dot))
        self.wait()


# Run this specific scene:
# manim -pql camera_scene.py YourCameraScene
```

### 8.3 3D ThreeDScene Template

*File: `templates/threed_scene.py`*

```python
"""
3D Scene Template for Manim Community

Use this for 3D visualizations with camera rotation and surfaces.

Render: manim -pql your_file.py Your3DScene
"""

from manim import *
import numpy as np


class Your3DScene(ThreeDScene):
    """
    Template for 3D scenes.

    Inherits from ThreeDScene which provides:
        - set_camera_orientation(phi, theta, gamma)
        - move_camera()
        - begin_ambient_camera_rotation() / stop_ambient_camera_rotation()
        - add_fixed_in_frame_mobjects() for 2D overlays
    """

    def construct(self):
        # ============================================================
        # CAMERA SETUP
        # ============================================================

        # Set initial camera orientation
        # phi: angle from z-axis (0 = top-down, 90 = side view)
        # theta: rotation around z-axis
        self.set_camera_orientation(
            phi=70 * DEGREES,
            theta=-45 * DEGREES
        )

        # ============================================================
        # 3D AXES
        # ============================================================

        axes = ThreeDAxes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            z_range=[-2, 2, 1],
            x_length=6,
            y_length=6,
            z_length=4,
        )

        # Axis labels (stay fixed to camera orientation)
        axis_labels = axes.get_axis_labels(
            x_label="x",
            y_label="y",
            z_label="z"
        )

        self.play(Create(axes))
        self.add(axis_labels)
        self.wait()

        # ============================================================
        # 3D OBJECTS
        # ============================================================

        # --- Basic 3D shapes ---
        sphere = Sphere(radius=0.5, color=BLUE).shift(LEFT * 2)
        cube = Cube(side_length=0.8, color=RED, fill_opacity=0.8)

        self.play(Create(sphere), Create(cube))
        self.wait()

        # --- 3D Surface ---
        # z = sin(sqrt(x^2 + y^2))
        surface = Surface(
            lambda u, v: axes.c2p(
                u, v,
                np.sin(np.sqrt(u ** 2 + v ** 2))
            ),
            u_range=[-2.5, 2.5],
            v_range=[-2.5, 2.5],
            resolution=(20, 20),
            fill_opacity=0.6,
        )
        surface.set_color_by_gradient(BLUE, TEAL, GREEN)

        self.play(
            FadeOut(sphere),
            FadeOut(cube),
            Create(surface),
            run_time=2
        )
        self.wait()

        # ============================================================
        # 2D OVERLAY (Fixed to screen)
        # ============================================================

        # Title that stays fixed to screen (doesn't rotate with 3D scene)
        title = Text("3D Surface Visualization", font_size=36)
        title.to_corner(UL)
        self.add_fixed_in_frame_mobjects(title)
        self.play(Write(title))

        # Math equation overlay
        equation = MathTex(r"z = \sin\sqrt{x^2 + y^2}")
        equation.to_corner(UR)
        self.add_fixed_in_frame_mobjects(equation)
        self.play(Write(equation))

        # ============================================================
        # CAMERA MOVEMENT
        # ============================================================

        # --- Manual camera movement ---
        self.move_camera(phi=45 * DEGREES, theta=30 * DEGREES, run_time=2)
        self.wait()

        # --- Continuous rotation ---
        self.begin_ambient_camera_rotation(rate=0.2)  # radians per second
        self.wait(5)
        self.stop_ambient_camera_rotation()

        # ============================================================
        # CLEANUP
        # ============================================================

        self.play(
            FadeOut(surface),
            FadeOut(axes),
            FadeOut(axis_labels),
            FadeOut(title),
            FadeOut(equation),
        )
        self.wait()


# Run this specific scene:
# manim -pql threed_scene.py Your3DScene
```

---

## 9. End-to-End Implementation Examples

### 9.1 Basic Animation Sequences

*File: `examples/basic_animations.py`*

```python
"""
Basic Animation Patterns for Manim Community

This file demonstrates fundamental animation techniques adapted from 3b1b patterns.
Run with: manim -pql basic_animations.py SceneName
"""

from manim import *


class ShapeCreation(Scene):
    """Demonstrates various ways to create and animate shapes."""

    def construct(self):
        # Create shapes
        circle = Circle(radius=1, color=BLUE, fill_opacity=0.5)
        square = Square(side_length=2, color=RED)
        triangle = Triangle(color=GREEN, fill_opacity=0.8)

        # Arrange shapes
        shapes = VGroup(circle, square, triangle).arrange(RIGHT, buff=1)

        # Different creation animations
        self.play(Create(circle))  # Draw outline progressively
        self.play(DrawBorderThenFill(square))  # Border first, then fill
        self.play(GrowFromCenter(triangle))  # Grow from center point

        self.wait()

        # Transform between shapes
        self.play(Transform(circle, square.copy().shift(UP * 2)))

        self.wait()


class TextAnimations(Scene):
    """Demonstrates text and LaTeX animations."""

    def construct(self):
        # Plain text
        title = Text("Manim Community", font_size=72, color=BLUE)
        self.play(Write(title))
        self.wait()

        # Move title up
        self.play(title.animate.to_edge(UP))

        # LaTeX math
        equation = MathTex(r"e^{i\pi} + 1 = 0", font_size=64)
        self.play(Write(equation))
        self.wait()

        # Transform equation
        expanded = MathTex(r"e^{i\pi} = -1", font_size=64)
        self.play(TransformMatchingTex(equation, expanded))

        self.wait()


class LaggedAnimations(Scene):
    """Demonstrates staggered animations using LaggedStart patterns."""

    def construct(self):
        # Create a grid of dots
        dots = VGroup(*[
            Dot(radius=0.15, color=interpolate_color(BLUE, RED, i / 24))
            for i in range(25)
        ]).arrange_in_grid(rows=5, cols=5, buff=0.5)

        # Staggered fade in
        self.play(
            LaggedStart(*[FadeIn(dot, scale=0.5) for dot in dots], lag_ratio=0.1)
        )
        self.wait()

        # Staggered transformation using LaggedStart with animate
        self.play(
            LaggedStart(
                *[dot.animate.scale(1.5).set_color(YELLOW) for dot in dots],
                lag_ratio=0.05
            )
        )
        self.wait()

        # Wave effect using AnimationGroup with rate_func
        self.play(
            LaggedStart(
                *[dot.animate(rate_func=there_and_back).shift(UP * 0.5) for dot in dots],
                lag_ratio=0.02,
                run_time=2
            )
        )


class AnimationComposition(Scene):
    """Demonstrates combining multiple animations."""

    def construct(self):
        # Create objects
        circle = Circle(color=BLUE, fill_opacity=0.5)
        label = Text("Circle", font_size=36).next_to(circle, DOWN)

        # Group them
        group = VGroup(circle, label)

        # Animate together
        self.play(
            Create(circle),
            Write(label),
            run_time=2
        )
        self.wait()

        # Sequential animations with Succession
        square = Square(color=RED, fill_opacity=0.5).shift(RIGHT * 3)
        square_label = Text("Square", font_size=36).next_to(square, DOWN)

        self.play(
            Succession(
                group.animate.shift(LEFT * 2),
                Create(square),
                Write(square_label),
                lag_ratio=0.5
            )
        )
        self.wait()


class PathAnimations(Scene):
    """Demonstrates movement along paths."""

    def construct(self):
        # Create a path
        path = VMobject()
        path.set_points_smoothly([
            LEFT * 3,
            LEFT * 2 + UP * 2,
            ORIGIN + UP,
            RIGHT * 2 + UP * 2,
            RIGHT * 3,
        ])
        path.set_color(GREY)

        # Create moving object
        dot = Dot(color=RED, radius=0.2)
        dot.move_to(path.get_start())

        self.add(path)
        self.play(Create(path))

        # Move along path
        self.play(MoveAlongPath(dot, path), run_time=3, rate_func=smooth)

        self.wait()


class ColorTransitions(Scene):
    """Demonstrates color manipulation and gradients."""

    def construct(self):
        # Color gradient on shapes
        squares = VGroup(*[
            Square(side_length=0.8, fill_opacity=0.8)
            for _ in range(7)
        ]).arrange(RIGHT, buff=0.2)

        # Apply gradient colors
        colors = [RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE, PINK]
        for square, color in zip(squares, colors):
            square.set_fill(color)
            square.set_stroke(WHITE, width=2)

        self.play(LaggedStartMap(GrowFromCenter, squares, lag_ratio=0.1))
        self.wait()

        # Animate color change
        self.play(
            *[square.animate.set_fill(interpolate_color(BLUE, RED, i / 6))
              for i, square in enumerate(squares)],
            run_time=2
        )
        self.wait()


class GroupOperations(Scene):
    """Demonstrates VGroup operations and arrangements."""

    def construct(self):
        # Create VGroup
        shapes = VGroup(
            Circle(color=RED),
            Square(color=GREEN),
            Triangle(color=BLUE),
        )

        # Arrange horizontally
        shapes.arrange(RIGHT, buff=1)
        self.play(Create(shapes))
        self.wait()

        # Scale entire group
        self.play(shapes.animate.scale(0.5))
        self.wait()

        # Arrange vertically
        self.play(shapes.animate.arrange(DOWN, buff=0.5))
        self.wait()

        # Apply operation to all
        self.play(shapes.animate.set_fill(YELLOW, opacity=0.5))

        self.wait()
```

### 9.2 Mathematical Visualization

*File: `examples/math_visualization.py`*

```python
"""
Mathematical Visualization Patterns for Manim Community

Demonstrates LaTeX rendering, equation animations, and color-coded math.
Adapted from 3b1b patterns for ManimCE compatibility.

Run with: manim -pql math_visualization.py SceneName
"""

from manim import *


class ColorCodedEquation(Scene):
    """Demonstrates color-coding for syntax highlighting in equations."""

    def construct(self):
        # Method 1: Use set_color_by_tex after creation (safer approach)
        equation = MathTex(
            r"\vec{v}_1", r"=", r"\begin{bmatrix} 1 \\ \lambda_1 \end{bmatrix}"
        )
        equation.scale(1.5)

        # Color specific parts
        equation[0].set_color(TEAL)  # \vec{v}_1

        self.play(Write(equation))
        self.wait()

        # Second equation with multiple colored parts
        equation2 = MathTex(r"A", r"\vec{v}_1", r"=", r"\lambda_1", r"\vec{v}_1")
        equation2.scale(1.5)
        equation2[0].set_color(RED)      # A
        equation2[1].set_color(TEAL)     # first \vec{v}_1
        equation2[3].set_color(YELLOW)   # \lambda_1
        equation2[4].set_color(TEAL)     # second \vec{v}_1

        self.play(TransformMatchingTex(equation, equation2))
        self.wait()


class EquationDerivation(Scene):
    """Shows step-by-step equation derivation with highlighting."""

    def construct(self):
        # Starting equation
        eq1 = MathTex(r"x^2 + 5x + 6 = 0")
        eq1.to_edge(UP)

        self.play(Write(eq1))
        self.wait()

        # Factor step
        eq2 = MathTex(r"(x + 2)(x + 3) = 0")
        eq2.next_to(eq1, DOWN, buff=0.8)

        self.play(
            TransformFromCopy(eq1, eq2),
            run_time=1.5
        )
        self.wait()

        # Solutions
        eq3 = MathTex(r"x = -2", color=BLUE)
        eq4 = MathTex(r"x = -3", color=GREEN)
        solutions = VGroup(eq3, eq4).arrange(RIGHT, buff=1)
        solutions.next_to(eq2, DOWN, buff=0.8)

        self.play(
            LaggedStart(
                Write(eq3),
                Write(eq4),
                lag_ratio=0.3
            )
        )

        # Highlight solutions
        boxes = VGroup(
            SurroundingRectangle(eq3, color=BLUE),
            SurroundingRectangle(eq4, color=GREEN),
        )
        self.play(Create(boxes))
        self.wait()


class MatrixTransformation(Scene):
    """Demonstrates matrix notation and transformations."""

    def construct(self):
        # Matrix definition
        matrix = MathTex(
            r"A = \begin{bmatrix} 2 & 1 \\ 1 & 3 \end{bmatrix}"
        ).scale(1.2)

        self.play(Write(matrix))
        self.wait()

        # Move to side
        self.play(matrix.animate.to_edge(LEFT))

        # Show transformation
        vector = MathTex(
            r"\vec{x} = \begin{bmatrix} 1 \\ 1 \end{bmatrix}",
            color=YELLOW
        )
        vector.next_to(matrix, RIGHT, buff=1)

        self.play(Write(vector))
        self.wait()

        # Result
        result = MathTex(
            r"A\vec{x} = \begin{bmatrix} 3 \\ 4 \end{bmatrix}",
            tex_to_color_map={r"\vec{x}": YELLOW}
        )
        result.next_to(vector, RIGHT, buff=1)

        arrow = Arrow(vector.get_right(), result.get_left(), buff=0.2)

        self.play(GrowArrow(arrow), Write(result))
        self.wait()


class IntegralVisualization(Scene):
    """Shows integral notation with visual meaning."""

    def construct(self):
        # Integral expression
        integral = MathTex(
            r"\int_0^1 x^2 \, dx = \frac{1}{3}",
            font_size=64
        )
        integral.to_edge(UP)

        self.play(Write(integral))
        self.wait()

        # Create axes
        axes = Axes(
            x_range=[0, 1.2, 0.5],
            y_range=[0, 1.2, 0.5],
            x_length=5,
            y_length=3,
            axis_config={"include_tip": True},
        )
        axes.shift(DOWN)

        # Create graph
        graph = axes.plot(lambda x: x**2, x_range=[0, 1], color=BLUE)

        # Create area under curve
        area = axes.get_area(graph, x_range=[0, 1], color=BLUE, opacity=0.3)

        self.play(Create(axes))
        self.play(Create(graph))
        self.play(FadeIn(area))
        self.wait()


class SummationNotation(Scene):
    """Demonstrates summation and series notation."""

    def construct(self):
        # Summation formula
        formula = MathTex(
            r"\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}",
            font_size=64
        )

        self.play(Write(formula))
        self.wait()

        # Show first few terms
        terms = MathTex(
            r"= 1 + \frac{1}{4} + \frac{1}{9} + \frac{1}{16} + \cdots",
            font_size=48
        )
        terms.next_to(formula, DOWN, buff=0.8)

        self.play(Write(terms))
        self.wait()

        # Create surrounding box around result
        box = SurroundingRectangle(formula, color=YELLOW, buff=0.2)
        self.play(Create(box))
        self.wait()


class FunctionNotation(Scene):
    """Shows function definition and evaluation."""

    def construct(self):
        # Function definition
        f_def = MathTex(r"f(x) = x^2 + 2x + 1", font_size=56)
        f_def.to_edge(UP)

        self.play(Write(f_def))
        self.wait()

        # Evaluation at x=3
        eval_step1 = MathTex(r"f(3) = 3^2 + 2(3) + 1", font_size=48)
        eval_step2 = MathTex(r"f(3) = 9 + 6 + 1", font_size=48)
        eval_step3 = MathTex(r"f(3) = 16", font_size=48, color=GREEN)

        steps = VGroup(eval_step1, eval_step2, eval_step3)
        steps.arrange(DOWN, buff=0.5)
        steps.next_to(f_def, DOWN, buff=1)

        for step in steps:
            self.play(Write(step))
            self.wait(0.5)

        # Box the answer
        box = SurroundingRectangle(eval_step3, color=GREEN)
        self.play(Create(box))
        self.wait()


class LimitNotation(Scene):
    """Demonstrates limit notation and evaluation."""

    def construct(self):
        # Limit expression
        limit = MathTex(
            r"\lim_{x \to 0} \frac{\sin x}{x} = 1",
            font_size=64
        )

        self.play(Write(limit))
        self.wait()

        # Show approaching behavior
        approaching = MathTex(
            r"x \to 0: \quad",
            r"\frac{\sin(0.1)}{0.1} \approx 0.998",
            font_size=40
        )
        approaching.next_to(limit, DOWN, buff=1)

        self.play(Write(approaching))
        self.wait()


class DerivativeChainRule(Scene):
    """Shows the chain rule for derivatives."""

    def construct(self):
        title = Text("Chain Rule", font_size=48, color=BLUE)
        title.to_edge(UP)

        # Chain rule formula
        rule = MathTex(
            r"\frac{d}{dx}[f(g(x))] = f'(g(x)) \cdot g'(x)",
            font_size=48
        )

        # Example
        example_title = Text("Example:", font_size=36)
        example = MathTex(
            r"\frac{d}{dx}[\sin(x^2)] = \cos(x^2) \cdot 2x",
            tex_to_color_map={
                r"\sin": BLUE,
                r"\cos": BLUE,
                r"x^2": YELLOW,
                r"2x": YELLOW,
            },
            font_size=44
        )

        content = VGroup(rule, example_title, example)
        content.arrange(DOWN, buff=0.8)

        self.play(Write(title))
        self.play(Write(rule))
        self.wait()
        self.play(Write(example_title))
        self.play(Write(example))
        self.wait()


class TexHighlighting(Scene):
    """Advanced tex highlighting techniques."""

    def construct(self):
        # Create equation with substrings to highlight
        equation = MathTex(
            r"E", r"=", r"m", r"c^2",
            font_size=96
        )

        self.play(Write(equation))
        self.wait()

        # Highlight individual parts
        self.play(equation[0].animate.set_color(YELLOW))  # E
        self.wait(0.3)
        self.play(equation[2].animate.set_color(BLUE))    # m
        self.wait(0.3)
        self.play(equation[3].animate.set_color(RED))     # c^2
        self.wait()

        # Add labels
        e_label = Text("Energy", font_size=24, color=YELLOW)
        m_label = Text("Mass", font_size=24, color=BLUE)
        c_label = Text("Speed of Light", font_size=24, color=RED)

        e_label.next_to(equation[0], UP)
        m_label.next_to(equation[2], DOWN)
        c_label.next_to(equation[3], UP)

        self.play(
            FadeIn(e_label, shift=DOWN * 0.3),
            FadeIn(m_label, shift=UP * 0.3),
            FadeIn(c_label, shift=DOWN * 0.3),
        )
        self.wait()
```

### 9.3 Function & Curve Plotting

*File: `examples/graph_plotting.py`*

```python
"""
Graph and Function Plotting Patterns for Manim Community

Demonstrates Axes, NumberPlane, function plotting, and coordinate systems.
Adapted from 3b1b patterns for ManimCE.

Run with: manim -pql graph_plotting.py SceneName
"""

from manim import *
import numpy as np


class BasicAxes(Scene):
    """Basic axes setup and labeling."""

    def construct(self):
        # Create axes
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-2, 2, 1],
            x_length=8,
            y_length=5,
            axis_config={
                "include_tip": True,
                "include_numbers": True,
            },
        )

        # Labels
        x_label = axes.get_x_axis_label("x")
        y_label = axes.get_y_axis_label("y")

        self.play(Create(axes), Write(x_label), Write(y_label))
        self.wait()


class FunctionPlotting(Scene):
    """Plotting functions on axes."""

    def construct(self):
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-1, 9, 2],
            x_length=8,
            y_length=5,
            axis_config={"include_numbers": True},
        )

        # Plot y = x^2
        parabola = axes.plot(
            lambda x: x ** 2,
            color=BLUE,
            x_range=[-3, 3]
        )

        # Label
        label = MathTex(r"y = x^2", color=BLUE)
        label.next_to(parabola, UR)

        self.play(Create(axes))
        self.play(Create(parabola), Write(label))
        self.wait()


class MultipleFunctions(Scene):
    """Multiple functions on same axes."""

    def construct(self):
        axes = Axes(
            x_range=[-2 * PI, 2 * PI, PI / 2],
            y_range=[-1.5, 1.5, 0.5],
            x_length=10,
            y_length=4,
        )

        # Plot sine and cosine
        sine = axes.plot(np.sin, color=BLUE, x_range=[-2 * PI, 2 * PI])
        cosine = axes.plot(np.cos, color=RED, x_range=[-2 * PI, 2 * PI])

        # Labels
        sin_label = MathTex(r"\sin(x)", color=BLUE).to_corner(UR)
        cos_label = MathTex(r"\cos(x)", color=RED).next_to(sin_label, DOWN)

        self.play(Create(axes))
        self.play(Create(sine), Write(sin_label))
        self.play(Create(cosine), Write(cos_label))
        self.wait()


class AreaUnderCurve(Scene):
    """Visualizing area under a curve (integration)."""

    def construct(self):
        axes = Axes(
            x_range=[0, 5, 1],
            y_range=[0, 10, 2],
            x_length=8,
            y_length=5,
        )

        # Function
        func = axes.plot(lambda x: 0.5 * x ** 2, color=BLUE, x_range=[0, 4])

        # Area under curve from x=1 to x=3
        area = axes.get_area(
            func,
            x_range=[1, 3],
            color=BLUE,
            opacity=0.3
        )

        # Integral notation
        integral = MathTex(
            r"\int_1^3 \frac{x^2}{2} \, dx",
            font_size=48
        ).to_corner(UR)

        self.play(Create(axes))
        self.play(Create(func))
        self.play(FadeIn(area))
        self.play(Write(integral))
        self.wait()


class NumberPlaneExample(Scene):
    """Using NumberPlane for coordinate grid."""

    def construct(self):
        # Create number plane
        plane = NumberPlane(
            x_range=[-7, 7, 1],
            y_range=[-4, 4, 1],
            background_line_style={
                "stroke_color": BLUE_D,
                "stroke_width": 1,
                "stroke_opacity": 0.5,
            }
        )

        # Plot a point
        point = Dot(plane.c2p(2, 3), color=RED, radius=0.15)
        point_label = MathTex("(2, 3)", color=RED).next_to(point, UR, buff=0.1)

        # Vector from origin to point
        vector = Arrow(
            plane.c2p(0, 0),
            plane.c2p(2, 3),
            buff=0,
            color=YELLOW
        )

        self.play(Create(plane))
        self.play(GrowArrow(vector))
        self.play(FadeIn(point), Write(point_label))
        self.wait()


class ParametricCurve(Scene):
    """Plotting parametric curves."""

    def construct(self):
        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[-4, 4, 1],
            x_length=7,
            y_length=7,
        )

        # Parametric curve (circle)
        circle = axes.plot_parametric_curve(
            lambda t: np.array([2 * np.cos(t), 2 * np.sin(t), 0]),
            t_range=[0, 2 * PI],
            color=BLUE
        )

        # Lissajous curve
        lissajous = axes.plot_parametric_curve(
            lambda t: np.array([2 * np.sin(3 * t), 2 * np.sin(2 * t), 0]),
            t_range=[0, 2 * PI],
            color=RED
        )

        self.play(Create(axes))
        self.play(Create(circle))
        self.wait()
        self.play(Transform(circle, lissajous))
        self.wait()


class TangentLine(Scene):
    """Showing tangent line to a curve."""

    def construct(self):
        axes = Axes(
            x_range=[-1, 4, 1],
            y_range=[-1, 10, 2],
            x_length=8,
            y_length=5,
        )

        # Function y = x^2
        func = axes.plot(lambda x: x ** 2, color=BLUE, x_range=[0, 3])

        # Point of tangency at x = 2
        x_val = 2
        point = Dot(axes.c2p(x_val, x_val ** 2), color=RED)

        # Tangent line: derivative of x^2 is 2x, at x=2 slope is 4
        tangent = axes.plot(
            lambda x: 4 * (x - 2) + 4,  # Point-slope form
            color=YELLOW,
            x_range=[0.5, 3.5]
        )

        # Label
        slope_label = MathTex(r"m = 2x = 4", color=YELLOW).to_corner(UR)

        self.play(Create(axes))
        self.play(Create(func))
        self.play(FadeIn(point))
        self.play(Create(tangent), Write(slope_label))
        self.wait()


class AnimatedGraph(Scene):
    """Animating a function parameter change."""

    def construct(self):
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-2, 2, 1],
            x_length=8,
            y_length=5,
        )

        # Amplitude tracker
        amplitude = ValueTracker(1)

        # Graph that updates with amplitude
        graph = always_redraw(
            lambda: axes.plot(
                lambda x: amplitude.get_value() * np.sin(x),
                color=BLUE,
                x_range=[-3, 3]
            )
        )

        # Amplitude display
        amp_text = always_redraw(
            lambda: MathTex(
                f"A = {amplitude.get_value():.1f}"
            ).to_corner(UR)
        )

        self.add(axes, graph, amp_text)

        # Animate amplitude change
        self.play(amplitude.animate.set_value(2), run_time=2)
        self.play(amplitude.animate.set_value(0.5), run_time=2)
        self.play(amplitude.animate.set_value(1.5), run_time=1)
        self.wait()


class RiemannSum(Scene):
    """Visualizing Riemann sums for integration."""

    def construct(self):
        axes = Axes(
            x_range=[0, 5, 1],
            y_range=[0, 5, 1],
            x_length=8,
            y_length=5,
        )

        # Function
        func = axes.plot(lambda x: 0.2 * x ** 2, color=BLUE, x_range=[0, 4])

        self.play(Create(axes), Create(func))
        self.wait()

        # Riemann rectangles
        dx_values = [1, 0.5, 0.25]

        for dx in dx_values:
            rects = axes.get_riemann_rectangles(
                func,
                x_range=[1, 3],
                dx=dx,
                color=BLUE,
                fill_opacity=0.5,
                stroke_width=1,
            )

            if dx == 1:
                self.play(Create(rects))
            else:
                self.play(Transform(rects, rects))

            self.wait()


class ImplicitFunction(Scene):
    """Plotting implicit functions (level curves)."""

    def construct(self):
        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[-4, 4, 1],
            x_length=7,
            y_length=7,
        )

        # Circle x^2 + y^2 = 4 as parametric
        circle = axes.plot_parametric_curve(
            lambda t: np.array([2 * np.cos(t), 2 * np.sin(t), 0]),
            t_range=[0, 2 * PI],
            color=BLUE
        )

        # Equation label
        equation = MathTex(r"x^2 + y^2 = 4", color=BLUE).to_corner(UR)

        self.play(Create(axes))
        self.play(Create(circle), Write(equation))
        self.wait()


class CoordinateLabeling(Scene):
    """Advanced coordinate labeling techniques."""

    def construct(self):
        axes = Axes(
            x_range=[-1, 5, 1],
            y_range=[-1, 5, 1],
            x_length=7,
            y_length=7,
            axis_config={"include_numbers": True},
        )

        # Function
        func = axes.plot(lambda x: np.sqrt(x), color=BLUE, x_range=[0, 4])

        # Highlight a specific point
        x_val = 2
        y_val = np.sqrt(2)

        point = Dot(axes.c2p(x_val, y_val), color=RED)

        # Dashed lines to axes
        h_line = DashedLine(
            axes.c2p(0, y_val),
            axes.c2p(x_val, y_val),
            color=GREY
        )
        v_line = DashedLine(
            axes.c2p(x_val, 0),
            axes.c2p(x_val, y_val),
            color=GREY
        )

        # Labels
        x_label = MathTex("2").next_to(axes.c2p(x_val, 0), DOWN)
        y_label = MathTex(r"\sqrt{2}").next_to(axes.c2p(0, y_val), LEFT)

        self.play(Create(axes))
        self.play(Create(func))
        self.play(Create(v_line), Create(h_line))
        self.play(FadeIn(point), Write(x_label), Write(y_label))
        self.wait()


class PolarPlot(Scene):
    """Plotting in polar coordinates."""

    def construct(self):
        # Polar axes
        polar_plane = PolarPlane(
            radius_max=3,
            size=6,
        )

        # Polar curve: r = 1 + sin(theta) (cardioid)
        cardioid = polar_plane.plot_polar_graph(
            lambda theta: 1 + np.sin(theta),
            theta_range=[0, 2 * PI],
            color=BLUE
        )

        # Rose curve: r = 2*cos(3*theta)
        rose = polar_plane.plot_polar_graph(
            lambda theta: 2 * np.cos(3 * theta),
            theta_range=[0, PI],
            color=RED
        )

        self.play(Create(polar_plane))
        self.play(Create(cardioid))
        self.wait()
        self.play(Transform(cardioid, rose))
        self.wait()
```

### 9.4 3D Mathematical Surfaces

*File: `examples/3d_visualization.py`*

```python
"""
3D Visualization Patterns for Manim Community

Demonstrates ThreeDScene, 3D axes, surfaces, and camera control.
Adapted from 3b1b patterns for ManimCE.

Run with: manim -pql 3d_visualization.py SceneName
"""

from manim import *
import numpy as np


class Basic3DScene(ThreeDScene):
    """Basic 3D scene with shapes."""

    def construct(self):
        # Set camera orientation
        self.set_camera_orientation(phi=60 * DEGREES, theta=-45 * DEGREES)

        # 3D shapes
        sphere = Sphere(radius=1, color=BLUE)
        cube = Cube(side_length=1.5, color=RED, fill_opacity=0.7)
        cone = Cone(base_radius=0.8, height=1.5, color=GREEN)

        # Position shapes
        sphere.shift(LEFT * 3)
        cone.shift(RIGHT * 3)

        self.play(Create(sphere), Create(cube), Create(cone))
        self.wait()

        # Rotate camera
        self.begin_ambient_camera_rotation(rate=0.3)
        self.wait(4)
        self.stop_ambient_camera_rotation()


class ThreeDAxesExample(ThreeDScene):
    """3D coordinate axes and plotting."""

    def construct(self):
        self.set_camera_orientation(phi=70 * DEGREES, theta=-45 * DEGREES)

        # Create 3D axes
        axes = ThreeDAxes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            z_range=[-2, 2, 1],
            x_length=6,
            y_length=6,
            z_length=4,
        )

        # Axis labels
        x_label = axes.get_x_axis_label(r"x")
        y_label = axes.get_y_axis_label(r"y")
        z_label = axes.get_z_axis_label(r"z")

        self.play(Create(axes))
        self.add_fixed_orientation_mobjects(x_label, y_label, z_label)
        self.wait()

        # Add a point
        point = Dot3D(axes.c2p(2, 1, 1.5), color=RED, radius=0.1)
        self.play(Create(point))

        # Camera rotation
        self.begin_ambient_camera_rotation(rate=0.2)
        self.wait(5)


class ParametricSurfaceExample(ThreeDScene):
    """3D parametric surface visualization."""

    def construct(self):
        self.set_camera_orientation(phi=60 * DEGREES, theta=-60 * DEGREES)

        axes = ThreeDAxes(
            x_range=[-3, 3],
            y_range=[-3, 3],
            z_range=[-2, 2],
        )

        # Saddle surface: z = x^2 - y^2
        surface = Surface(
            lambda u, v: axes.c2p(u, v, u ** 2 - v ** 2),
            u_range=[-2, 2],
            v_range=[-2, 2],
            resolution=(20, 20),
            fill_opacity=0.7,
        )
        surface.set_color_by_gradient(BLUE, GREEN, YELLOW)

        self.play(Create(axes))
        self.play(Create(surface), run_time=2)

        self.begin_ambient_camera_rotation(rate=0.15)
        self.wait(5)


class SphereVisualization(ThreeDScene):
    """Sphere with parametric representation."""

    def construct(self):
        self.set_camera_orientation(phi=70 * DEGREES, theta=30 * DEGREES)

        # Parametric sphere
        sphere = Surface(
            lambda u, v: np.array([
                np.cos(v) * np.sin(u),
                np.sin(v) * np.sin(u),
                np.cos(u)
            ]),
            u_range=[0, PI],
            v_range=[0, 2 * PI],
            resolution=(20, 40),
        )
        sphere.set_color_by_gradient(BLUE_E, BLUE, TEAL)

        self.play(Create(sphere), run_time=2)

        # Animate camera
        self.begin_ambient_camera_rotation(rate=0.2)
        self.wait(5)


class Function3DPlot(ThreeDScene):
    """Plotting z = f(x, y) surfaces."""

    def construct(self):
        self.set_camera_orientation(phi=65 * DEGREES, theta=-45 * DEGREES)

        axes = ThreeDAxes(
            x_range=[-3, 3],
            y_range=[-3, 3],
            z_range=[-1, 1],
        )

        # Sine wave surface
        surface = Surface(
            lambda u, v: axes.c2p(
                u, v,
                np.sin(np.sqrt(u ** 2 + v ** 2))
            ),
            u_range=[-3, 3],
            v_range=[-3, 3],
            resolution=(30, 30),
        )
        surface.set_color_by_gradient(PURPLE, RED, ORANGE)

        self.play(Create(axes))
        self.play(Create(surface), run_time=2)

        self.begin_ambient_camera_rotation(rate=0.1)
        self.wait(6)


class VectorField3D(ThreeDScene):
    """3D vector field visualization."""

    def construct(self):
        self.set_camera_orientation(phi=60 * DEGREES, theta=-45 * DEGREES)

        axes = ThreeDAxes(
            x_range=[-3, 3],
            y_range=[-3, 3],
            z_range=[-3, 3],
        )

        # Create arrows representing a vector field
        arrows = VGroup()
        for x in np.arange(-2, 3, 1):
            for y in np.arange(-2, 3, 1):
                for z in np.arange(-2, 3, 1):
                    # Vector field: F = (-y, x, z)
                    start = axes.c2p(x, y, z)
                    direction = np.array([-y, x, z]) * 0.3
                    end = start + direction

                    arrow = Arrow3D(
                        start=start,
                        end=end,
                        color=interpolate_color(
                            BLUE, RED,
                            (z + 2) / 4
                        ),
                    )
                    arrows.add(arrow)

        self.play(Create(axes))
        self.play(LaggedStart(*[Create(a) for a in arrows], lag_ratio=0.02))

        self.begin_ambient_camera_rotation(rate=0.1)
        self.wait(5)


class CameraMovement3D(ThreeDScene):
    """Demonstrating 3D camera controls."""

    def construct(self):
        # Start with a default view
        self.set_camera_orientation(phi=75 * DEGREES, theta=-45 * DEGREES)

        # Create a 3D object
        torus = Torus(
            major_radius=2,
            minor_radius=0.5,
            color=BLUE,
            fill_opacity=0.8
        )

        self.play(Create(torus))
        self.wait()

        # Move camera to different angles
        self.move_camera(phi=30 * DEGREES, theta=0, run_time=2)
        self.wait()

        self.move_camera(phi=90 * DEGREES, theta=90 * DEGREES, run_time=2)
        self.wait()

        # Zoom by adjusting frame
        self.move_camera(zoom=1.5, run_time=1)
        self.wait()

        self.move_camera(zoom=0.7, run_time=1)
        self.wait()


class Line3DExample(ThreeDScene):
    """3D lines and curves."""

    def construct(self):
        self.set_camera_orientation(phi=70 * DEGREES, theta=-45 * DEGREES)

        axes = ThreeDAxes()

        # 3D helix
        helix = ParametricFunction(
            lambda t: np.array([
                np.cos(t),
                np.sin(t),
                t / 4
            ]),
            t_range=[0, 4 * PI],
            color=YELLOW,
        )

        # Line in 3D
        line = Line3D(
            start=axes.c2p(-2, -2, -1),
            end=axes.c2p(2, 2, 1),
            color=RED,
        )

        self.play(Create(axes))
        self.play(Create(helix), run_time=2)
        self.play(Create(line))

        self.begin_ambient_camera_rotation(rate=0.15)
        self.wait(5)


class TextIn3D(ThreeDScene):
    """Text and math in 3D scenes."""

    def construct(self):
        self.set_camera_orientation(phi=60 * DEGREES, theta=-45 * DEGREES)

        axes = ThreeDAxes()

        # 3D text (stays fixed to camera)
        title = Text("3D Visualization", font_size=48)
        title.to_corner(UL)
        self.add_fixed_in_frame_mobjects(title)

        # Math label fixed to camera
        equation = MathTex(r"z = x^2 + y^2")
        equation.to_corner(UR)
        self.add_fixed_in_frame_mobjects(equation)

        # Surface
        paraboloid = Surface(
            lambda u, v: axes.c2p(u, v, u ** 2 + v ** 2),
            u_range=[-1.5, 1.5],
            v_range=[-1.5, 1.5],
            resolution=(15, 15),
        )
        paraboloid.set_color_by_gradient(BLUE, GREEN)

        self.play(Write(title), Write(equation))
        self.play(Create(axes))
        self.play(Create(paraboloid))

        self.begin_ambient_camera_rotation(rate=0.1)
        self.wait(5)


class AnimatedSurface(ThreeDScene):
    """Surface that changes over time."""

    def construct(self):
        self.set_camera_orientation(phi=65 * DEGREES, theta=-45 * DEGREES)

        axes = ThreeDAxes(
            x_range=[-3, 3],
            y_range=[-3, 3],
            z_range=[-2, 2],
        )

        # Time parameter
        time = ValueTracker(0)

        # Animated wave surface
        surface = always_redraw(
            lambda: Surface(
                lambda u, v: axes.c2p(
                    u, v,
                    np.sin(np.sqrt(u ** 2 + v ** 2) - time.get_value())
                ),
                u_range=[-3, 3],
                v_range=[-3, 3],
                resolution=(25, 25),
            ).set_color_by_gradient(BLUE, TEAL)
        )

        self.add(axes, surface)

        # Animate
        self.play(
            time.animate.set_value(4 * PI),
            run_time=8,
            rate_func=linear
        )


class MultipleObjects3D(ThreeDScene):
    """Combining multiple 3D objects."""

    def construct(self):
        self.set_camera_orientation(phi=60 * DEGREES, theta=-30 * DEGREES)

        # Create various 3D shapes
        sphere = Sphere(radius=0.5, color=RED).shift(LEFT * 2 + UP)
        cube = Cube(side_length=0.8, color=BLUE).shift(RIGHT * 2)
        cylinder = Cylinder(
            radius=0.4,
            height=1.2,
            color=GREEN
        ).shift(DOWN + LEFT)

        # Arrows connecting them
        arrow1 = Arrow3D(
            start=sphere.get_center(),
            end=cube.get_center(),
            color=YELLOW
        )
        arrow2 = Arrow3D(
            start=cube.get_center(),
            end=cylinder.get_center(),
            color=YELLOW
        )

        self.play(
            Create(sphere),
            Create(cube),
            Create(cylinder),
        )
        self.play(Create(arrow1), Create(arrow2))

        self.begin_ambient_camera_rotation(rate=0.2)
        self.wait(5)
```

### 9.5 Dynamic Updaters & Tracker Patterns

*File: `examples/updater_patterns.py`*

```python
"""
Updater and ValueTracker Patterns for Manim Community

Demonstrates dynamic animations using updaters and ValueTracker.
Adapted from 3b1b's animation patterns for ManimCE.

Run with: manim -pql updater_patterns.py SceneName
"""

from manim import *
import numpy as np


class BasicUpdater(Scene):
    """Simple updater that makes an object follow another."""

    def construct(self):
        # Leader dot
        leader = Dot(color=RED, radius=0.2)
        leader_label = Text("Leader", font_size=24).next_to(leader, UP)

        # Follower that always stays next to leader
        follower = Dot(color=BLUE, radius=0.15)
        follower.add_updater(lambda m: m.next_to(leader, RIGHT, buff=0.5))

        follower_label = Text("Follower", font_size=24, color=BLUE)
        follower_label.add_updater(lambda m: m.next_to(follower, DOWN))

        self.add(leader, leader_label, follower, follower_label)

        # Move the leader - follower automatically follows
        self.play(leader.animate.shift(RIGHT * 3), run_time=2)
        self.play(leader.animate.shift(UP * 2), run_time=2)
        self.play(leader.animate.shift(LEFT * 4 + DOWN), run_time=2)
        self.wait()


class ValueTrackerBasics(Scene):
    """Demonstrates ValueTracker for animating numeric values."""

    def construct(self):
        # Create a ValueTracker
        tracker = ValueTracker(0)

        # DecimalNumber that displays the tracker value
        number = DecimalNumber(
            0,
            num_decimal_places=2,
            font_size=72,
            include_sign=True
        )
        number.add_updater(lambda m: m.set_value(tracker.get_value()))

        # Label
        label = Text("Value: ", font_size=48)
        label.next_to(number, LEFT)

        self.add(label, number)

        # Animate the tracker
        self.play(tracker.animate.set_value(10), run_time=2)
        self.wait(0.5)
        self.play(tracker.animate.set_value(-5), run_time=2)
        self.wait(0.5)
        self.play(tracker.animate.set_value(0), run_time=1)
        self.wait()


class CircleRadiusTracker(Scene):
    """Circle that grows/shrinks with a ValueTracker."""

    def construct(self):
        tracker = ValueTracker(1)

        # Circle with radius controlled by tracker
        circle = always_redraw(
            lambda: Circle(
                radius=tracker.get_value(),
                color=BLUE,
                fill_opacity=0.3
            )
        )

        # Radius label
        radius_text = always_redraw(
            lambda: MathTex(
                f"r = {tracker.get_value():.2f}"
            ).to_edge(UP)
        )

        self.add(circle, radius_text)

        # Animate radius changes
        self.play(tracker.animate.set_value(2.5), run_time=2)
        self.play(tracker.animate.set_value(0.5), run_time=2)
        self.play(tracker.animate.set_value(1.5), run_time=1)
        self.wait()


class RotatingUpdater(Scene):
    """Object that rotates continuously using dt (delta time)."""

    def construct(self):
        # Create rotating group
        square = Square(side_length=2, color=BLUE, fill_opacity=0.5)
        dot = Dot(color=RED).move_to(square.get_corner(UR))

        group = VGroup(square, dot)

        # Add rotation updater with dt for smooth rotation
        group.add_updater(lambda m, dt: m.rotate(dt * PI / 2))

        self.add(group)
        self.wait(4)  # Watch it rotate

        # Remove updater
        group.clear_updaters()
        self.wait()


class TracedPathExample(Scene):
    """Demonstrates TracedPath for drawing motion trails."""

    def construct(self):
        # Moving dot
        dot = Dot(color=RED, radius=0.15)
        dot.move_to(LEFT * 3)

        # Traced path follows the dot
        traced_path = TracedPath(
            dot.get_center,
            stroke_color=YELLOW,
            stroke_width=3
        )

        self.add(traced_path, dot)

        # Move dot in a pattern
        self.play(
            dot.animate.shift(RIGHT * 3 + UP * 2),
            run_time=1.5
        )
        self.play(
            dot.animate.shift(RIGHT * 2 + DOWN * 3),
            run_time=1.5
        )
        self.play(
            dot.animate.shift(LEFT * 2 + UP * 1),
            run_time=1.5
        )
        self.wait()


class SineWaveTracker(Scene):
    """Animated sine wave using ValueTracker."""

    def construct(self):
        # Phase tracker
        phase = ValueTracker(0)

        # Axes
        axes = Axes(
            x_range=[0, 2 * PI, PI / 2],
            y_range=[-1.5, 1.5, 0.5],
            x_length=10,
            y_length=4,
        )

        # Sine wave that updates with phase
        sine_wave = always_redraw(
            lambda: axes.plot(
                lambda x: np.sin(x + phase.get_value()),
                color=BLUE,
                x_range=[0, 2 * PI]
            )
        )

        # Dot that follows the wave
        dot = always_redraw(
            lambda: Dot(color=RED).move_to(
                axes.c2p(PI, np.sin(PI + phase.get_value()))
            )
        )

        self.add(axes, sine_wave, dot)

        # Animate phase change (wave shifts)
        self.play(
            phase.animate.set_value(2 * PI),
            run_time=4,
            rate_func=linear
        )


class ArrowUpdater(Scene):
    """Arrow that always points from one object to another."""

    def construct(self):
        # Two dots
        dot1 = Dot(color=BLUE, radius=0.2).shift(LEFT * 2)
        dot2 = Dot(color=RED, radius=0.2).shift(RIGHT * 2)

        # Arrow that always connects them
        arrow = always_redraw(
            lambda: Arrow(
                dot1.get_center(),
                dot2.get_center(),
                buff=0.3,
                color=YELLOW
            )
        )

        # Distance label
        distance = always_redraw(
            lambda: DecimalNumber(
                np.linalg.norm(dot2.get_center() - dot1.get_center()),
                num_decimal_places=2,
                font_size=36
            ).next_to(arrow, UP)
        )

        self.add(dot1, dot2, arrow, distance)

        # Move dots around
        self.play(dot1.animate.shift(UP * 2), run_time=1.5)
        self.play(dot2.animate.shift(DOWN + LEFT * 2), run_time=1.5)
        self.play(
            dot1.animate.shift(RIGHT * 3),
            dot2.animate.shift(UP * 2),
            run_time=2
        )
        self.wait()


class ParametricCurveTracer(Scene):
    """Traces a parametric curve using ValueTracker."""

    def construct(self):
        # Parameter t
        t_tracker = ValueTracker(0)

        # Parametric curve (Lissajous)
        def parametric_func(t):
            return np.array([
                2 * np.sin(2 * t),
                2 * np.sin(3 * t),
                0
            ])

        # Dot at current position
        dot = always_redraw(
            lambda: Dot(color=RED, radius=0.15).move_to(
                parametric_func(t_tracker.get_value())
            )
        )

        # Traced path
        path = TracedPath(
            dot.get_center,
            stroke_color=BLUE,
            stroke_width=2
        )

        self.add(path, dot)

        # Trace the curve
        self.play(
            t_tracker.animate.set_value(2 * PI),
            run_time=6,
            rate_func=linear
        )
        self.wait()


class MultipleTrackers(Scene):
    """Using multiple ValueTrackers together."""

    def construct(self):
        # Separate trackers for x and y
        x_tracker = ValueTracker(0)
        y_tracker = ValueTracker(0)

        # Dot controlled by both trackers
        dot = always_redraw(
            lambda: Dot(color=RED, radius=0.2).move_to(
                RIGHT * x_tracker.get_value() + UP * y_tracker.get_value()
            )
        )

        # Coordinate display
        coords = always_redraw(
            lambda: MathTex(
                f"({x_tracker.get_value():.1f}, {y_tracker.get_value():.1f})"
            ).to_corner(UL)
        )

        self.add(dot, coords)

        # Animate both trackers
        self.play(x_tracker.animate.set_value(3), run_time=1.5)
        self.play(y_tracker.animate.set_value(2), run_time=1.5)
        self.play(
            x_tracker.animate.set_value(-2),
            y_tracker.animate.set_value(-1),
            run_time=2
        )
        self.wait()


class SpringMassSimulation(Scene):
    """Simple physics simulation with updaters."""

    def construct(self):
        # Physics parameters
        k = 10  # Spring constant
        mass = 1
        damping = 0.5

        # State trackers
        position = ValueTracker(2)  # Initial displacement
        velocity = ValueTracker(0)

        # Ground line
        ground = Line(LEFT * 4, RIGHT * 4, color=WHITE).shift(DOWN * 2)

        # Mass (square)
        mass_obj = always_redraw(
            lambda: Square(
                side_length=0.8,
                color=BLUE,
                fill_opacity=0.8
            ).move_to(UP * position.get_value())
        )

        # Spring (simplified as line)
        spring = always_redraw(
            lambda: Line(
                ground.get_center() + UP * 0.1,
                mass_obj.get_bottom(),
                color=GREY
            )
        )

        self.add(ground, spring, mass_obj)

        # Physics update function
        def physics_update(mob, dt):
            x = position.get_value()
            v = velocity.get_value()

            # F = -kx - damping*v
            acceleration = (-k * x - damping * v) / mass
            new_v = v + acceleration * dt
            new_x = x + new_v * dt

            velocity.set_value(new_v)
            position.set_value(new_x)

        # Add physics updater to a dummy mobject
        physics_driver = Mobject()
        physics_driver.add_updater(physics_update)
        self.add(physics_driver)

        # Let it run
        self.wait(5)

        # Clean up
        physics_driver.clear_updaters()
        self.wait()
```

### 9.6 Lorenz Attractor Simulation

*File: `examples/lorenz_attractor.py`*

```python
"""
Lorenz Attractor - Converted from 3b1b ManimGL to ManimCE

Original: videos/_2024/manim_demo/lorenz.py
This demonstrates a chaotic system visualization with 3D curves and tracing dots.

Run with: manim -pql lorenz_attractor.py LorenzAttractor
"""

from manim import *
from scipy.integrate import solve_ivp
import numpy as np


def lorenz_system(t, state, sigma=10, rho=28, beta=8 / 3):
    """The Lorenz system of differential equations."""
    x, y, z = state
    dxdt = sigma * (y - x)
    dydt = x * (rho - z) - y
    dzdt = x * y - beta * z
    return [dxdt, dydt, dzdt]


def ode_solution_points(function, state0, time, dt=0.01):
    """Solve ODE and return solution points."""
    solution = solve_ivp(
        function,
        t_span=(0, time),
        y0=state0,
        t_eval=np.arange(0, time, dt)
    )
    return solution.y.T


class LorenzAttractor(ThreeDScene):
    """
    Visualization of the Lorenz attractor - a classic chaotic system.

    Shows multiple trajectories starting from nearly identical initial conditions
    that diverge chaotically over time.
    """

    def construct(self):
        # Set up 3D axes
        axes = ThreeDAxes(
            x_range=(-50, 50, 10),
            y_range=(-50, 50, 10),
            z_range=(0, 50, 10),
            x_length=12,
            y_length=12,
            z_length=6,
        )
        axes.center()

        # Set camera orientation
        self.set_camera_orientation(phi=76 * DEGREES, theta=43 * DEGREES)

        self.add(axes)

        # Add the equations (fixed to screen)
        equations = MathTex(
            r"\frac{dx}{dt} &= \sigma(y-x) \\",
            r"\frac{dy}{dt} &= x(\rho-z)-y \\",
            r"\frac{dz}{dt} &= xy-\beta z",
            font_size=30
        )
        equations.to_corner(UL)
        self.add_fixed_in_frame_mobjects(equations)
        self.play(Write(equations))

        # Compute a set of solutions with slightly different initial conditions
        epsilon = 1e-5
        evolution_time = 20  # Reduced for faster rendering
        n_points = 5  # Reduced for performance

        states = [
            [10, 10, 10 + n * epsilon]
            for n in range(n_points)
        ]
        colors = color_gradient([BLUE_E, BLUE_A], len(states))

        # Create curves from ODE solutions
        curves = VGroup()
        for state, color in zip(states, colors):
            points = ode_solution_points(lorenz_system, state, evolution_time)
            # Scale points to fit axes
            scaled_points = [axes.c2p(p[0], p[1], p[2]) for p in points]
            curve = VMobject()
            curve.set_points_smoothly(scaled_points)
            curve.set_stroke(color, width=2, opacity=0.8)
            curves.add(curve)

        # Create dots that will trace the curves
        dots = VGroup(*[
            Dot3D(color=color, radius=0.15)
            for color in colors
        ])

        # Position dots at start of curves
        for dot, curve in zip(dots, curves):
            dot.move_to(curve.get_start())

        self.add(dots)

        # Start ambient camera rotation
        self.begin_ambient_camera_rotation(rate=0.1)

        # Animate curves being drawn with dots following
        self.play(
            *[Create(curve, rate_func=linear) for curve in curves],
            *[MoveAlongPath(dot, curve, rate_func=linear) for dot, curve in zip(dots, curves)],
            run_time=evolution_time,
        )

        self.wait(2)


class LorenzAttractorSimple(ThreeDScene):
    """
    Simplified version with just one trajectory and traced path.
    Better for understanding the basic pattern.
    """

    def construct(self):
        # Set up axes
        axes = ThreeDAxes(
            x_range=(-50, 50, 10),
            y_range=(-50, 50, 10),
            z_range=(0, 50, 10),
            x_length=10,
            y_length=10,
            z_length=5,
        )

        self.set_camera_orientation(phi=70 * DEGREES, theta=45 * DEGREES)
        self.add(axes)

        # Compute single trajectory
        evolution_time = 15
        points = ode_solution_points(lorenz_system, [10, 10, 10], evolution_time)
        scaled_points = [axes.c2p(p[0], p[1], p[2]) for p in points]

        # Create curve
        curve = VMobject()
        curve.set_points_smoothly(scaled_points)
        curve.set_stroke(BLUE, width=2)

        # Create moving dot with traced path
        dot = Dot3D(color=RED, radius=0.2)
        dot.move_to(curve.get_start())

        # Traced path follows the dot
        traced_path = TracedPath(
            dot.get_center,
            stroke_color=YELLOW,
            stroke_width=3,
        )

        self.add(traced_path, dot)

        # Title
        title = Text("Lorenz Attractor", font_size=36)
        title.to_corner(UL)
        self.add_fixed_in_frame_mobjects(title)

        # Animate
        self.begin_ambient_camera_rotation(rate=0.15)
        self.play(
            MoveAlongPath(dot, curve, rate_func=linear),
            run_time=evolution_time,
        )
        self.wait(2)
```

---

## Summary & Quick CLI Reference

| Command | Action |
|---|---|
| `manim -ql scene.py SceneName` | Fast low-resolution preview (480p, 15fps) |
| `manim -qm scene.py SceneName` | Medium resolution (720p, 30fps) |
| `manim -qh scene.py SceneName` | High resolution production render (1080p, 60fps) |
| `manim -qk scene.py SceneName` | 4K ultra HD render (2160p, 60fps) |
| `manim -ql -p scene.py SceneName` | Preview video automatically in default media player |
| `manim -ql -s scene.py SceneName` | Save the final frame as PNG image |
| `manim -ql --format=gif scene.py SceneName` | Render directly as animated GIF |
| `manim -ql --disable_caching scene.py SceneName` | Force clean render without cached partial frames |
