"""Shared Weights & Biases setup for AOS SFT and GRPO training."""

from __future__ import annotations

import os
import sys
from pathlib import Path

TRAINING_ROOT = Path(__file__).resolve().parent
DEFAULT_DOTENV = TRAINING_ROOT / ".env"

DEFAULT_PROJECT_SFT = "aos-sft"
DEFAULT_PROJECT_GRPO = "aos-grpo"


def load_training_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE pairs from apps/training/.env into os.environ."""
    dotenv_path = path or DEFAULT_DOTENV
    if not dotenv_path.is_file():
        return

    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def wandb_api_key() -> str | None:
    raw = os.environ.get("WANDB_API_KEY", "").strip()
    return raw or None


def resolve_report_to(requested: str) -> str:
    """Use wandb only when requested and WANDB_API_KEY is available."""
    if requested == "none":
        return "none"
    if requested != "wandb":
        return requested
    if wandb_api_key():
        return "wandb"
    print(
        "WARNING: report_to=wandb but WANDB_API_KEY is not set; disabling experiment tracking.",
        file=sys.stderr,
    )
    return "none"


def configure_wandb(
    *,
    project: str,
    run_name: str,
    job_type: str,
    project_env_key: str | None = None,
    group: str | None = None,
    tags: tuple[str, ...] | list[str] | None = None,
    config: dict[str, object] | None = None,
) -> str:
    """Apply W&B env defaults and login. Returns effective report_to backend."""
    load_training_dotenv()

    if project_env_key:
        project = os.environ.get(project_env_key, project).strip() or project

    if os.environ.get("WANDB_PROJECT", "").strip():
        project = os.environ["WANDB_PROJECT"].strip()
    else:
        os.environ["WANDB_PROJECT"] = project

    if run_name and not os.environ.get("WANDB_RUN_NAME", "").strip():
        os.environ["WANDB_RUN_NAME"] = run_name

    if not os.environ.get("WANDB_JOB_TYPE", "").strip():
        os.environ["WANDB_JOB_TYPE"] = job_type

    if group and not os.environ.get("WANDB_RUN_GROUP", "").strip():
        os.environ["WANDB_RUN_GROUP"] = group

    if tags and not os.environ.get("WANDB_TAGS", "").strip():
        os.environ["WANDB_TAGS"] = ",".join(tags)

    key = wandb_api_key()
    if not key:
        return "none"

    import wandb

    wandb.login(key=key)

    if config is not None and wandb.run is None:
        wandb.init(
            project=project,
            name=os.environ.get("WANDB_RUN_NAME") or run_name or None,
            group=group,
            tags=list(tags) if tags else None,
            config=config,
            job_type=job_type,
        )

    return "wandb"


def collect_wandb_env_vars(
    *,
    project: str,
    run_name: str | None = None,
    project_env_key: str | None = None,
    group: str | None = None,
    tags: tuple[str, ...] | list[str] | None = None,
) -> dict[str, str]:
    """Build env dict for Vertex container submission."""
    load_training_dotenv()

    if project_env_key:
        project = os.environ.get(project_env_key, project).strip() or project

    env_vars: dict[str, str] = {}
    key = wandb_api_key()
    if not key:
        return env_vars

    env_vars["WANDB_API_KEY"] = key
    env_vars["WANDB_PROJECT"] = (
        os.environ.get("WANDB_PROJECT", project).strip() or project
    )

    entity = os.environ.get("WANDB_ENTITY", "").strip()
    if entity:
        env_vars["WANDB_ENTITY"] = entity

    effective_run_name = run_name or os.environ.get("WANDB_RUN_NAME", "").strip()
    if effective_run_name:
        env_vars["WANDB_RUN_NAME"] = effective_run_name

    effective_group = group or os.environ.get("WANDB_RUN_GROUP", "").strip()
    if effective_group:
        env_vars["WANDB_RUN_GROUP"] = effective_group

    if tags:
        env_vars["WANDB_TAGS"] = ",".join(tags)
    elif os.environ.get("WANDB_TAGS", "").strip():
        env_vars["WANDB_TAGS"] = os.environ["WANDB_TAGS"].strip()

    return env_vars
