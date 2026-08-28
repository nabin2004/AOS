"""Docker-backed Manim sandbox. Host tools never run bash on the machine."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

DEFAULT_IMAGE = "manimcommunity/manim:stable"
CONTAINER_ROOT = "/manim"


class PathJailError(ValueError):
    """Path escaped the workspace root."""


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def build_docker_run_argv(
    *,
    cwd: Path,
    image: str,
    inner: list[str],
    docker_user: str | None = None,
    workdir: str = CONTAINER_ROOT,
) -> list[str]:
    argv = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{cwd.resolve()}:{CONTAINER_ROOT}",
        "-w",
        workdir,
    ]
    if docker_user:
        argv.extend(["--user", docker_user])
    argv.append(image)
    argv.extend(inner)
    return argv


class DockerSandbox:
    def __init__(
        self,
        cwd: Path,
        *,
        image: str = DEFAULT_IMAGE,
        docker_user: str | None = None,
        quality: str = "m",
    ) -> None:
        self.cwd = cwd.resolve()
        self.image = image
        self.docker_user = docker_user
        self.quality = quality if quality in {"l", "m", "h", "k"} else "m"

    def jail(self, raw: str) -> Path:
        text = (raw or "").strip()
        if not text or text.startswith("~"):
            raise PathJailError("path must be relative to the workspace")
        path = Path(text)
        resolved = path.resolve() if path.is_absolute() else (self.cwd / path).resolve()
        if not _is_under(resolved, self.cwd):
            raise PathJailError(f"path escapes workspace: {resolved}")
        return resolved

    def container_path(self, host_path: Path) -> str:
        rel = host_path.resolve().relative_to(self.cwd)
        posix = rel.as_posix()
        if posix == ".":
            return CONTAINER_ROOT
        return f"{CONTAINER_ROOT}/{posix}"

    def bash_argv(self, command: str) -> list[str]:
        return build_docker_run_argv(
            cwd=self.cwd,
            image=self.image,
            inner=["bash", "-lc", command],
            docker_user=self.docker_user,
        )

    def manim_argv(self, scene_file: str, scene_name: str, quality: str | None = None) -> list[str]:
        q = quality or self.quality
        if q not in {"l", "m", "h", "k"}:
            q = "m"
        host = self.jail(scene_file)
        inner_file = self.container_path(host)
        # manim inside the image expects a path relative to /manim or absolute
        rel = host.relative_to(self.cwd).as_posix()
        return build_docker_run_argv(
            cwd=self.cwd,
            image=self.image,
            inner=["manim", f"-q{q}", rel if rel != "." else inner_file, scene_name],
            docker_user=self.docker_user,
        )

    def docker_available(self) -> bool:
        return shutil.which("docker") is not None

    def run(self, argv: list[str], timeout: int = 180) -> subprocess.CompletedProcess[str]:
        if not self.docker_available():
            raise FileNotFoundError(
                "Docker is not installed or not on PATH. "
                "EduClaw sandbox commands run inside manimcommunity/manim."
            )
        return subprocess.run(
            argv,
            cwd=self.cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            encoding="utf-8",
            errors="replace",
            # timeout=timeout,
            # check=False,

        )

    def format_result(self, proc: subprocess.CompletedProcess[str], *, limit: int = 4000) -> str:
        chunks = [f"exit={proc.returncode}"]
        if proc.stdout.strip():
            chunks.append(proc.stdout.strip())
        if proc.stderr.strip():
            chunks.append(proc.stderr.strip())
        text = "\n".join(chunks)
        if len(text) > limit:
            return text[:limit] + "\n…[truncated]"
        return text
