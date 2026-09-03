from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_weight_sum(items: list[float], label: str) -> list[str]:
    total = sum(items)
    if not math.isclose(total, 1.0, rel_tol=1e-9, abs_tol=1e-9):
        return [f"{label} weights must sum to 1.0 but got {total}"]
    return []


def validate_problem_dir(problem_dir: Path) -> list[str]:
    errors: list[str] = []
    required = [
        "problem.json",
        "reference.py",
        "visual_events.json",
        "coverage.json",
        "version_notes.json",
        "ref_embeddings.npy",
    ]

    for req in required:
        if not (problem_dir / req).exists():
            errors.append(f"missing required file: {problem_dir / req}")

    if errors:
        return errors

    problem = _load_json(problem_dir / "problem.json")
    visual_events = _load_json(problem_dir / "visual_events.json")
    coverage = _load_json(problem_dir / "coverage.json")
    version_notes = _load_json(problem_dir / "version_notes.json")

    pid = problem.get("id")
    if pid != visual_events.get("problem_id"):
        errors.append(f"id mismatch visual_events problem_id for {problem_dir}")
    if pid != coverage.get("problem_id"):
        errors.append(f"id mismatch coverage problem_id for {problem_dir}")
    if pid != version_notes.get("problem_id"):
        errors.append(f"id mismatch version_notes problem_id for {problem_dir}")

    event_weights = [float(e.get("weight", 0.0)) for e in visual_events.get("events", [])]
    errors.extend(_check_weight_sum(event_weights, f"event ({pid})"))

    for event in visual_events.get("events", []):
        t0, t1 = event.get("expected_time_range", [0.0, 0.0])
        if t0 < 0 or t1 < t0:
            errors.append(f"invalid expected_time_range for {pid}:{event.get('event_id')}")
        if not event.get("keyword_bank"):
            errors.append(f"empty keyword_bank for {pid}:{event.get('event_id')}")
        if not str(event.get("clip_query", "")).strip():
            errors.append(f"empty clip_query for {pid}:{event.get('event_id')}")

    req_weights = [float(spec.get("weight", 0.0)) for spec in coverage.get("requirements", {}).values()]
    errors.extend(_check_weight_sum(req_weights, f"coverage ({pid})"))

    return errors


def validate_splits(data_root: Path, known_ids: set[str]) -> list[str]:
    errors: list[str] = []
    split_ids: dict[str, set[str]] = {}

    for split in ("train", "val", "test"):
        path = data_root / "splits" / f"{split}.jsonl"
        if not path.exists():
            errors.append(f"missing split file: {path}")
            continue

        split_ids[split] = set()
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            pid = item["id"]
            split_ids[split].add(pid)
            if pid not in known_ids:
                errors.append(f"split id {pid} not found in problems")
            if not Path(item["problem_path"]).exists():
                errors.append(f"problem_path does not exist: {item['problem_path']}")

    if all(name in split_ids for name in ("train", "val", "test")):
        if split_ids["train"] & split_ids["val"]:
            errors.append("train and val overlap")
        if split_ids["train"] & split_ids["test"]:
            errors.append("train and test overlap")
        if split_ids["val"] & split_ids["test"]:
            errors.append("val and test overlap")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate ManiBench GRPO dataset layout.")
    parser.add_argument("--data-root", default="data", help="Path to data root")
    args = parser.parse_args()

    data_root = Path(args.data_root)
    problems = sorted((data_root / "problems").glob("*/"))
    errors: list[str] = []
    known_ids: set[str] = set()

    for problem_dir in problems:
        p_errors = validate_problem_dir(problem_dir)
        errors.extend(p_errors)
        if (problem_dir / "problem.json").exists():
            payload = _load_json(problem_dir / "problem.json")
            known_ids.add(payload["id"])

    errors.extend(validate_splits(data_root, known_ids))

    if errors:
        print("VALIDATION FAILED")
        for item in errors:
            print(f"- {item}")
        raise SystemExit(1)

    print("VALIDATION PASSED")


if __name__ == "__main__":
    main()
