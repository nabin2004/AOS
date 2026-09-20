"""Execution runner for CodeAgent steps, prompt assembly, and artifact recording."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import RunUsage, UsageLimits

from coder_agent import SFT_BATCH_ADDENDUM, coder_agent
from coder_prompt import build_coder_user_prompt, plan_to_payload
from coder_run import CoderRunResult, arrange_coder_artifacts, new_coder_run_dir
from ir.manim_ir import Lecture, Subject
from llm_config import is_ollama, model_for
from llm_retry import execute_with_llm_retry
from observability import sft_batch_enabled
from openai_compatible import format_custom_endpoint_error
from teaching_script import TeachingScript, teaching_script_to_payload
from tools.coder_workspace import load_manifest, save_manifest


def subject_str(subject: str | Subject) -> str:
    """Normalize subject enum or string representation."""
    if isinstance(subject, Subject):
        return subject.value
    return str(subject)


async def run_coder_step(
    topic: str,
    subject: str | Subject,
    plan: Lecture | str | dict,
    *,
    teaching_script: TeachingScript | dict | None = None,
    usage: RunUsage | None = None,
    user_prompt: str | None = None,
    prompt_index: int | None = None,
    existing_run_dir: str | None = None,
    feedback: str | None = None,
    length: str = "medium",
    cinematic: bool = False,
    animation_mode: str = "keyframe",
) -> CoderRunResult:
    """Execute Manim code synthesis and compilation for a given lecture topic."""
    run_dir = Path(existing_run_dir) if existing_run_dir else new_coder_run_dir(topic)

    payload = plan_to_payload(plan)
    script_payload = teaching_script_to_payload(teaching_script)
    if script_payload:
        payload["teaching_script"] = script_payload
        try:
            (run_dir / "teaching_script.json").write_text(
                json.dumps(script_payload, indent=2), encoding="utf-8"
            )
            manifest = load_manifest(run_dir)
            manifest["teaching_script"] = script_payload
            manifest["topic"] = topic
            save_manifest(run_dir, manifest)
        except Exception:
            pass

    local_coder = is_ollama(model_for("coder"))
    prompt = build_coder_user_prompt(
        topic=topic,
        subject=subject_str(subject),
        output_dir=run_dir,
        plan_payload=payload,
        compact=local_coder,
        include_codemode_hint=local_coder,
        length=length,
        cinematic=cinematic,
        mode=animation_mode,
    )

    if feedback and existing_run_dir:
        code_file = Path(existing_run_dir) / "lecture.py"
        if not code_file.exists():
            code_file = Path(existing_run_dir) / "scene.py"
        current_code = (
            code_file.read_text(encoding="utf-8") if code_file.exists() else ""
        )
        prompt += (
            f"\n\nExisting Code:\n```python\n{current_code}\n```\n\n"
            f"User Feedback for Revision:\n{feedback}\nRevise the code to address this feedback."
        )

    if sft_batch_enabled():
        prompt += SFT_BATCH_ADDENDUM

    messages = None
    run_usage = usage
    summary = ""
    stopped_reason = "completed"
    request_limit = int(os.getenv("AOS_CODER_MAX_REQUESTS", "6"))
    coder_limits = UsageLimits(request_limit=request_limit)

    try:
        async def _call_coder():
            return await coder_agent.run(prompt, usage=usage, usage_limits=coder_limits)

        result = await execute_with_llm_retry(_call_coder, operation_name="Coder Agent")
        messages = result.all_messages()
        run_usage = result.usage
        summary = str(result.output) if result.output is not None else ""
    except UsageLimitExceeded as exc:
        stopped_reason = f"usage_limit: {exc}"
        summary = stopped_reason
    except Exception as exc:
        stopped_reason = format_custom_endpoint_error(exc)
        summary = stopped_reason

    manifest = load_manifest(run_dir)
    if (manifest.get("last_compile") or {}).get("ok"):
        stopped_reason = "completed"

    return arrange_coder_artifacts(
        run_dir,
        messages=messages,
        usage=run_usage,
        summary=summary,
        stopped_reason=stopped_reason,
        request_limit=request_limit,
        tool_calls_limit=None,
        user_prompt=user_prompt or topic,
        prompt_index=prompt_index,
    )
