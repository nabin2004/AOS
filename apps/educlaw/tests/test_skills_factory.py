from pathlib import Path

from pydantic_ai.models.test import TestModel

from educlaw.agent.factory import build_agent
from educlaw.skills import PACKAGE_SKILLS, skill_directories
from educlaw.testing import make_settings


def test_package_skills_exist() -> None:
    dirs = skill_directories()
    assert dirs
    names = {p.name for p in PACKAGE_SKILLS.iterdir() if p.is_dir()}
    assert {"manim-scene", "manim-quality", "manim-latex"} <= names
    assert (PACKAGE_SKILLS / "manim-scene" / "SKILL.md").is_file()


def test_build_agent_registers_tools() -> None:
    agent = build_agent(
        make_settings(),
        model=TestModel(call_tools=[], custom_output_text="ok"),
        wrap_kitaru=False,
    )
    names = set(agent._function_toolset.tools)  # noqa: SLF001
    for name in ("sandbox_read", "sandbox_write", "sandbox_bash", "manim_render", "lsp_diagnostics"):
        assert name in names


def test_cwd_skills_override_discovery(tmp_path: Path) -> None:
    skill = tmp_path / ".decode" / "skills" / "local" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: local\ndescription: x\n---\n# x\n", encoding="utf-8")
    found = skill_directories(tmp_path)
    assert any(str(tmp_path.resolve()) in item for item in found)
