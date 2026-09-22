from repair import deterministic_repair, documentation_context


def test_repairs_mathtex_center_lookup_and_validates_python() -> None:
    source = 'arrow_b = Arrow(eq1.get_part_by_tex("b").get_center(), eq1.get_center())'

    result = deterministic_repair(source)

    assert result.syntax_valid
    assert result.source == 'arrow_b = Arrow(eq1.get_center(), eq1.get_center())'
    assert result.changes


def test_invalid_source_is_not_reported_as_repaired() -> None:
    result = deterministic_repair("def construct(:\n    pass")

    assert not result.syntax_valid
    assert result.syntax_error


def test_repairs_mathtex_shift_endpoint() -> None:
    result = deterministic_repair(
        'arrow = Arrow(start=eq1.get_center(), end=eq1.get_part_by_tex("b").shift(DOWN))'
    )

    assert result.syntax_valid
    assert "eq1.get_part_by_tex" not in result.source
    assert "eq1.get_center() + (DOWN)" in result.source


def test_repairs_scene_camera_frame_mismatch() -> None:
    result = deterministic_repair("class DemoScene(Scene):\n    def construct(self):\n        self.camera.frame.move_to(DOWN * 1.5)\n")

    assert result.syntax_valid
    assert "self.camera.frame" not in result.source
    assert "MovingCameraScene" in result.source


def test_normalizes_multi_argument_tex_lookup() -> None:
    result = deterministic_repair('exp_parts = exp_eq.get_parts_by_tex("2", "3", "8")')

    assert result.syntax_valid
    assert "get_parts_by_tex" not in result.source
    assert "get_part_by_tex(token)" in result.source


def test_removes_unsupported_tex_compiler_override() -> None:
    result = deterministic_repair('config["tex_compiler"] = "pdflatex"')

    assert result.syntax_valid
    assert "tex_compiler" not in result.source
    assert "managed by Manim" in result.source


def test_documentation_context_keeps_retrieval_separate() -> None:
    class Hit:
        score = 0.91
        chunk = {"name": "MathTex", "module": "manim.mobject.text", "text": "MathTex docs"}

    calls = []

    def search(query: str, limit: int, chunk_type: str):
        calls.append((query, limit, chunk_type))
        return [Hit()]

    docs = documentation_context(error="NoneType get_center", source="scene", search=search, top_k=3)

    assert docs[0]["name"] == "MathTex"
    assert calls[0][1:] == (3, "entry")
