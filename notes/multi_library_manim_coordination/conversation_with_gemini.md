# Multi-Library Manim Coordination for Preparing the SFT Dataset
## Full Verbatim Conversation Record with Gemini & Supervisor Nathan

---

### Original Inbound Consultation to Supervisor Nathan

**From:** Nabin Oli `<nabinoli2004@gmail.com>`  
**Date:** Sun, Sep 6, 2026, 23:18  
**To:** Nathan  
**Subject:** Seeking advice on multi-library coordination (Manim + NumPy/SciPy) in fine-tuned LLMs  

```text
Hi Nathan,

I am a final year undergrad student. I have taken up the generating of the Manim animations using LLM where my supervisor wants me to do LLM fine tuning for better marks. 

I tried:
1. Doing the SFT on supervised pair data
2. Doing DPO but couldn't get any better results due to low data

I have fine tuned the Gemma4:e2b, Qwen2.5-coder-7b and Qwen3-8b but I am not getting any expected results. And in this process I drained some of my money too in google Collab , Runpod and experiments. I tried reaching out to people in Nepal but not getting any inputs. 

At last, I am thinking of doing Continuous Pretraining(CPT) then SFT on the dataset. I hope this will work. 

My question is: Since Manim animation needs to pair up the Manim library with Scientific computing library (like for visualising Lorenz attractor we use solve_ivp function). Do you have insights for me how to do this pair up and finetune the LLM for making the best Manim animation. 

Thank you for your time. Your guidance is much appreciated and will help me to ace my final year project. 

Nabin Oli
Final year Student @ Sunway College Kathmandu Nepal
Pursuing the goal of making best Manim animations as final year project
(Nepal Kathmandu)
olinabin.com.np
```

---

### Supervisor Nathan's Strategic Reply

**Subject:** Re: Seeking advice on multi-library coordination (Manim + NumPy/SciPy) in fine-tuned LLMs  

Hi Nabin,

It is great to hear from you, and I appreciate the detailed update on your progress. It is clear you have been putting a lot of hard work into this, and experimenting with state-of-the-art models like Qwen and Gemma is exactly the kind of ambition I like to see in a final-year project.

However, I want to ensure you are working efficiently and not burning through your personal funds needlessly. Let's course-correct a bit to get you on track for top marks.

#### 1. Reconsidering Continuous Pretraining (CPT)
I strongly advise against attempting Continuous Pretraining. CPT requires a massive corpus of text (billions of tokens) and significant compute power to effectively shift the model's foundational understanding. Doing this on Colab or RunPod will drain your remaining funds very quickly and is highly unlikely to yield better results than targeted fine-tuning for a project of this scope.

Instead of throwing more compute at the problem, we need to focus on data quality and prompt formulation. For coding tasks, 500 perfectly curated, step-by-step examples will drastically outperform thousands of low-quality snippets.

#### 2. Multi-Library Coordination (Manim + SciPy)
The challenge with generating code that combines manim and scipy (like `solve_ivp` for a Lorenz attractor) is that the LLM has to simultaneously act as a mathematician and a visualizer. You need to structure your SFT dataset to teach the model to separate these concerns.

Here is how you should structure the target outputs in your fine-tuning dataset:

* **Enforce Chain-of-Thought (CoT)**: Do not train the model to just output the raw code. Train it to write a brief plan first. Your SFT target should look something like:
  - *Plan: First, define the Lorenz system differential equations.*
  - *Plan: Second, use `scipy.integrate.solve_ivp` to compute the trajectory array.*
  - *Plan: Third, map the resulting NumPy arrays to 3D coordinates using Manim's `set_points_as_corners`.*
  - *Code: [Then the actual Python script follows].*
* **Bridge the Data Gap**: LLMs often struggle to understand how SciPy outputs map to Manim inputs. Ensure your training examples explicitly demonstrate how to unpack the `solve_ivp` solution (which is usually a dense numerical array) and feed it into Manim objects. Focus heavily on examples using `VMobject.set_points_smoothly` or `ValueTracker`, as these are the primary bridges between NumPy arrays and Manim animations.
* **Modularize the Code Generation**: Teach the model to write a `compute_data()` function (using SciPy/NumPy) and a separate `construct()` method (for Manim). When the LLM sees these as two distinct tasks within the same file, it is less likely to hallucinate Manim syntax into the math logic.

#### Your Next Steps
Before you run any more fine-tuning jobs and spend more money, I want you to step back from the compute side.

1. Take 20-30 of your existing SFT data pairs that require SciPy + Manim.
2. Rewrite the target outputs manually to include the Chain-of-Thought reasoning I mentioned above, and ensure the Python code perfectly bridges the two libraries.
3. Could you send me 3 of these manually formatted examples by later this week? Let's review the data structure before you spin up another GPU.

Keep up the great effort, Nabin. You are tackling a complex problem, and we will get this working.

Best regards,  
Nathan  
Supervisor

---

### Manim Library Anatomy & Advanced Modules

The complete anatomy of the Manim library:

* **Animations**: `animation`, `changing`, `composition`, `creation`, `fading`, `growing`, `indication`, `movement`, `numbers`, `rotation`, `specialized`, `speedmodifier`, `transform`, `transform_matching_parts`, `updaters`.
* **Cameras**: `camera`, `mapping_camera`, `moving_camera`, `multi_camera`, `three_d_camera`.
* **Configuration**: `_config`, `utils`, `logger_utils`.
* **Mobjects**: `frame`, `geometry`, `graph`, `graphing`, `logo`, `matrix`, `mobject`, `svg`, `table`, `text`, `three_d`, `types`, `utils`, `value_tracker`, `vector_field`.
* **Scenes**: `moving_camera_scene`, `section`, `scene`, `scene_file_writer`, `three_d_scene`, `vector_space_scene`, `zoomed_scene`.
* **Utilities**: `bezier`, `cli`, `color`, `commands`, `config_ops`, `constants`, `data_structures`, `debug`, `deprecation`, `docbuild`, `hashing`, `images`, `ipython_magic`, `iterables`, `paths`, `rate_functions`, `simple_functions`, `sounds`, `space_ops`, `testing`, `tex`, `tex_file_writing`, `tex_templates`, `typing`.

#### Roadmap for Fine-Tuning Advanced Animations

1. **The Core of Dynamic Motion**:
   - `value_tracker`: Stores numerical values changing smoothly over time.
   - `updaters`: Redraw Mobjects every frame based on `ValueTracker`.
   - **SciPy Connection**: When using `solve_ivp` from SciPy, train LLMs to load the resulting NumPy array, set up a `ValueTracker` as an array index, and use an updater to smoothly draw a line or move a dot across pre-computed coordinates frame-by-frame.
2. **Advanced Visual Environments**:
   - `three_d_scene` & `three_d_camera`: Use `self.set_camera_orientation(phi=..., theta=...)` for sweeping, rotating views.
   - `vector_field` & `graphing`: Map equations to `ArrowVectorField` or `StreamLines` for fluid dynamics and fields.
3. **Elegant Transitions**:
   - `transform_matching_parts`: Visually move identical LaTeX terms (`x` or `2`) to new positions.
   - `rate_functions`: Apply `rate_func=there_and_back` or `rate_func=smooth` to eliminate robotic linear movements.

---

### Complete SFT Data Pair: SciPy + ValueTracker + Updaters (Lorenz Attractor)

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are an expert Python developer specializing in Manim animations and scientific computing. When asked to create an animation, first write a numbered Chain-of-Thought plan, then provide the complete executable code."
    },
    {
      "role": "user",
      "content": "Write a Manim script that animates the trajectory of a Lorenz attractor in a 3D scene. Use scipy.integrate.solve_ivp to calculate the coordinates, and use a ValueTracker with an updater to draw the path smoothly."
    },
    {
      "role": "assistant",
      "content": "1. Plan: Define the Lorenz system's differential equations with standard parameters (sigma=10, rho=28, beta=8/3).\n2. Plan: Use `scipy.integrate.solve_ivp` to compute the trajectory over a set time span, storing the dense numerical output into a 2D numpy array of 3D coordinates.\n3. Plan: Initialize a `ThreeDScene`, set the camera orientation, and add `ThreeDAxes`.\n4. Plan: Create a `ValueTracker` that represents the current index of the pre-computed coordinate array.\n5. Plan: Create a `VMobject` for the curve and attach an `updater` that reads the `ValueTracker`'s value, slices the coordinate array up to that index, and redraws the curve using `set_points_as_corners`.\n6. Plan: Animate the `ValueTracker` from 0 to the length of the coordinate array.\n\n```python\nfrom manim import *\nimport numpy as np\nfrom scipy.integrate import solve_ivp\n\nclass LorenzAttractor(ThreeDScene):\n    def construct(self):\n        # 1. Define the Math\n        def lorenz_system(t, state, sigma=10, rho=28, beta=8/3):\n            x, y, z = state\n            dxdt = sigma * (y - x)\n            dydt = x * (rho - z) - y\n            dzdt = x * y - beta * z\n            return [dxdt, dydt, dzdt]\n\n        # 2. Compute the Data\n        t_span = (0, 25)\n        t_eval = np.linspace(t_span[0], t_span[1], 2500)\n        initial_state = [1.0, 1.0, 1.0]\n\n        solution = solve_ivp(lorenz_system, t_span, initial_state, t_eval=t_eval)\n        \n        # Convert SciPy output to a format Manim can use (scaled for visibility)\n        x, y, z = solution.y\n        points = np.vstack((x, y, z)).T * 0.1 \n\n        # 3. Scene Setup\n        axes = ThreeDAxes()\n        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES)\n        self.add(axes)\n\n        # 4. Animation Setup\n        tracker = ValueTracker(0)\n        \n        # The path that will grow over time\n        trajectory = VMobject()\n        trajectory.set_color(BLUE)\n\n        # The leading dot\n        dot = Dot3D(point=axes.c2p(*points[0]), color=YELLOW)\n\n        # 5. Updaters\n        def update_trajectory(mob):\n            current_idx = int(tracker.get_value())\n            if current_idx > 0:\n                # Slice the array up to the current index and map to axes\n                current_points = [axes.c2p(*p) for p in points[:current_idx + 1]]\n                mob.set_points_as_corners(current_points)\n\n        def update_dot(mob):\n            current_idx = int(tracker.get_value())\n            mob.move_to(axes.c2p(*points[current_idx]))\n\n        trajectory.add_updater(update_trajectory)\n        dot.add_updater(update_dot)\n\n        self.add(trajectory, dot)\n\n        # 6. Execute Animation\n        self.play(\n            tracker.animate.set_value(len(points) - 1),\n            run_time=15,\n            rate_func=linear\n        )\n        self.wait()\n```"
    }
  ]
}
```

#### Why This Works
* **The Array Slice Trick**: `points[:current_idx + 1]`. ValueTracker tracks the array index, not continuous floating seconds.
* **Coordinate Mapping**: Wraps raw points in `axes.c2p(*p)` (coordinates to point).
* **Separation of Concerns**: `solve_ivp` runs once upfront, not 60 times a second inside updaters.

---

### Voiceover Synchronization Pattern (`manim-voiceover`)

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are an expert Python developer specializing in Manim animations, scientific computing, and audio-visual synchronization using manim-voiceover. First write a numbered Chain-of-Thought plan, then provide the complete executable code."
    },
    {
      "role": "user",
      "content": "Write a Manim script that animates the trajectory of a Lorenz attractor in a 3D scene. Include a voiceover that explains what is happening. Synchronize the drawing of the trajectory exactly to the duration of the spoken explanation."
    },
    {
      "role": "assistant",
      "content": "1. Plan: Inherit from both `VoiceoverScene` and `ThreeDScene` to support both voice generation and 3D camera controls.\n2. Plan: Initialize a TTS service (e.g., GTTSService) using `self.set_speech_service()`.\n3. Plan: Define the Lorenz system and compute the trajectory using `scipy.integrate.solve_ivp`.\n4. Plan: Set up the 3D axes, camera orientation, and the `ValueTracker` for drawing the curve.\n5. Plan: Use the `with self.voiceover(text=...) as tracker:` context manager. This will generate the audio and provide the exact duration of the spoken text.\n6. Plan: Execute the animation using `run_time=tracker.duration` to ensure the trajectory finishes drawing exactly when the voiceover stops.\n\n```python\nfrom manim import *\nfrom manim_voiceover import VoiceoverScene\nfrom manim_voiceover.services.gtts import GTTSService\nimport numpy as np\nfrom scipy.integrate import solve_ivp\n\n# Inherit from VoiceoverScene first for proper MRO (Method Resolution Order)\nclass LorenzWithVoice(VoiceoverScene, ThreeDScene):\n    def construct(self):\n        # 1. Initialize Speech Service\n        self.set_speech_service(GTTSService())\n\n        # 2. Math & Data Setup (SciPy)\n        def lorenz_system(t, state, sigma=10, rho=28, beta=8/3):\n            x, y, z = state\n            return [sigma * (y - x), x * (rho - z) - y, x * y - beta * z]\n\n        t_span = (0, 25)\n        solution = solve_ivp(lorenz_system, t_span, [1.0, 1.0, 1.0], t_eval=np.linspace(t_span[0], t_span[1], 2500))\n        points = np.vstack(solution.y).T * 0.1 \n\n        # 3. Visual Setup\n        axes = ThreeDAxes()\n        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES)\n        self.add(axes)\n\n        path_tracker = ValueTracker(0)\n        trajectory = VMobject().set_color(BLUE)\n\n        def update_trajectory(mob):\n            idx = int(path_tracker.get_value())\n            if idx > 0:\n                mob.set_points_as_corners([axes.c2p(*p) for p in points[:idx + 1]])\n\n        trajectory.add_updater(update_trajectory)\n        self.add(trajectory)\n\n        # 4. Voiceover & Synchronized Animation\n        script = \"The Lorenz attractor is a set of chaotic solutions to the Lorenz system. Notice how the trajectory orbits two distinct points, creating a butterfly shape, but never crosses its own path.\"\n        \n        with self.voiceover(text=script) as audio_tracker:\n            self.play(\n                path_tracker.animate.set_value(len(points) - 1),\n                run_time=audio_tracker.duration, # Crucial: Syncs visual to audio\n                rate_func=linear\n            )\n        self.wait(2)\n```"
    }
  ]
}
```

---

### Multi-Part Voiceover Pattern

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are an expert Python developer specializing in Manim animations, scientific computing, and voiceover synchronization using manim-voiceover. Plan first, then write clean, bug-free executable code."
    },
    {
      "role": "user",
      "content": "Create a multi-step animation introducing the Lorenz Attractor: first introduce the equations with narration, then transition to drawing the 3D trajectory with narration."
    },
    {
      "role": "assistant",
      "content": "1. Plan: Inherit from `VoiceoverScene` and `ThreeDScene`.\n2. Plan: Set up `GTTSService` for speech synthesis.\n3. Plan: Part 1 - Display the differential equations in 2D with introductory voiceover.\n4. Plan: Part 2 - Fade out equations, reorient camera to 3D, and generate the trajectory while explaining the butterfly geometry, binding `run_time` to each audio segment.\n\n```python\nfrom manim import *\nfrom manim_voiceover import VoiceoverScene\nfrom manim_voiceover.services.gtts import GTTSService\nimport numpy as np\nfrom scipy.integrate import solve_ivp\n\nclass MultiPartLorenz(VoiceoverScene, ThreeDScene):\n    def construct(self):\n        self.set_speech_service(GTTSService())\n\n        # --- Section 1: Theory ---\n        title = Title(\"The Lorenz System\").to_edge(UP)\n        eqs = MathTex(\n            r\"\\frac{dx}{dt} &= \\sigma(y - x)\\\\\",\n            r\"\\frac{dy}{dt} &= x(\\rho - z) - y\\\\\",\n            r\"\\frac{dz}{dt} &= xy - \\beta z\"\n        ).scale(0.8)\n\n        with self.voiceover(\n            text=\"The Lorenz attractor originated as a simplified mathematical model for atmospheric convection.\"\n        ) as trk1:\n            self.play(Write(title), run_time=trk1.duration * 0.4)\n            self.play(Write(eqs), run_time=trk1.duration * 0.6)\n\n        # --- Section 2: Transition & Trajectory ---\n        with self.voiceover(\n            text=\"When numerically integrated in three dimensions, the solution forms a deterministic chaotic flow.\"\n        ) as trk2:\n            self.play(FadeOut(title), FadeOut(eqs), run_time=trk2.duration * 0.3)\n            \n            # Pre-compute data\n            def lorenz(t, s, sig=10, rho=28, beta=8/3):\n                return [sig * (s[1] - s[0]), s[0] * (rho - s[2]) - s[1], s[0] * s[1] - beta * s[2]]\n            \n            sol = solve_ivp(lorenz, (0, 20), [1.0, 1.0, 1.0], t_eval=np.linspace(0, 20, 1500))\n            points = np.vstack(sol.y).T * 0.12\n\n            axes = ThreeDAxes()\n            self.move_camera(phi=70 * DEGREES, theta=45 * DEGREES, run_time=trk2.duration * 0.7)\n            self.add(axes)\n\n        # --- Section 3: Drawing the Trajectory ---\n        tracker = ValueTracker(0)\n        curve = VMobject().set_color(BLUE)\n\n        def update_curve(mob):\n            idx = int(tracker.get_value())\n            if idx > 0:\n                mob.set_points_as_corners([axes.c2p(*p) for p in points[:idx + 1]])\n\n        curve.add_updater(update_curve)\n        self.add(curve)\n\n        with self.voiceover(\n            text=\"The system never repeats itself, tracing an infinite path within a bounded region known as a strange attractor.\"\n        ) as trk3:\n            self.play(\n                tracker.animate.set_value(len(points) - 1),\n                run_time=trk3.duration,\n                rate_func=linear\n            )\n        self.wait(1)\n```"
    }
  ]
}
```

---

### Critical Gotchas in LLM-Generated Manim + Voiceover + SciPy

1. **Context Manager Scope & Audio Stacking**: All `self.play()` calls intended to accompany speech must remain indented inside the `with` block.
2. **Cumulative Sub-Animation Timing Mismatches**: Sub-animations inside a voiceover block must partition `tracker.duration` (e.g., `0.4` and `0.6`).
3. **SciPy Integration Inside Updaters (Performance Crash)**: Precompute numerical arrays upfront. Updaters should only perform index slicing.
4. **2D vs. 3D Camera Coordinate Conflicts**: Fade out 2D elements or use `self.add_fixed_in_frame_mobjects()`.
5. **Empty Line Interpolation (IndexError on zero length)**: Guard updaters with `if idx > 1:` before applying points to `set_points_as_corners`.
6. **Method Resolution Order (MRO)**: Always declare `VoiceoverScene` leftmost: `class SceneName(VoiceoverScene, ThreeDScene):`.

---

### Automated Matrix Synthesis & Execution Pipeline

```text
[ Taxonomy Matrix ] 
         │ (Random / Systematic Sample)
         ▼
[ Prompt Synthesizer ] ──► (Generates User Task: Math Goal + Visual Constraints)
         │
         ▼
[ Teacher LLM Engine ] ──► (Outputs: CoT Plan + Manim Script)
         │
         ▼
[ Static Syntax & AST Check ] ──── (Fails? Drop / Self-Refine)
         │ (Pass)
         ▼
[ Headless Execution Sandbox ] ── (Fails? Drop / Auto-Repair via Traceback)
         │ (Exit Code 0 + Non-empty MP4)
         ▼
[ Curated SFT Dataset (.jsonl) ]
```

* Target sample count: **300 to 500 fully verified, diverse examples**.
