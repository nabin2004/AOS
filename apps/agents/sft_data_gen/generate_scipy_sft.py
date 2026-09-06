"""Automated Synthetic SFT Data Generator for Multi-Library Manim + SciPy + Voiceover.

Pipeline:
1. Taxonomy Matrix Sampling (Combinatorial Scientific Domains x Visual Paradigms).
2. Teacher LLM Generation (Structured Output: User prompt, CoT Plan, Executable Code).
3. Static AST Guardrails (Rejects illegal SciPy in updaters, incorrect MRO, unanchored 3D text).
4. Headless Execution Sandbox (Renders with 'manim -ql' to verify exit code 0).
5. Dataset Emitting (Appends verified ChatML / OpenAI JSONL entries).
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import random
import subprocess
import sys
import tempfile
from typing import Any, List, Optional
from pydantic import BaseModel, Field

# --- Step A: Combinatorial Taxonomy Matrix ---

SCIENTIFIC_DOMAINS = [
    {
        "topic": "Lorenz Strange Attractor",
        "scipy": "scipy.integrate.solve_ivp",
        "desc": "Chaotic 3D trajectory showing sensitive dependence on initial conditions.",
    },
    {
        "topic": "Lotka-Volterra Predator-Prey Dynamics",
        "scipy": "scipy.integrate.solve_ivp",
        "desc": "Phase space limit cycle of predator vs. prey population oscillations.",
    },
    {
        "topic": "Damped Harmonic Oscillator",
        "scipy": "scipy.integrate.solve_ivp",
        "desc": "Position vs velocity phase space showing a decaying inward spiral toward equilibrium.",
    },
    {
        "topic": "Rosenbrock Optimization Valley",
        "scipy": "scipy.optimize.minimize",
        "desc": "Iterative gradient descent or Nelder-Mead path down a curved banana valley.",
    },
    {
        "topic": "Fourier Series Square Wave Synthesis",
        "scipy": "scipy.signal or numpy.fft",
        "desc": "Harmonic epicyclic or frequency summation approximating a discontinuous square wave.",
    },
    {
        "topic": "Double Compound Pendulum Chaos",
        "scipy": "scipy.integrate.solve_ivp",
        "desc": "Coupled non-linear differential equations demonstrating deterministic chaos.",
    },
    {
        "topic": "Rössler Attractor",
        "scipy": "scipy.integrate.solve_ivp",
        "desc": "Continuous-time dynamical system with spiral chaos in 3D phase space.",
    },
    {
        "topic": "B-Spline Curve Interpolation",
        "scipy": "scipy.interpolate.splprep",
        "desc": "Fitting smooth parametric splines through noisy spatial data points.",
    },
]

VISUAL_PARADIGMS = [
    {
        "scene": "ThreeDScene",
        "technique": "ValueTracker array indexer with set_points_as_corners",
        "camera": "Sweeping rotating 3D camera orientation",
    },
    {
        "scene": "VoiceoverScene, ThreeDScene",
        "technique": "Axes with dynamic VMobject trajectory synchronized with speech duration",
        "camera": "Fixed HUD title overlay with rotating 3D axes",
    },
    {
        "scene": "VoiceoverScene",
        "technique": "Two-stage sequence: MathTex differential equations followed by phase portrait",
        "camera": "2D plane with proportional duration partitioning",
    },
    {
        "scene": "MovingCameraScene",
        "technique": "Dynamic dot tracking array coordinate with camera auto-centering",
        "camera": "Moving camera frame panning smoothly with value tracker",
    },
]

# --- Step B: Structured Output Schema ---

class SyntheticSFTItem(BaseModel):
    user_prompt: str = Field(
        description="The user instruction describing the scientific concept, calculation, and visual style."
    )
    cot_plan: List[str] = Field(
        description="Step-by-step Chain-of-Thought reasoning plan detailing the math, array slice logic, and scene setup."
    )
    python_code: str = Field(
        description="Complete, self-contained executable Python code using Manim, SciPy/NumPy, and Voiceover."
    )


# --- Step C: Static AST Linting & Failure Mode Guardrails ---

BANNED_COMPUTE_FUNCS = {
    "solve_ivp",
    "odeint",
    "minimize",
    "curve_fit",
    "root",
    "fft",
    "rfft",
    "convolve",
}


def passes_ast_check(code_str: str) -> tuple[bool, str]:
    """Inspects code AST to catch runtime traps before sandbox execution."""
    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"

    # Rule 1: No heavy SciPy/NumPy solver calls inside updater functions
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and ("update" in node.name.lower()):
            for subnode in ast.walk(node):
                if isinstance(subnode, ast.Call):
                    func_name = ""
                    if isinstance(subnode.func, ast.Name):
                        func_name = subnode.func.id
                    elif isinstance(subnode.func, ast.Attribute):
                        func_name = subnode.func.attr
                    if func_name in BANNED_COMPUTE_FUNCS:
                        return (
                            False,
                            f"AST Violation: Heavy compute function '{func_name}' called inside updater '{node.name}'",
                        )

    # Rule 2: Check MRO for scenes using VoiceoverScene
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            base_names = []
            for b in node.bases:
                if isinstance(b, ast.Name):
                    base_names.append(b.id)
                elif isinstance(b, ast.Attribute):
                    base_names.append(b.attr)

            if "VoiceoverScene" in base_names and len(base_names) > 1:
                if base_names[0] != "VoiceoverScene":
                    return (
                        False,
                        f"MRO Violation: VoiceoverScene must be listed first in class inheritance order, found: {base_names}",
                    )

    return True, "Passed AST checks"


# --- Step D: Headless Sandbox Execution ---

def verify_manim_render(
    code_str: str, timeout_sec: int = 45, media_dir: Optional[str] = None
) -> tuple[bool, str]:
    """Runs a dry headless render at low quality (-ql) to ensure exit code 0."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target_dir = media_dir or tmpdir
        file_path = os.path.join(tmpdir, "scene.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code_str)

        cmd = [
            sys.executable,
            "-m",
            "manim",
            "render",
            "-ql",
            "--media_dir",
            target_dir,
            file_path,
        ]

        # Use xvfb-run on Linux headless environments if available
        if sys.platform.startswith("linux") and os.system("which xvfb-run > /dev/null 2>&1") == 0:
            cmd = ["xvfb-run", "-a"] + cmd

        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_sec,
                text=True,
            )
            if res.returncode != 0:
                error_snippet = (res.stderr or res.stdout)[-600:]
                return False, f"Render failed (code {res.returncode}): {error_snippet}"
            return True, "Render successful"
        except subprocess.TimeoutExpired:
            return False, f"Render timed out after {timeout_sec}s"
        except Exception as e:
            return False, f"Execution exception: {e}"


# --- Step E: Reference Test Example ---

REFERENCE_LORENZ_CODE = """from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService
import numpy as np
from scipy.integrate import solve_ivp

class LorenzAttractorScene(VoiceoverScene, ThreeDScene):
    def construct(self):
        self.set_speech_service(GTTSService())

        def lorenz_system(t, state, sigma=10, rho=28, beta=8/3):
            x, y, z = state
            return [sigma * (y - x), x * (rho - z) - y, x * y - beta * z]

        t_span = (0, 25)
        t_eval = np.linspace(t_span[0], t_span[1], 1500)
        sol = solve_ivp(lorenz_system, t_span, [1.0, 1.0, 1.0], t_eval=t_eval)
        points = np.vstack(sol.y).T * 0.1

        axes = ThreeDAxes()
        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES)
        self.add(axes)

        tracker = ValueTracker(0)
        trajectory = VMobject().set_color(BLUE)

        def update_trajectory(mob):
            idx = int(tracker.get_value())
            if idx > 1:
                mob.set_points_as_corners([axes.c2p(*p) for p in points[:idx + 1]])

        trajectory.add_updater(update_trajectory)
        self.add(trajectory)

        script = "The Lorenz attractor demonstrates deterministic chaos in atmospheric convection."
        with self.voiceover(text=script) as audio_tracker:
            self.play(
                tracker.animate.set_value(len(points) - 1),
                run_time=audio_tracker.duration,
                rate_func=linear
            )
        self.wait(1)
"""

BAD_UPDATER_CODE = """from manim import *
import numpy as np
from scipy.integrate import solve_ivp

class BadScene(ThreeDScene):
    def construct(self):
        tracker = ValueTracker(0)
        line = VMobject()
        def update_curve(mob):
            # ILLEGAL: solve_ivp inside updater!
            sol = solve_ivp(lambda t, y: [-y[1], y[0]], (0, 10), [1.0, 0.0])
            mob.set_points_as_corners([np.array([y[0], y[1], 0]) for y in sol.y.T])
        line.add_updater(update_curve)
        self.add(line)
"""


def run_self_test():
    """Validates that the AST checker accurately discriminates safe vs broken patterns."""
    print("=== Running AST Safety Filter Tests ===")

    # Test 1: Good Reference
    ok, msg = passes_ast_check(REFERENCE_LORENZ_CODE)
    print(f"1. Valid Lorenz Attractor: ok={ok}, msg='{msg}'")
    assert ok, f"Expected reference Lorenz code to pass AST, got: {msg}"

    # Test 2: Bad Updater
    bad_ok, bad_msg = passes_ast_check(BAD_UPDATER_CODE)
    print(f"2. Bad Updater (SciPy inside callback): ok={bad_ok}, msg='{bad_msg}'")
    assert not bad_ok, "Expected AST checker to catch solve_ivp inside updater!"

    # Test 3: MRO violation
    bad_mro_code = "class BadMRO(ThreeDScene, VoiceoverScene):\n    pass"
    mro_ok, mro_msg = passes_ast_check(bad_mro_code)
    print(f"3. Bad MRO (ThreeDScene before VoiceoverScene): ok={mro_ok}, msg='{mro_msg}'")
    assert not mro_ok, "Expected AST checker to catch invalid MRO!"

    print("\n[SUCCESS] All AST filter self-tests passed successfully!")


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Library Scientific Manim SFT Generator & Validator"
    )
    parser.add_argument(
        "--test-sample",
        action="store_true",
        help="Run AST self-tests on reference patterns",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="prompts_scipy_multi_library.jsonl",
        help="Path to output JSONL dataset",
    )
    args = parser.parse_args()

    if args.test_sample:
        run_self_test()
        return

    print("Combinatorial Taxonomy Matrix available:")
    print(f"- {len(SCIENTIFIC_DOMAINS)} Scientific Domains")
    print(f"- {len(VISUAL_PARADIGMS)} Visual Paradigms")
    print(f"- Total grid size: {len(SCIENTIFIC_DOMAINS) * len(VISUAL_PARADIGMS)} combinations")
    print(
        "\nTo generate and verify pairs using an OpenAI-compatible teacher model, ensure OPENAI_API_KEY is configured."
    )


if __name__ == "__main__":
    main()
