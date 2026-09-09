"""Unit tests for the AOS Cinematic Mode & Director Engine."""

import os
from cinematic_director import (
    CINEMATIC_MANIMCE_CONTEXT,
    TEMPLATE_CINEMATIC_MASTERPIECE,
    get_mathematical_model,
    get_numerical_simulation_recipe,
    is_cinematic_mode,
)
from coder_prompt import build_coder_user_prompt
from tools.compile import validate_manim_code_static
from video_templates import get_template_for_duration


def test_is_cinematic_mode_detection():
    # Keyword detection
    assert is_cinematic_mode("Create a cinematic 3D Lorenz attractor")
    assert is_cinematic_mode("Make a glowing chaotic visualization in 3b1b style")
    assert is_cinematic_mode("Hollywood style movie on dynamical systems")
    assert not is_cinematic_mode("Solve 2 + 2 arithmetic")

    # Flag and environment detection
    assert is_cinematic_mode("simple topic", flag=True)
    os.environ["AOS_CINEMATIC_MODE"] = "1"
    try:
        assert is_cinematic_mode("simple topic")
    finally:
        del os.environ["AOS_CINEMATIC_MODE"]


def test_get_mathematical_model_lorenz():
    model = get_mathematical_model("Lorenz Attractor")
    assert model["name"] == "Lorenz Attractor"
    assert model["parameters"]["sigma"] == 10.0
    assert model["parameters"]["rho"] == 28.0
    assert model["canvas_scale"] == 0.12
    assert r"\sigma(y - x)" in model["latex_system"]


def test_get_numerical_simulation_recipe():
    recipe = get_numerical_simulation_recipe("Lorenz Attractor")
    assert "DATA ENGINEER" in recipe
    assert "np.sqrt" in recipe or "sigma" in recipe
    assert "set_color_by_gradient" in recipe
    assert "ACCENT_RED" in recipe  # Divergence trajectory


def test_video_template_cinematic_selection():
    tmpl = get_template_for_duration("medium", cinematic=True)
    assert tmpl == TEMPLATE_CINEMATIC_MASTERPIECE
    assert "(VoiceoverScene, ThreeDScene)" in tmpl
    assert "set_color_by_gradient" in tmpl
    assert "add_fixed_in_frame_mobjects" in tmpl
    assert "begin_ambient_camera_rotation" in tmpl


def test_build_coder_user_prompt_cinematic_injection():
    prompt = build_coder_user_prompt(
        topic="Lorenz Attractor",
        subject="Mathematics",
        output_dir="workspace/test",
        plan_payload={"topic": "Lorenz Attractor"},
        cinematic=True,
    )
    assert "CINEMATIC VISUALIZATION MODE ACTIVE" in prompt
    assert "MODERN MANIM COMMUNITY EDITION" in prompt
    assert "DATA ENGINEER NUMERICAL SIMULATION RECIPE" in prompt
    assert "CinematicAttractorScene" in prompt


def test_cinematic_masterpiece_template_validates_static():
    ok, err = validate_manim_code_static(TEMPLATE_CINEMATIC_MASTERPIECE, "CinematicAttractorScene")
    assert ok, f"Validation failed: {err}"
    assert err is None
