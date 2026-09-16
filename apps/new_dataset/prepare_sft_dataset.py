#!/usr/bin/env python3
"""Prepare the ManimCE SFT Dataset for Qwen3-8B from AOS-Trajectories.

Transforms multi-turn raw agent trajectories from `nabin2004/AOS-Trajectories` into a
clean, high-quality Supervised Fine-Tuning dataset formatted with the Qwen Chat Template.

Key features:
1. AST-based transformation from VoiceoverScene into pure, standard ManimCE `Scene`.
2. Escape sequence repair for LaTeX math expressions (raw r'...' string literals).
3. 100% executable syntax verified by Python AST parser.
4. Pedagogical spatial reasoning & animation planning steps in the assistant response.
5. Exports both JSONL and Parquet formats for training and Hugging Face Dataset Viewer.

Usage:
    uv run python prepare_sft_dataset.py
    uv run python prepare_sft_dataset.py --output-dir ./data
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from datasets import Dataset, DatasetDict
from huggingface_hub import hf_hub_download

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "data"
DEFAULT_SOURCE_REPO = "nabin2004/AOS-Trajectories"

SYSTEM_PROMPT = (
    "You are an expert Python programmer specializing in the Manim Community Edition (ManimCE) library. "
    "You write clean, executable, and visually appealing mathematical animations. "
    "Always plan your spatial layout and animation sequence, then wrap your complete Python code in ```python ... ``` blocks."
)


def fix_escape_sequences_exact(code_str: str) -> str:
    r"""Ensure non-raw string literals containing invalid escape sequences (e.g. '\s', '\%', '\m') become raw r'...'."""
    import io
    import tokenize

    try:
        tokens = list(tokenize.tokenize(io.BytesIO(code_str.encode("utf-8")).readline))
    except Exception:
        return code_str

    invalid_escape_re = re.compile(r'\\(?![ntrbfa\\v\'"0-7xuUN])')
    lines = code_str.splitlines(keepends=True)

    string_tokens = [tok for tok in tokens if tok.type == tokenize.STRING]
    string_tokens.reverse()

    for tok in string_tokens:
        val = tok.string
        prefix_match = re.match(r"^([rRuUbBfF]*)([\"'].*)$", val, re.DOTALL)
        if prefix_match:
            prefix, body = prefix_match.groups()
            if "r" not in prefix.lower() and invalid_escape_re.search(body):
                s_row, s_col = tok.start
                if 1 <= s_row <= len(lines):
                    line = lines[s_row - 1]
                    lines[s_row - 1] = line[:s_col] + "r" + line[s_col:]

    return "".join(lines)


class SilentSceneTransformer(ast.NodeTransformer):
    """Transforms a VoiceoverScene AST into a standalone ManimCE Scene AST."""

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        if node.module in ("manim_voiceover", "tools.aos_speech_service"):
            return None
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        new_bases = []
        for b in node.bases:
            if getattr(b, "id", "") == "VoiceoverScene":
                new_bases.append(ast.Name(id="Scene", ctx=ast.Load()))
            else:
                new_bases.append(b)
        node.bases = new_bases
        self.generic_visit(node)
        return node

    def visit_Expr(self, node: ast.Expr) -> Any:
        if isinstance(node.value, ast.Call):
            func = node.value.func
            if isinstance(func, ast.Attribute) and func.attr in (
                "set_speech_service",
                "wait_until_bookmark",
            ):
                return None
        return self.generic_visit(node)

    def visit_With(self, node: ast.With) -> Any:
        is_vo = False
        for item in node.items:
            ctx_expr = item.context_expr
            if isinstance(ctx_expr, ast.Call) and isinstance(ctx_expr.func, ast.Attribute):
                if ctx_expr.func.attr == "voiceover":
                    is_vo = True
                    break

        if is_vo:
            class DurationReplacer(ast.NodeTransformer):
                def visit_Attribute(self, attr_node: ast.Attribute) -> Any:
                    if (
                        attr_node.attr == "duration"
                        and isinstance(attr_node.value, ast.Name)
                        and attr_node.value.id == "tracker"
                    ):
                        return ast.Constant(value=2.0)
                    return attr_node

            new_body = []
            for stmt in node.body:
                transformed = DurationReplacer().visit(stmt)
                if transformed is not None:
                    new_body.append(transformed)

            flattened = []
            for s in new_body:
                res = self.visit(s)
                if isinstance(res, list):
                    flattened.extend(res)
                elif res is not None:
                    flattened.append(res)
            return flattened

        return self.generic_visit(node)


def convert_to_pure_manimce(raw_code: str) -> Optional[str]:
    """Convert and sanitize raw code into pure, standalone ManimCE Scene code."""
    code = raw_code.strip()
    if not code:
        return None

    # Strip surrounding markdown code fence if already present
    if code.startswith("```python"):
        code = code[len("```python"):].strip()
    elif code.startswith("```"):
        code = code[3:].strip()
    if code.endswith("```"):
        code = code[:-3].strip()

    code = fix_escape_sequences_exact(code)

    # Ensure essential import
    if "from manim import *" not in code and "from manim import" not in code:
        code = "from manim import *\n\n" + code

    import warnings
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(code)
    except SyntaxError:
        return None

    transformer = SilentSceneTransformer()
    new_tree = transformer.visit(tree)
    ast.fix_missing_locations(new_tree)

    try:
        clean_code = ast.unparse(new_tree).strip()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            final_tree = ast.parse(clean_code)

        # Ensure valid Scene class definition exists
        has_scene = any(
            isinstance(node, ast.ClassDef)
            and any(
                (isinstance(b, ast.Name) and "Scene" in b.id)
                or (isinstance(b, ast.Attribute) and "Scene" in b.attr)
                for b in node.bases
            )
            for node in ast.walk(final_tree)
        )
        if not has_scene or len(clean_code) < 100:
            return None

        return clean_code
    except Exception:
        return None


def extract_planning_thought(summary_text: str, user_prompt: str) -> str:
    """Extract or generate a structured pedagogical planning step."""
    if summary_text:
        lines = summary_text.splitlines()
        clean_lines = []
        in_content = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if "Output Location:" in stripped or "/home/" in stripped or "├──" in stripped:
                break
            if (
                stripped.startswith("✅")
                or stripped.startswith("## What Was Created")
                or stripped.startswith("### Scene:")
            ):
                in_content = True
                continue
            if in_content or stripped.startswith("1.") or stripped.startswith("- ") or stripped.startswith("###"):
                cleaned = re.sub(r"^###\s*", "", stripped)
                clean_lines.append(cleaned)

        if clean_lines:
            plan_body = "\n".join(clean_lines[:12])
            return f"Here is the visual and pedagogical plan for the animation:\n{plan_body}\n"

    # Default structured plan based on user prompt
    return (
        "To visualize this concept effectively using Manim Community Edition, "
        "I will structure the animation into clear phases: introduce the mathematical entities, "
        "highlight key relationships with dynamic color-coding, and animate the geometric transitions smoothly.\n"
    )


def format_assistant_response(plan: str, code: str) -> str:
    """Assemble assistant response with planning thought + python code fence."""
    code_block = f"```python\n{code}\n```"
    if plan:
        return f"{plan.strip()}\n\n{code_block}"
    return code_block


def load_source_trajectories(repo_id: str) -> List[Dict[str, Any]]:
    """Download trajectories.jsonl from Hugging Face Hub."""
    print(f"Fetching trajectories.jsonl from Hub: {repo_id}...")
    file_path = hf_hub_download(
        repo_id=repo_id,
        filename="trajectories.jsonl",
        repo_type="dataset",
    )
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    print(f"Loaded {len(records)} raw trajectories.")
    return records


def get_existing_split_prompts(repo_id: str) -> Tuple[set[str], set[str]]:
    """Retrieve existing prompt partitions for exact train/val parity if available."""
    try:
        p_train = hf_hub_download(repo_id=repo_id, filename="tool_trace/train.jsonl", repo_type="dataset")
        p_val = hf_hub_download(repo_id=repo_id, filename="tool_trace/val.jsonl", repo_type="dataset")

        with open(p_train, "r", encoding="utf-8") as f:
            train_prompts = set(json.loads(line)["messages"][0]["content"].strip() for line in f if line.strip())

        with open(p_val, "r", encoding="utf-8") as f:
            val_prompts = set(json.loads(line)["messages"][0]["content"].strip() for line in f if line.strip())

        return train_prompts, val_prompts
    except Exception as exc:
        print(f"Note: Could not load existing split prompts ({exc}); will use 90/10 split.")
        return set(), set()


def prepare_dataset(
    repo_id: str = DEFAULT_SOURCE_REPO,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Execute the full curation and preparation pipeline."""
    output_dir.mkdir(parents=True, exist_ok=True)
    trajectories = load_source_trajectories(repo_id)
    existing_train_prompts, existing_val_prompts = get_existing_split_prompts(repo_id)

    curated_samples: List[Dict[str, Any]] = []
    skipped_count = 0

    seen_prompts: set[str] = set()

    for idx, item in enumerate(trajectories):
        prompt = (item.get("user_prompt") or "").strip()
        raw_code = item.get("final_code") or ""
        success = item.get("success", False)

        if not prompt or not raw_code or not success:
            skipped_count += 1
            continue

        if prompt in seen_prompts:
            continue
        seen_prompts.add(prompt)

        clean_code = convert_to_pure_manimce(raw_code)
        if not clean_code:
            skipped_count += 1
            continue

        plan = extract_planning_thought(item.get("summary") or "", prompt)
        assistant_content = format_assistant_response(plan, clean_code)

        sample = {
            "id": f"aos_sft_{idx:04d}",
            "prompt_index": item.get("prompt_index", idx),
            "user_prompt": prompt,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": assistant_content},
            ],
            "code": clean_code,
            "has_plan": bool(plan),
        }
        curated_samples.append(sample)

    print(f"\nSuccessfully curated {len(curated_samples)} high-quality samples (skipped {skipped_count}).")

    # Split into train and validation
    train_samples: List[Dict[str, Any]] = []
    val_samples: List[Dict[str, Any]] = []

    if existing_train_prompts or existing_val_prompts:
        for s in curated_samples:
            if s["user_prompt"] in existing_val_prompts:
                val_samples.append(s)
            else:
                train_samples.append(s)
    else:
        split_idx = int(len(curated_samples) * 0.9)
        train_samples = curated_samples[:split_idx]
        val_samples = curated_samples[split_idx:]

    print(f"Train split:      {len(train_samples)} samples")
    print(f"Validation split: {len(val_samples)} samples")

    # Save JSONL files (chat format with messages)
    train_jsonl = output_dir / "train.jsonl"
    val_jsonl = output_dir / "val.jsonl"

    with open(train_jsonl, "w", encoding="utf-8") as f:
        for s in train_samples:
            row = {"messages": s["messages"]}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    with open(val_jsonl, "w", encoding="utf-8") as f:
        for s in val_samples:
            row = {"messages": s["messages"]}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"✔ Saved JSONL: {train_jsonl}")
    print(f"✔ Saved JSONL: {val_jsonl}")

    # Save Parquet files via Hugging Face datasets
    hf_train = Dataset.from_list([{"messages": s["messages"]} for s in train_samples])
    hf_val = Dataset.from_list([{"messages": s["messages"]} for s in val_samples])

    train_parquet = output_dir / "train.parquet"
    val_parquet = output_dir / "val.parquet"

    hf_train.to_parquet(str(train_parquet))
    hf_val.to_parquet(str(val_parquet))

    print(f"✔ Saved Parquet: {train_parquet}")
    print(f"✔ Saved Parquet: {val_parquet}")

    # Generate metadata summary
    metadata = {
        "dataset_name": "AOS-Manim-SFT",
        "source_repo": repo_id,
        "format": "qwen_chat_template",
        "system_prompt": SYSTEM_PROMPT,
        "num_train": len(train_samples),
        "num_val": len(val_samples),
        "num_total": len(curated_samples),
        "ast_syntax_verified": True,
        "pure_manimce_standard": True,
    }
    with open(output_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return train_samples, val_samples


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare ManimCE SFT Dataset for Qwen3-8B")
    parser.add_argument("--repo-id", default=DEFAULT_SOURCE_REPO, help="Source trajectories repo")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory")
    args = parser.parse_args()

    prepare_dataset(repo_id=args.repo_id, output_dir=args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
