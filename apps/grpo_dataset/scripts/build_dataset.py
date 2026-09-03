from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProblemRow:
    problem_id: str
    prompt: str
    path: str


def load_problem_rows(data_root: Path) -> list[ProblemRow]:
    problems_dir = data_root / "problems"
    curated_path = data_root.parent / "scripts" / "curated_scenes.json"
    curated_map: dict[str, dict] = {}
    if curated_path.is_file():
        try:
            items = json.loads(curated_path.read_text(encoding="utf-8"))
            for item in items:
                curated_map[item["id"]] = item
        except Exception:
            pass

    rows: list[ProblemRow] = []
    for problem_dir in sorted(problems_dir.glob("*/")):
        if not problem_dir.is_dir():
            continue
        pid = problem_dir.name
        problem_json = problem_dir / "problem.json"
        prompt = ""
        
        if problem_json.is_file() and problem_json.stat().st_size > 0:
            try:
                payload = json.loads(problem_json.read_text(encoding="utf-8"))
                pid = payload.get("id", pid)
                prompt = payload.get("full_prompt", "")
            except Exception:
                pass

        if not prompt and pid in curated_map:
            c = curated_map[pid]
            prompt = f"Write a Manim visualization for {c.get('class_name')} covering {c.get('topic', 'mathematics')}."
        elif not prompt:
            prompt = f"Write a Manim visualization for {pid}."

        rows.append(
            ProblemRow(
                problem_id=pid,
                prompt=prompt,
                path=str(problem_json.as_posix()),
            )
        )
    return rows


def write_splits(rows: list[ProblemRow], splits_dir: Path, seed: int) -> None:
    rng = random.Random(seed)
    shuffled = rows[:]
    rng.shuffle(shuffled)

    n = len(shuffled)
    n_train = max(1, int(n * 0.8)) if n else 0
    n_val = int(n * 0.1)

    train = shuffled[:n_train]
    val = shuffled[n_train : n_train + n_val]
    test = shuffled[n_train + n_val :]

    for name, split_rows in (("train", train), ("val", val), ("test", test)):
        out = splits_dir / f"{name}.jsonl"
        with out.open("w", encoding="utf-8") as fh:
            for row in split_rows:
                item = {
                    "id": row.problem_id,
                    "prompt": row.prompt,
                    "problem_path": row.path,
                }
                fh.write(json.dumps(item, ensure_ascii=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic split files from data/problems.")
    parser.add_argument("--data-root", default="data", help="Path to dataset root")
    parser.add_argument("--seed", type=int, default=20260817, help="Split seed")
    args = parser.parse_args()

    data_root = Path(args.data_root)
    rows = load_problem_rows(data_root)
    write_splits(rows, data_root / "splits", args.seed)


if __name__ == "__main__":
    main()
