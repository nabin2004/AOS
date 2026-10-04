from app.services.manim_code import repair_manim_code


def test_repairs_unsafe_mathtex_center_lookup() -> None:
    source = 'arrow_b = Arrow(eq1.get_part_by_tex("b").get_center(), eq1.get_center())'

    repaired = repair_manim_code(source)

    assert repaired.code == 'arrow_b = Arrow(eq1.get_center(), eq1.get_center())'
    assert repaired.changes


def test_preserves_non_chained_mathtex_lookup() -> None:
    source = 'part = eq1.get_part_by_tex("b")'

    repaired = repair_manim_code(source)

    assert repaired.code == source
    assert repaired.changes == ()


def test_repairs_tex_math_expression_to_mathtex() -> None:
    source = 'eq = Tex(r"2 \\times 3")'
    repaired = repair_manim_code(source)
    assert repaired.code == 'eq = MathTex(r"2 \\times 3")'
    assert any("Converted Tex to MathTex" in c for c in repaired.changes)


def test_repairs_tex_prose_with_math_command() -> None:
    source = 'label = Tex(r"Area equals length \\times width")'
    repaired = repair_manim_code(source)
    assert repaired.code == 'label = Tex(r"Area equals length $\\times$ width")'
    assert any("Wrapped math commands" in c for c in repaired.changes)


def test_preflight_detects_tex_math_mode_mismatch() -> None:
    from app.services.manim_code import preflight_manim_code
    source = '''
class MyScene(Scene):
    def construct(self):
        t = Tex(r"2 \\times 3")
        self.add(t)
'''
    res = preflight_manim_code(source)
    assert any(err.get("type") == "TexMathModeMismatch" for err in res.errors)

