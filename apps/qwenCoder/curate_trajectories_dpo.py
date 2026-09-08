#!/usr/bin/env python3
"""Curate clean DPO preference pairs and Continued SFT datasets from AOS-Trajectories.

Transforms high-quality, authentic code-agent trajectories from
`nabin2004/AOS-Trajectories` into:
1. DPO Preference Dataset (chosen: VoiceoverScene with synchronized narration,
   rejected: structurally identical silent Scene generated via AST transformation).
2. Continued SFT Dataset (chat messages format with system prompt and VoiceoverScene).

Usage:
    uv run python curate_trajectories_dpo.py
    uv run python curate_trajectories_dpo.py --push-to-hub --dpo-repo nabin2004/manim-narrated-dpo-400
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Reconfigure stdout/stderr for clean UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    from huggingface_hub import HfApi, get_token, hf_hub_download
except ImportError:
    HfApi = None
    get_token = None
    hf_hub_download = None

QWEN_ROOT = Path(__file__).resolve().parent
REPO_ROOT = QWEN_ROOT.parent.parent

DEFAULT_TRAJECTORIES_REPO = "nabin2004/AOS-Trajectories"
DEFAULT_DPO_DIR = QWEN_ROOT / "data_narrated_dpo"
DEFAULT_SFT_DIR = QWEN_ROOT / "data_narrated_sft"
DEFAULT_DPO_REPO = "nabin2004/manim-narrated-dpo-400"
DEFAULT_SFT_REPO = "nabin2004/AOS-Narrated-Manim-400"

SYSTEM_PROMPT = (
    "You are an expert mathematical animator and pedagogical engineer using Manim Community Edition "
    "and manim-voiceover with AOSSpeechService. Write executable, self-contained Python code that "
    "synchronizes mathematical animations with spoken educational explanations."
)


def _format_code_block(code_str: str) -> str:
    code_str = code_str.strip()
    if code_str.startswith("```python") and code_str.endswith("```"):
        return code_str
    if code_str.startswith("```") and code_str.endswith("```"):
        return code_str
    return f"```python\n{code_str}\n```"


def fix_escape_sequences_exact(code_str: str) -> str:
    r"""Ensure non-raw string literals containing invalid escape sequences (e.g. '\s', '\%') become raw r'...'."""
    import io
    import tokenize

    try:
        tokens = list(tokenize.tokenize(io.BytesIO(code_str.encode("utf-8")).readline))
    except Exception:
        return code_str

    invalid_escape_re = re.compile(r'\\(?![ntrbfa\\v\'"0-7xuUN])')
    lines = code_str.splitlines(keepends=True)

    # Process string tokens in reverse so row/col offsets remain stable
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


def sanitize_voiceover_code(raw_code: str) -> Optional[str]:
    """Sanitize and validate a VoiceoverScene Python script."""
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

    # Apply precise escape sequence cleanup
    code = fix_escape_sequences_exact(code)

    # Ensure essential imports exist if VoiceoverScene or AOSSpeechService is referenced
    lines = code.splitlines()
    has_manim_import = any("from manim import" in line for line in lines)
    has_vo_import = any("manim_voiceover" in line for line in lines)
    has_speech_import = any("tools.aos_speech_service" in line for line in lines)

    prefix_lines: List[str] = []
    if not has_manim_import:
        prefix_lines.append("from manim import *")
    if not has_vo_import:
        prefix_lines.append("from manim_voiceover import VoiceoverScene")
    if not has_speech_import:
        prefix_lines.append("from tools.aos_speech_service import AOSSpeechService")

    if prefix_lines:
        code = "\n".join(prefix_lines) + "\n\n" + code

    # Validate AST
    import warnings
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            ast.parse(code)
    except SyntaxError:
        return None

    return code.strip()


class SilentSceneTransformer(ast.NodeTransformer):
    """Transforms a VoiceoverScene AST into a clean silent Scene AST."""

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
            # Replace tracker.duration references with a standard duration (2.0s)
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


def convert_to_silent_scene(narrated_code: str) -> Optional[str]:
    """Convert a VoiceoverScene into its structurally identical silent Scene counterpart."""
    import warnings

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(narrated_code)
    except SyntaxError:
        return None

    transformer = SilentSceneTransformer()
    new_tree = transformer.visit(tree)
    ast.fix_missing_locations(new_tree)

    try:
        silent_code = ast.unparse(new_tree).strip()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            ast.parse(silent_code)
        return silent_code
    except Exception:
        return None


def fetch_trajectories(repo_id: str = DEFAULT_TRAJECTORIES_REPO, local_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load raw trajectories from local file or Hugging Face Hub."""
    target_path = local_path
    if not target_path or not target_path.is_file():
        if hf_hub_download is None:
            raise RuntimeError("huggingface_hub is required to download trajectories from hub.")
        token = os.environ.get("HF_TOKEN") or (get_token() if get_token else None)
        print(f"Downloading trajectories.jsonl from Hub: {repo_id}...")
        downloaded = hf_hub_download(
            repo_id=repo_id,
            filename="trajectories.jsonl",
            repo_type="dataset",
            token=token,
        )
        target_path = Path(downloaded)

    records: List[Dict[str, Any]] = []
    with open(target_path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                records.append(json.loads(line_str))
            except json.JSONDecodeError:
                continue

    print(f"Loaded {len(records)} raw trajectories from: {target_path}")
    return records


def curate_datasets(
    trajectories: List[Dict[str, Any]],
    output_dpo_dir: Path,
    output_sft_dir: Path,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Process trajectories into clean DPO preference pairs and Continued SFT records."""
    output_dpo_dir.mkdir(parents=True, exist_ok=True)
    output_sft_dir.mkdir(parents=True, exist_ok=True)

    dpo_records: List[Dict[str, Any]] = []
    sft_records: List[Dict[str, Any]] = []

    skipped_no_code = 0
    skipped_non_vo = 0
    skipped_syntax = 0
    skipped_silent_fail = 0

    seen_prompts: set[str] = set()

    for idx, item in enumerate(trajectories):
        prompt = (item.get("user_prompt") or "").strip()
        raw_code = item.get("final_code")

        if not prompt or not raw_code:
            skipped_no_code += 1
            continue

        if prompt in seen_prompts:
            continue
        seen_prompts.add(prompt)

        # Check that this trajectory is a VoiceoverScene
        if "VoiceoverScene" not in raw_code:
            skipped_non_vo += 1
            continue

        # 1. Sanitize & validate narrated VoiceoverScene (chosen)
        chosen_code = sanitize_voiceover_code(raw_code)
        if not chosen_code:
            skipped_syntax += 1
            continue

        # 2. Derive silent Scene counterpart (rejected)
        silent_code = convert_to_silent_scene(chosen_code)
        if not silent_code:
            skipped_silent_fail += 1
            continue

        formatted_chosen = _format_code_block(chosen_code)
        formatted_rejected = _format_code_block(silent_code)

        sample_id = f"aos_traj_{idx:04d}"
        topic_summary = (item.get("summary") or prompt[:80]).strip()

        # DPO Record
        dpo_item = {
            "prompt": prompt,
            "chosen": formatted_chosen,
            "rejected": formatted_rejected,
            "metadata": {
                "id": sample_id,
                "source": "nabin2004/AOS-Trajectories",
                "summary": topic_summary,
            },
        }
        dpo_records.append(dpo_item)

        # Continued SFT Record (Chat messages format)
        sft_item = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": formatted_chosen},
            ],
            "metadata": {
                "id": sample_id,
                "source": "nabin2004/AOS-Trajectories",
                "summary": topic_summary,
            },
        }
        sft_records.append(sft_item)

    print("\n--- Curation Statistics ---")
    print(f"Total input trajectories:     {len(trajectories)}")
    print(f"Skipped missing code/prompt:  {skipped_no_code}")
    print(f"Skipped non-Voiceover scenes: {skipped_non_vo}")
    print(f"Skipped syntax/validation:    {skipped_syntax}")
    print(f"Skipped silent conversion:    {skipped_silent_fail}")
    print(f"Successfully curated pairs:   {len(dpo_records)}")

    # Write DPO train.jsonl
    dpo_file = output_dpo_dir / "train.jsonl"
    with open(dpo_file, "w", encoding="utf-8") as f:
        for r in dpo_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"✔ Saved DPO dataset: {dpo_file} ({len(dpo_records)} samples)")

    # Write SFT train.jsonl
    sft_file = output_sft_dir / "train.jsonl"
    with open(sft_file, "w", encoding="utf-8") as f:
        for r in sft_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"✔ Saved Continued SFT dataset: {sft_file} ({len(sft_records)} samples)")

    return dpo_records, sft_records


def push_to_hf(
    local_dir: Path,
    repo_id: str,
    commit_message: str,
    repo_type: str = "dataset",
) -> None:
    """Upload a curated dataset directory to Hugging Face Hub."""
    if HfApi is None:
        raise ImportError("huggingface_hub is required to push to Hub.")
    token = os.environ.get("HF_TOKEN") or (get_token() if get_token else None)
    if not token:
        print(f"WARNING: HF_TOKEN not found. Skipping push to {repo_id}.", file=sys.stderr)
        return

    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type=repo_type, exist_ok=True)

    print(f"Uploading files from {local_dir} to {repo_id}...")
    api.upload_folder(
        folder_path=str(local_dir),
        repo_id=repo_id,
        repo_type=repo_type,
        commit_message=commit_message,
    )
    print(f"✔ Uploaded dataset successfully to https://huggingface.co/datasets/{repo_id}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Curate clean DPO & SFT datasets from nabin2004/AOS-Trajectories"
    )
    parser.add_argument(
        "--input-trajectories",
        type=Path,
        default=None,
        help="Optional local path to trajectories.jsonl",
    )
    parser.add_argument(
        "--hub-input-repo",
        default=DEFAULT_TRAJECTORIES_REPO,
        help=f"Hub repository for raw trajectories (default: {DEFAULT_TRAJECTORIES_REPO})",
    )
    parser.add_argument(
        "--dpo-out-dir",
        type=Path,
        default=DEFAULT_DPO_DIR,
        help=f"Directory to save DPO train.jsonl (default: {DEFAULT_DPO_DIR})",
    )
    parser.add_argument(
        "--sft-out-dir",
        type=Path,
        default=DEFAULT_SFT_DIR,
        help=f"Directory to save SFT train.jsonl (default: {DEFAULT_SFT_DIR})",
    )
    parser.add_argument(
        "--push-to-hub",
        action="store_true",
        help="Push curated datasets to Hugging Face Hub",
    )
    parser.add_argument(
        "--dpo-repo",
        default=DEFAULT_DPO_REPO,
        help=f"Target HF dataset repo for DPO (default: {DEFAULT_DPO_REPO})",
    )
    parser.add_argument(
        "--sft-repo",
        default=DEFAULT_SFT_REPO,
        help=f"Target HF dataset repo for Continued SFT (default: {DEFAULT_SFT_REPO})",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    trajectories = fetch_trajectories(
        repo_id=args.hub_input_repo,
        local_path=args.input_trajectories,
    )

    dpo_records, sft_records = curate_datasets(
        trajectories=trajectories,
        output_dpo_dir=args.dpo_out_dir,
        output_sft_dir=args.sft_out_dir,
    )

    if args.push_to_hub:
        push_to_hf(
            local_dir=args.dpo_out_dir,
            repo_id=args.dpo_repo,
            commit_message=f"Upload clean DPO preference dataset ({len(dpo_records)} samples from AOS-Trajectories)",
        )
        push_to_hf(
            local_dir=args.sft_out_dir,
            repo_id=args.sft_repo,
            commit_message=f"Upload clean Continued SFT dataset ({len(sft_records)} samples from AOS-Trajectories)",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
