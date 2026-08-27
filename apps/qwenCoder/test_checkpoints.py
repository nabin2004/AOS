from __future__ import annotations

import json
from pathlib import Path

import pytest

from checkpoints import (
    checkpoint_step,
    is_trainer_checkpoint,
    last_checkpoint_in,
    materialize_checkpoint,
    resolve_resume_checkpoint,
)


def _write_ckpt(root: Path, step: int) -> Path:
    path = root / f"checkpoint-{step}"
    path.mkdir(parents=True)
    (path / "trainer_state.json").write_text(
        json.dumps({"global_step": step}), encoding="utf-8"
    )
    (path / "adapter_config.json").write_text("{}", encoding="utf-8")
    return path


def test_is_trainer_checkpoint(tmp_path: Path) -> None:
    ckpt = _write_ckpt(tmp_path, 200)
    assert is_trainer_checkpoint(ckpt)
    assert checkpoint_step(ckpt) == 200
    assert not is_trainer_checkpoint(tmp_path)


def test_last_checkpoint_in_picks_highest_step(tmp_path: Path) -> None:
    _write_ckpt(tmp_path, 200)
    later = _write_ckpt(tmp_path, 400)
    assert last_checkpoint_in(tmp_path) == later
    assert last_checkpoint_in(later) == later


def test_materialize_copies_readonly_source(tmp_path: Path) -> None:
    src_root = tmp_path / "input"
    src = _write_ckpt(src_root, 200)
    output = tmp_path / "working"
    dest = materialize_checkpoint(src, output)
    assert dest == output / "checkpoint-200"
    assert (dest / "trainer_state.json").is_file()
    assert dest != src


def test_resolve_auto_resumes_local(tmp_path: Path) -> None:
    ckpt = _write_ckpt(tmp_path, 200)
    found = resolve_resume_checkpoint(
        output_dir=tmp_path,
        resume="auto",
        resume_from=None,
        hub_checkpoint_id=None,
        sync_trainer_checkpoint=False,
    )
    assert found == ckpt


def test_resolve_never_ignores_checkpoint(tmp_path: Path) -> None:
    _write_ckpt(tmp_path, 200)
    found = resolve_resume_checkpoint(
        output_dir=tmp_path,
        resume="never",
        resume_from=None,
        hub_checkpoint_id=None,
        sync_trainer_checkpoint=False,
    )
    assert found is None


def test_resolve_always_requires_checkpoint(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        resolve_resume_checkpoint(
            output_dir=tmp_path,
            resume="always",
            resume_from=None,
            hub_checkpoint_id=None,
            sync_trainer_checkpoint=False,
        )


def test_resolve_from_external_dir(tmp_path: Path) -> None:
    incoming = tmp_path / "kaggle-input"
    _write_ckpt(incoming, 400)
    output = tmp_path / "working"
    found = resolve_resume_checkpoint(
        output_dir=output,
        resume="auto",
        resume_from=incoming,
        hub_checkpoint_id=None,
        sync_trainer_checkpoint=False,
    )
    assert found == output / "checkpoint-400"
    assert checkpoint_step(found) == 400


def test_kaggle_preset_does_not_force_5k() -> None:
    pytest.importorskip("peft")
    pytest.importorskip("trl")
    from config import TrainingConfig, apply_kaggle_preset

    cfg = apply_kaggle_preset(TrainingConfig())
    assert cfg.max_samples is None
    assert cfg.save_strategy == "steps"
    assert cfg.save_steps == 200
    assert cfg.lora_r == 16
    assert cfg.sync_trainer_checkpoint is True
