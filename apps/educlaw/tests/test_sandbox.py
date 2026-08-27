from pathlib import Path

import pytest

from educlaw.sandbox.docker import DockerSandbox, PathJailError, build_docker_run_argv


def test_docker_run_argv_mount_and_image(tmp_path: Path) -> None:
    argv = build_docker_run_argv(
        cwd=tmp_path,
        image="manimcommunity/manim:stable",
        inner=["manim", "-qm", "scene.py", "Intro"],
        docker_user="1000:1000",
    )
    assert argv[:3] == ["docker", "run", "--rm"]
    assert f"{tmp_path.resolve()}:/manim" in argv
    assert "--user" in argv
    assert argv[argv.index("--user") + 1] == "1000:1000"
    assert "manimcommunity/manim:stable" in argv
    assert "-qm" in argv
    assert "Intro" in argv


def test_path_jail_blocks_escape(tmp_path: Path) -> None:
    box = DockerSandbox(tmp_path)
    with pytest.raises(PathJailError):
        box.jail("../outside.py")
    inside = box.jail("scene.py")
    assert inside == (tmp_path / "scene.py").resolve()


def test_manim_argv_uses_relative_file(tmp_path: Path) -> None:
    box = DockerSandbox(tmp_path, quality="m")
    (tmp_path / "scene.py").write_text("x = 1\n", encoding="utf-8")
    argv = box.manim_argv("scene.py", "Intro", "m")
    assert "manim" in argv
    assert "-qm" in argv
    assert "scene.py" in argv
    assert "Intro" in argv


def test_bash_never_uses_host_shell(tmp_path: Path) -> None:
    argv = DockerSandbox(tmp_path).bash_argv("ls")
    assert argv[0] == "docker"
    assert argv[-3:] == ["bash", "-lc", "ls"]
