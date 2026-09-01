"""
ManiBench Evaluation — Structured Logging
===========================================
JSON-lines logger for reproducible experiment tracking.
Each log entry includes timestamp, run metadata, and metric values.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evaluation.config import LOGS_DIR


def _make_run_id() -> str:
    """Generate a unique run identifier from current UTC timestamp."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


class StructuredLogger:
    """
    Dual-output logger:
      1. Human-readable console output (INFO level)
      2. Machine-readable JSONL file (all levels) for paper analysis
    """

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or _make_run_id()
        self.log_path = LOGS_DIR / f"run_{self.run_id}.jsonl"
        self.summary_path = LOGS_DIR / f"run_{self.run_id}_summary.json"

        # Python logger for console
        self._logger = logging.getLogger(f"manibench.{self.run_id}")
        self._logger.setLevel(logging.DEBUG)
        self._logger.propagate = False

        if not self._logger.handlers:
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(logging.INFO)
            fmt = logging.Formatter(
                "[%(asctime)s] %(levelname)-8s %(message)s",
                datefmt="%H:%M:%S",
            )
            ch.setFormatter(fmt)
            self._logger.addHandler(ch)

        # JSONL file handle
        self._file = open(self.log_path, "a", encoding="utf-8")
        self.info(f"Logging to {self.log_path}")

    # ── Core methods ───────────────────────────────────────────────────

    def _write(self, level: str, event: str, data: dict[str, Any] | None = None):
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "level": level,
            "event": event,
        }
        if data:
            record["data"] = data
        self._file.write(json.dumps(record, default=str) + "\n")
        self._file.flush()

    def info(self, msg: str, **data):
        self._logger.info(msg)
        self._write("INFO", msg, data if data else None)

    def debug(self, msg: str, **data):
        self._logger.debug(msg)
        self._write("DEBUG", msg, data if data else None)

    def warning(self, msg: str, **data):
        self._logger.warning(msg)
        self._write("WARNING", msg, data if data else None)

    def error(self, msg: str, **data):
        self._logger.error(msg)
        self._write("ERROR", msg, data if data else None)

    # ── Structured events ──────────────────────────────────────────────

    def log_generation(self, model: str, problem_id: str, trial: int,
                       prompt_strategy: str, prompt_tokens: int,
                       completion_tokens: int, latency_ms: float,
                       code: str, raw_response: str | None = None):
        """Log a single code generation event."""
        self._write("GENERATION", f"{model}/{problem_id}/t{trial}", {
            "model": model,
            "problem_id": problem_id,
            "trial": trial,
            "prompt_strategy": prompt_strategy,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": round(latency_ms, 1),
            "code_length": len(code),
            "code_hash": hex(hash(code)),
        })

    def log_metrics(self, model: str, problem_id: str, trial: int,
                    metrics: dict[str, Any]):
        """Log computed metrics for one (model, problem, trial)."""
        self.info(
            f"  → {model}/{problem_id}/t{trial}: "
            f"exec={metrics.get('executability', '?')} "
            f"vcr={metrics.get('version_conflict_rate', '?'):.0%} "
            f"align={metrics.get('alignment_score', '?'):.3f} "
            f"cover={metrics.get('coverage_score', '?'):.3f}"
        )
        self._write("METRICS", f"{model}/{problem_id}/t{trial}", {
            "model": model,
            "problem_id": problem_id,
            "trial": trial,
            **metrics,
        })

    def log_render(self, model: str, problem_id: str, trial: int,
                   exec_detail: dict[str, Any]):
        """Log Manim subprocess output for one (model, problem, trial)."""
        attempted = exec_detail.get("render_attempted", False)
        duration = exec_detail.get("render_duration_s", 0.0)
        rc = exec_detail.get("returncode")
        error = exec_detail.get("error_type") or "-"
        self.info(
            f"    render={'attempted' if attempted else 'skipped'} "
            f"duration={duration}s rc={rc} error={error}"
        )
        self._write("RENDER", f"{model}/{problem_id}/t{trial}", {
            "model": model,
            "problem_id": problem_id,
            "trial": trial,
            "render_attempted": attempted,
            "render_success": exec_detail.get("render_success", False),
            "render_duration_s": duration,
            "returncode": rc,
            "error_type": exec_detail.get("error_type"),
            "error_message": exec_detail.get("error_message"),
            "command": exec_detail.get("command", []),
            "stdout": exec_detail.get("stdout", ""),
            "stderr": exec_detail.get("stderr", ""),
        })

    def log_run_config(self, config: dict[str, Any]):
        """Log the full evaluation configuration at run start."""
        self._write("CONFIG", "run_config", config)

    def save_summary(self, summary: dict[str, Any]):
        """Write final summary JSON for paper tables."""
        with open(self.summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, default=str)
        self.info(f"Summary saved to {self.summary_path}")

    # ── Cleanup ────────────────────────────────────────────────────────

    def close(self):
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
