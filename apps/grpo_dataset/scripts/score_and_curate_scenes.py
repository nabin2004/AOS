"""Score 3b1b/videos scenes (2022–2026) and lock a 200-row curated list."""
from __future__ import annotations

import ast
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIDEOS = ROOT / "raw" / "videos"
OUT_PATH = Path(__file__).resolve().parent / "curated_scenes.json"

YEARS = (2022, 2023, 2024, 2025, 2026)
YEAR_QUOTAS = {2026: 40, 2025: 50, 2024: 45, 2023: 40, 2022: 25}

TOPIC_CAPS: dict[tuple[int, str], int] = {
    (2026, "cross_entropy"): 10,
    (2026, "print_gallery"): 8,
    (2026, "spheres_talk"): 8,
    (2026, "monthly_mindbenders"): 6,
    (2025, "laplace"): 12,
    (2025, "grover"): 10,
    (2025, "cosmic_distance"): 10,
    (2025, "guest_videos"): 4,
    (2025, "zeta"): 2,
    (2024, "transformers"): 12,
    (2024, "holograms"): 8,
    (2024, "inscribed_rect"): 8,
    (2024, "puzzles"): 8,
    (2024, "antp"): 5,
    (2024, "manim_demo"): 1,
    (2023, "optics_puzzles"): 8,
    (2023, "moser_reboot"): 6,
    (2022, "quintic"): 6,
    (2022, "borwein"): 5,
    (2022, "galois"): 4,
    (2022, "piano"): 4,
}

ENGINE_SCENE_BASES = {
    "InteractiveScene",
    "Scene",
    "ThreeDScene",
    "SpecialThreeDScene",
    "MovingCameraScene",
}
EXCLUDE_BASES = {
    "TeacherStudentsScene",
    "PiCreatureScene",
    "PatreonEndScreen",
    "EndScreen",
}
EXCLUDE_FILE_NAMES = {
    "tree_editor.py",
    "wav_to_midi.py",
    "simulations.py",
    "old_functions.py",
    "old_auto_regression.py",
    "find_strings_seeds.py",
    "annotations.py",
    "ior_annotations.py",
    "wordy_scenes.py",
    "winners.py",
    "announcement.py",
    "helpers.py",
}
EXCLUDE_TOPICS = {
    "wordle",
    "SoME3",
    "colliding_blocks_v2",
    "convolutions",
    "convolutions2",
    "linalg",
    "clt",
    "clt_proof",
    "gauss_int",
    "hairy_ball",
}
EXCLUDE_NAME_RE = re.compile(
    r"(Thumbnail|TitleCard|EndScreen|Patreon|OpeningQuote|Logo|Banner|"
    r"Footer|ScratchPad|InterpolateTest|RobotTest|DiagramTest)$",
    re.I,
)
VARIANT_RE = re.compile(
    r"(V2|V3|V4|Short|Fast|Fast2|NoPause|Preview|PreviewClip)$"
)
PLAY_RE = re.compile(r"self\.play\(")
SIGNAL_WEIGHTS = (
    ("ValueTracker", 6),
    ("always_redraw", 5),
    ("f_always", 4),
    ("NumberPlane", 4),
    ("ThreeDAxes", 5),
    ("Axes(", 4),
    ("ComplexPlane", 4),
    ("ParametricCurve", 3),
    ("ParametricSurface", 4),
    ("StreamLines", 4),
    ("VectorField", 4),
    ("DecimalNumber", 3),
    ("MathTex", 2),
    ("Tex(", 3),
    ("Transform", 3),
    ("LaggedStart", 2),
    ("ShowCreation", 2),
    ("MoveAlongPath", 4),
    ("reorient", 3),
    ("updater", 3),
)
PENALTY_WEIGHTS = (
    ("ImageMobject", 6),
    ("SVGMobject", 4),
    ("PiCreature", 8),
    ("Teacher", 4),
    ("Student", 3),
    ("checkpoint_paste", 10),
    ("get_output_dir", 8),
    ("DATA_DIR", 6),
)

PINNED = [
    ("_2024/manim_demo/lorenz.py", "LorenzAttractor"),
    ("_2024/transformers/attention.py", "AttentionPatterns"),
    ("_2024/transformers/embedding.py", "Word2VecScene"),
    ("_2023/optics_puzzles/adding_waves.py", "WhiteLightAsASum"),
    ("_2022/quintic/polynomial_baisics.py", "ConstructPolynomialWithGivenRoots"),
    ("_2022/quintic/cubic.py", "CubicFormula"),
    ("_2022/galois/groups.py", "FlowerSymmetries"),
    ("_2022/piano/fourier_animations.py", "SumOfWaves"),
    ("_2022/piano/fourier_animations.py", "ThreeDChangeOfBasisExample"),
    ("_2022/borwein/main.py", "ShowIntegrals"),
]


def topic_from_rel(rel: Path) -> str:
    parts = rel.parts
    return parts[1] if len(parts) > 1 else parts[0]


def base_names(node: ast.ClassDef) -> list[str]:
    names = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            names.append(base.id)
        elif isinstance(base, ast.Attribute):
            names.append(base.attr)
    return names


def class_source(lines: list[str], node: ast.ClassDef) -> str:
    start = node.lineno - 1
    if node.decorator_list:
        start = min(start, node.decorator_list[0].lineno - 1)
    end = node.end_lineno or node.lineno
    return "".join(lines[start:end])


def has_construct(node: ast.ClassDef) -> ast.FunctionDef | None:
    for item in node.body:
        if isinstance(item, ast.FunctionDef) and item.name == "construct":
            return item
    return None


def construct_play_count(construct: ast.FunctionDef) -> int:
    return sum(
        1
        for n in ast.walk(construct)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "play"
        and isinstance(n.func.value, ast.Name)
        and n.func.value.id == "self"
    )


def score_scene(src: str, nlines: int, play_count: int) -> int:
    score = play_count * 4
    for token, weight in SIGNAL_WEIGHTS:
        if token in src:
            score += weight
    for token, weight in PENALTY_WEIGHTS:
        if token in src:
            score -= weight
    if 40 <= nlines <= 400:
        score += 12
    elif 25 <= nlines < 40:
        score += 2
    elif 400 < nlines <= 800:
        score += 6
    elif nlines > 1200:
        score -= 4
    elif nlines < 25:
        score -= 25
    return score


def iter_year_files(year: int):
    folder = VIDEOS / f"_{year}"
    if not folder.exists():
        return
    yield from folder.rglob("*.py")


def collect_candidates() -> list[dict]:
    rows: list[dict] = []
    for year in YEARS:
        for path in iter_year_files(year):
            if path.name.startswith("__") or path.name in EXCLUDE_FILE_NAMES:
                continue
            rel = path.relative_to(VIDEOS).as_posix()
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
            except SyntaxError:
                continue
            lines = text.splitlines(keepends=True)
            defined_classes = {
                n.name: n for n in tree.body if isinstance(n, ast.ClassDef)
            }
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                if EXCLUDE_NAME_RE.search(node.name):
                    continue
                bases = set(base_names(node))
                if bases & EXCLUDE_BASES:
                    continue
                if not (bases & ENGINE_SCENE_BASES):
                    # Local scene bases (RootCoefScene, Blocks, …) still count
                    # if some ancestor in this file is an engine scene.
                    ancestors = list(bases)
                    seen = set()
                    is_scene = False
                    while ancestors:
                        b = ancestors.pop()
                        if b in seen:
                            continue
                        seen.add(b)
                        if b in ENGINE_SCENE_BASES:
                            is_scene = True
                            break
                        if b in EXCLUDE_BASES:
                            is_scene = False
                            break
                        parent = defined_classes.get(b)
                        if parent is None:
                            # Unknown local-style base: treat as scene candidate
                            # only if the name ends with Scene or looks pedagogical.
                            is_scene = node.name.endswith("Scene") or b.endswith("Scene")
                            break
                        ancestors.extend(base_names(parent))
                    if not is_scene:
                        continue
                construct = has_construct(node)
                if construct is None:
                    continue
                nlines = (node.end_lineno or node.lineno) - node.lineno + 1
                play_count = construct_play_count(construct)
                if nlines < 25 or play_count < 2:
                    continue
                if VARIANT_RE.search(node.name):
                    continue
                src = class_source(lines, node)
                if "PiCreature" in src and play_count < 8:
                    continue
                topic = topic_from_rel(Path(rel))
                if topic in EXCLUDE_TOPICS:
                    continue
                rows.append(
                    {
                        "source_relpath": rel,
                        "class_name": node.name,
                        "year": year,
                        "topic": topic,
                        "nlines": nlines,
                        "play_count": play_count,
                        "score": score_scene(src, nlines, play_count),
                    }
                )
    return rows


def pin_key(rel: str, name: str) -> tuple[str, str]:
    return (rel.replace("\\", "/"), name)


def select_200(candidates: list[dict]) -> list[dict]:
    by_key = {(c["source_relpath"], c["class_name"]): c for c in candidates}
    selected: list[dict] = []
    used_keys: set[tuple[str, str]] = set()
    year_counts: dict[int, int] = defaultdict(int)
    topic_counts: dict[tuple[int, str], int] = defaultdict(int)

    def try_add(row: dict) -> bool:
        key = (row["source_relpath"], row["class_name"])
        if key in used_keys:
            return False
        year = row["year"]
        if year_counts[year] >= YEAR_QUOTAS[year]:
            return False
        cap = TOPIC_CAPS.get((year, row["topic"]))
        if cap is not None and topic_counts[(year, row["topic"])] >= cap:
            return False
        used_keys.add(key)
        selected.append(row)
        year_counts[year] += 1
        topic_counts[(year, row["topic"])] += 1
        return True

    for rel, name in PINNED:
        row = by_key.get(pin_key(rel, name))
        if row:
            # Pinned scenes may exceed topic cap by bumping the cap locally
            key = (row["source_relpath"], row["class_name"])
            if key not in used_keys and year_counts[row["year"]] < YEAR_QUOTAS[row["year"]]:
                used_keys.add(key)
                selected.append(row)
                year_counts[row["year"]] += 1
                topic_counts[(row["year"], row["topic"])] += 1

    ranked = sorted(
        candidates,
        key=lambda r: (-r["score"], -r["play_count"], r["source_relpath"], r["class_name"]),
    )

    # Fill each capped topic up to its cap (year quota still enforced).
    for row in ranked:
        if len(selected) >= 200:
            break
        if (row["year"], row["topic"]) not in TOPIC_CAPS:
            continue
        try_add(row)

    # Remaining year seats: prefer uncapped topics in-year, then any in-year.
    def fill_year(respect_topic_caps: bool, require_uncapped: bool) -> None:
        for row in ranked:
            if len(selected) >= 200:
                return
            year = row["year"]
            if year_counts[year] >= YEAR_QUOTAS[year]:
                continue
            key = (row["source_relpath"], row["class_name"])
            if key in used_keys:
                continue
            capped = (year, row["topic"]) in TOPIC_CAPS
            if require_uncapped and capped:
                continue
            if respect_topic_caps:
                try_add(row)
            else:
                used_keys.add(key)
                selected.append(row)
                year_counts[year] += 1
                topic_counts[(year, row["topic"])] += 1

    fill_year(respect_topic_caps=True, require_uncapped=True)
    fill_year(respect_topic_caps=True, require_uncapped=False)
    fill_year(respect_topic_caps=False, require_uncapped=False)

    # Last resort: remaining high-score rows (still 2022–2026).
    if len(selected) < 200:
        for row in ranked:
            if len(selected) >= 200:
                break
            key = (row["source_relpath"], row["class_name"])
            if key in used_keys:
                continue
            used_keys.add(key)
            selected.append(row)

    selected.sort(key=lambda r: (-r["year"], r["topic"], -r["score"], r["class_name"]))
    locked = []
    for i, row in enumerate(selected[:200], start=1):
        locked.append(
            {
                "id": f"MB-{i:03d}",
                "source_relpath": row["source_relpath"],
                "class_name": row["class_name"],
                "year": row["year"],
                "topic": row["topic"],
                "nlines": row["nlines"],
                "play_count": row["play_count"],
                "score": row["score"],
            }
        )
    return locked


def main() -> None:
    candidates = collect_candidates()
    locked = select_200(candidates)
    OUT_PATH.write_text(json.dumps(locked, indent=2) + "\n", encoding="utf-8")
    by_year: dict[int, int] = defaultdict(int)
    by_topic: dict[str, int] = defaultdict(int)
    for row in locked:
        by_year[row["year"]] += 1
        by_topic[f"{row['year']}/{row['topic']}"] += 1
    print(f"candidates={len(candidates)} locked={len(locked)} -> {OUT_PATH}")
    print("year", dict(sorted(by_year.items())))
    print("topics:")
    for k in sorted(by_topic):
        print(f"  {k}: {by_topic[k]}")


if __name__ == "__main__":
    main()
