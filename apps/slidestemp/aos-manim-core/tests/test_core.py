import pytest
from aos_manim_core import (
    get_theme,
    set_theme,
    use_theme,
    ThemeConfig,
    SemanticPalette,
    MODERN_DARK,
    ACADEMIC_OXFORD,
    PluginManifest,
    Capability,
    ManifestBuilder,
    PluginRegistry,
    NumericalToleranceValidator,
    SymbolicEquivalenceValidator,
    CanvasBoundsValidator,
)
from manim import Circle, Square, LEFT, RIGHT, UP, DOWN


def test_theme_manager_switching():
    # Test default
    set_theme("modern_dark")
    t1 = get_theme()
    assert t1.name == "modern_dark"
    assert t1.primary is not None

    # Test switch
    set_theme("academic_oxford")
    t2 = get_theme()
    assert t2.name == "academic_oxford"

    # Test context manager
    with use_theme("nord") as t_nord:
        assert t_nord.name == "nord"
        assert get_theme().name == "nord"

    # Restores after context
    assert get_theme().name == "academic_oxford"


def test_manifest_schema_and_builder():
    builder = ManifestBuilder(
        plugin="aos-manim-test",
        domain="STEM",
        layer="Layer B",
        description="Test Plugin",
    )
    builder.add_capability(
        name="test_cap",
        category="algebra",
        description="Test capability",
        backends=["sympy"],
        mobjects=["Dot"],
        animations=["FadeIn"],
    )
    manifest = builder.build()
    assert manifest.plugin == "aos-manim-test"
    assert len(manifest.capabilities) == 1
    assert manifest.capabilities[0].name == "test_cap"

    json_str = manifest.to_json()
    assert "test_cap" in json_str


def test_validators():
    # Numerical tolerance
    num_val = NumericalToleranceValidator(atol=1e-3)
    res1 = num_val.validate(3.14159, expected=3.1416)
    assert res1.is_valid

    res2 = num_val.validate(3.14, expected=4.0)
    assert not res2.is_valid

    # Symbolic equivalence
    sym_val = SymbolicEquivalenceValidator()
    res3 = sym_val.validate("x**2 - y**2", expected="(x - y)*(x + y)")
    assert res3.is_valid

    res4 = sym_val.validate("x**2 + 1", expected="x**2 - 1")
    assert not res4.is_valid


def test_spatial_bounds_validator():
    bounds_val = CanvasBoundsValidator(margin=0.5, frame_width=14, frame_height=8)
    # Circle within bounds
    c = Circle(radius=1).shift(LEFT * 2)
    res1 = bounds_val.validate(c)
    assert res1.is_valid

    # Circle shifted way out of bounds
    c_out = Circle(radius=1).shift(RIGHT * 10)
    res2 = bounds_val.validate(c_out)
    assert len(res2.issues) > 0


def test_plugin_registry():
    registry = PluginRegistry()
    manifest = PluginManifest(
        plugin="aos-manim-test-reg",
        domain="STEM",
        layer="Layer B",
        description="Registry test",
        capabilities=[
            Capability(name="cap1", category="calculus", description="Calculus cap", tags=["derivative"])
        ]
    )
    registry.register(manifest)
    assert registry.get_plugin("aos-manim-test-reg") is not None

    caps = registry.find_capabilities(domain="STEM", category="calculus")
    assert len(caps) == 1
    assert caps[0].name == "cap1"


def test_narration_bookmarks_and_play_script():
    from aos_manim_core import (
        Cue,
        CueAction,
        CueResolver,
        NarrationScript,
        inject_bookmarks,
        parse_bookmark_marks,
        play_script,
    )
    from manim import Text

    cues = [
        Cue(mark="a", target_id="a", action=CueAction.REVEAL),
        Cue(mark="b", target_id="b", action=CueAction.REVEAL),
    ]
    text = inject_bookmarks("Hello there.", cues)
    assert parse_bookmark_marks(text) == ["a", "b"]

    ta = Text("A")
    tb = Text("B")
    ta.set_opacity(0)
    tb.set_opacity(0)

    class Dummy:
        def wait(self, t):
            pass

    script = NarrationScript(text=text, cues=cues)
    resolver = CueResolver(targets={"a": ta, "b": tb})
    play_script(Dummy(), script, resolver, gap=0.0)
    assert ta.get_fill_opacity() > 0.5
    assert tb.get_fill_opacity() > 0.5
