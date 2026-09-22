from app.services.manim_code import preflight_manim_code


def test_preflight_reports_syntax_error_before_render() -> None:
    result = preflight_manim_code("def construct(self)\n    pass")

    assert not result.valid
    assert result.errors[0]["type"] == "SyntaxError"
    assert result.errors[0]["line"] == 1


def test_preflight_reports_manime_name_typo() -> None:
    result = preflight_manim_code(
        "from manim import *\n\nclass DemoScene(Scene):\n    def construct(self):\n        self.play(Wrtie(Text('x')))"
    )

    assert not result.valid
    assert any(error["name"] == "Wrtie" for error in result.errors)


def test_preflight_allows_user_variables_and_manime_wildcard() -> None:
    result = preflight_manim_code(
        "from manim import *\n\nclass DemoScene(Scene):\n    def construct(self):\n        label = Text('x')\n        self.play(Write(label))"
    )

    assert result.valid


def test_preflight_collects_multiple_maninm_findings_in_one_pass() -> None:
    result = preflight_manim_code(
        "from manim import *\n"
        "class DemoScene(Scene):\n"
        "    def construct(self):\n"
        "        q = MathTex(\"e \\\\approx 2.718\")\n"
        "        q.set_text(\"bad\")\n"
        "        self.play(Write(q[5]))\n"
        "        self.play(Write(Text(\"x\").to_edge(BOTTOM)))\n"
    )

    kinds = {error["type"] for error in result.errors}
    assert {"NonRawTexString", "UnsupportedManimMethod", "BrittleMobjectIndex", "UnsupportedManimName"} <= kinds


def test_repair_normalizes_raw_tex_and_bottom() -> None:
    from app.services.manim_code import repair_manim_code

    source = 'q = MathTex("e \\approx 2.718")\nlabel.to_edge(BOTTOM)\n'
    repaired = repair_manim_code(source)

    assert 'MathTex(r"e \\approx 2.718")' in repaired.code
    assert "to_edge(DOWN)" in repaired.code


def test_preflight_reports_mathtex_index_against_its_definition() -> None:
    result = preflight_manim_code(
        "from manim import *\n"
        "class DemoScene(Scene):\n"
        "    def construct(self):\n"
        "        eq = MathTex(r\"x = y\")\n"
        "        self.play(ReplacementTransform(eq[1], Text(\"?\")))\n"
    )

    finding = next(error for error in result.errors if error["type"] == "MobjectIndexOutOfRange")
    assert result.valid is False
    assert finding["name"] == "eq"
    assert finding["index"] == 1
    assert finding["definition_line"] == 4
    assert "MathTex" in finding["definition"]
