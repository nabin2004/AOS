"""Save optimized prompts to the reports directory."""
from pathlib import Path

import dspy


def export_prompt(prompt: str, name: str, output_dir: str = "reports") -> Path:
    """Save a raw prompt string to a text file."""
    path = Path(output_dir) / f"{name}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prompt, encoding="utf-8")
    return path


def export_program_instructions(
    program: dspy.Module, name: str, output_dir: str = "reports"
) -> dict[str, Path]:
    """Save the (possibly GEPA-optimized) instructions of every predictor in a
    compiled dspy.Module, one file per predictor.
    """
    written = {}
    for pred_name, predictor in program.named_predictors():
        suffix = pred_name.replace(".", "_")
        path = export_prompt(
            predictor.signature.instructions, f"{name}_{suffix}", output_dir
        )
        written[pred_name] = path
    return written
