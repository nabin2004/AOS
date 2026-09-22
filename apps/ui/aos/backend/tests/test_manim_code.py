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
