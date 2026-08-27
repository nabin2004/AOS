"""Trainer checkpoint resume + Hub last-trainer-checkpoint sync."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from hub_upload import TRAINER_CHECKPOINT_DIR, optional_token, push_model_folder

TRAINER_STATE = "trainer_state.json"


def is_trainer_checkpoint(path: Path) -> bool:
    return path.is_dir() and (path / TRAINER_STATE).is_file()


def last_checkpoint_in(directory: Path | None) -> Path | None:
    if directory is None or not directory.is_dir():
        return None
    if is_trainer_checkpoint(directory):
        return directory
    numbered = [
        path
        for path in directory.iterdir()
        if path.is_dir()
        and path.name.startswith("checkpoint-")
        and is_trainer_checkpoint(path)
    ]
    if not numbered:
        return None
    return max(numbered, key=lambda path: checkpoint_step(path) or -1)


def checkpoint_step(path: Path) -> int | None:
    state_file = path / TRAINER_STATE
    if not state_file.is_file():
        return None
    try:
        payload = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    step = payload.get("global_step")
    return int(step) if step is not None else None


def materialize_checkpoint(src: Path, output_dir: Path) -> Path:
    """Copy a (possibly read-only) checkpoint into output_dir/checkpoint-{step}."""
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        src_resolved = src.resolve()
        out_resolved = output_dir.resolve()
        if src_resolved.is_relative_to(out_resolved):
            return src
    except (OSError, ValueError):
        pass
    step = checkpoint_step(src) or 0
    dest = output_dir / f"checkpoint-{step}"
    if dest.exists() and dest.resolve() == src.resolve():
        return dest
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return dest


def resolve_resume_checkpoint(
    *,
    output_dir: Path,
    resume: str,
    resume_from: Path | None,
    hub_checkpoint_id: str | None,
    sync_trainer_checkpoint: bool,
) -> Path | None:
    """Return a local Trainer checkpoint to resume, or None for a fresh run."""
    local = last_checkpoint_in(resume_from) or last_checkpoint_in(output_dir)
    if resume == "never":
        if local is not None:
            print(
                f"WARNING: --no-resume ignores Trainer checkpoint {local}",
                flush=True,
            )
        return None

    if local is None and sync_trainer_checkpoint:
        local = pull_trainer_checkpoint(hub_checkpoint_id, output_dir)

    if local is None:
        if resume == "always":
            raise FileNotFoundError(
                "--resume was set but no checkpoint-* (or Hub "
                f"{TRAINER_CHECKPOINT_DIR}) was found."
            )
        print("No Trainer checkpoint found; starting from step 0", flush=True)
        return None

    ready = materialize_checkpoint(local, output_dir)
    step = checkpoint_step(ready)
    print(
        f"Resuming Trainer checkpoint {ready}"
        + (f" (global_step={step})" if step is not None else ""),
        flush=True,
    )
    return ready


def push_trainer_checkpoint(checkpoint_dir: Path, repo_id: str | None) -> None:
    token = optional_token()
    if not token or not repo_id:
        return
    if not is_trainer_checkpoint(checkpoint_dir):
        return
    push_model_folder(
        checkpoint_dir,
        repo_id,
        token,
        path_in_repo=TRAINER_CHECKPOINT_DIR,
        ignore_patterns=["README.md", ".git", "*.tmp"],
    )


def pull_trainer_checkpoint(repo_id: str | None, output_dir: Path) -> Path | None:
    token = optional_token()
    if not token or not repo_id:
        return None
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        return None

    tmp = Path(tempfile.mkdtemp(prefix="aos-trainer-ckpt-"))
    try:
        snapshot_download(
            repo_id=repo_id,
            repo_type="model",
            token=token,
            allow_patterns=[f"{TRAINER_CHECKPOINT_DIR}/**"],
            local_dir=str(tmp),
        )
    except Exception as exc:
        print(f"No Hub trainer checkpoint at {repo_id}: {exc}", flush=True)
        shutil.rmtree(tmp, ignore_errors=True)
        return None

    src = tmp / TRAINER_CHECKPOINT_DIR
    if not is_trainer_checkpoint(src):
        shutil.rmtree(tmp, ignore_errors=True)
        return None
    dest = materialize_checkpoint(src, output_dir)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"Downloaded Hub trainer checkpoint -> {dest}", flush=True)
    return dest
