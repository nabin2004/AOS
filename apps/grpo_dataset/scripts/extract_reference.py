"""Extract curated Scene classes into data/problems/MB-XXX/reference.py bundles."""
from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIDEOS = ROOT / "raw" / "videos"
CURATED = Path(__file__).resolve().parent / "curated_scenes.json"
PROBLEMS = ROOT / "data" / "problems"
INDEX_PATH = ROOT / "data" / "reference_index.json"

ENGINE_NAMES = {
    "InteractiveScene",
    "Scene",
    "ThreeDScene",
    "SpecialThreeDScene",
    "MovingCameraScene",
    "TeacherStudentsScene",
    "PiCreatureScene",
    "PatreonEndScreen",
    "EndScreen",
}
BUILTIN_OK = set(dir(__builtins__)) if isinstance(__builtins__, dict) else set(dir(__builtins__))
MAX_HELPER_LINES = 900


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def module_lines(path: Path) -> list[str]:
    return read_text(path).splitlines(keepends=True)


def parse_path(path: Path) -> ast.Module:
    return ast.parse(read_text(path))


def node_start(node: ast.AST) -> int:
    start = getattr(node, "lineno", 1) - 1
    deco = getattr(node, "decorator_list", None)
    if deco:
        start = min(start, deco[0].lineno - 1)
    return start


def node_end(node: ast.AST) -> int:
    return getattr(node, "end_lineno", getattr(node, "lineno", 1))


def slice_node(lines: list[str], node: ast.AST) -> str:
    return "".join(lines[node_start(node) : node_end(node)]).rstrip() + "\n"


def base_ids(node: ast.ClassDef) -> list[str]:
    names = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            names.append(base.id)
        elif isinstance(base, ast.Attribute):
            names.append(base.attr)
    return names


def load_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            names.add(n.id)
        elif isinstance(n, ast.ClassDef):
            names.update(base_ids(n))
    return names


class ModuleIndex:
    def __init__(self, path: Path):
        self.path = path
        self.lines = module_lines(path)
        self.tree = ast.parse("".join(self.lines))
        self.classes: dict[str, ast.ClassDef] = {}
        self.functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        self.assigns: dict[str, ast.AST] = {}
        self.imports: list[ast.AST] = []
        for node in self.tree.body:
            if isinstance(node, ast.ClassDef):
                self.classes[node.name] = node
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.functions[node.name] = node
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                self.imports.append(node)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        self.assigns[t.id] = node
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                self.assigns[node.target.id] = node

    def defines(self, name: str) -> ast.AST | None:
        return self.classes.get(name) or self.functions.get(name) or self.assigns.get(name)


def import_module_path(node: ast.ImportFrom) -> Path | None:
    if not node.module:
        return None
    parts = node.module.split(".")
    if not parts[0].startswith("_20"):
        return None
    candidate = VIDEOS.joinpath(*parts).with_suffix(".py")
    if candidate.exists():
        return candidate
    return None


def imported_names(mod: ModuleIndex) -> dict[str, tuple[Path, str | None]]:
    """name -> (path, original_name or None for star)."""
    mapping: dict[str, tuple[Path, str | None]] = {}
    for node in mod.imports:
        if not isinstance(node, ast.ImportFrom):
            continue
        path = import_module_path(node)
        if path is None:
            continue
        if node.names[0].name == "*":
            mapping[f"*:{path.as_posix()}"] = (path, "*")
        else:
            for alias in node.names:
                local = alias.asname or alias.name
                mapping[local] = (path, alias.name)
    return mapping


_index_cache: dict[Path, ModuleIndex] = {}


def get_index(path: Path) -> ModuleIndex:
    path = path.resolve()
    if path not in _index_cache:
        _index_cache[path] = ModuleIndex(path)
    return _index_cache[path]


def collect_needed(
    start_path: Path,
    class_name: str,
) -> tuple[list[tuple[Path, ast.AST, str]], list[str]]:
    """Return ordered (path, node, kind) defs plus kept import source strings."""
    start = get_index(start_path)
    if class_name not in start.classes:
        raise KeyError(f"{class_name} not in {start_path}")

    needed: dict[tuple[Path, str], ast.AST] = {}
    order: list[tuple[Path, str]] = []
    helper_lines = 0

    def add_def(path: Path, name: str, node: ast.AST) -> None:
        nonlocal helper_lines
        key = (path.resolve(), name)
        if key in needed:
            return
        extra = (node_end(node) - node_start(node))
        if path.resolve() != start_path.resolve() and helper_lines + extra > MAX_HELPER_LINES:
            return
        if path.resolve() != start_path.resolve():
            helper_lines += extra
        needed[key] = node
        order.append(key)

    pending: list[tuple[Path, ast.AST]] = [(start_path, start.classes[class_name])]
    add_def(start_path, class_name, start.classes[class_name])

    seen_walk: set[tuple[Path, int]] = set()
    while pending:
        path, node = pending.pop()
        walk_key = (path.resolve(), id(node))
        if walk_key in seen_walk:
            continue
        seen_walk.add(walk_key)
        idx = get_index(path)
        used = load_names(node)
        for base in base_ids(node) if isinstance(node, ast.ClassDef) else []:
            if base in ENGINE_NAMES:
                continue
            local = idx.defines(base)
            if local is not None:
                add_def(path, base, local)
                pending.append((path, local))
                continue
            imap = imported_names(idx)
            if base in imap:
                other_path, orig = imap[base]
                other = get_index(other_path)
                orig_name = orig or base
                found = other.defines(orig_name)
                if found is not None:
                    add_def(other_path, orig_name, found)
                    pending.append((other_path, found))

        imap = imported_names(idx)
        star_paths = [p for k, (p, kind) in imap.items() if kind == "*"]
        for name in used:
            if name in ENGINE_NAMES or name in BUILTIN_OK or name in {"self", "cls"}:
                continue
            local = idx.defines(name)
            if local is not None:
                add_def(path, name, local)
                pending.append((path, local))
                continue
            if name in imap:
                other_path, orig = imap[name]
                if orig == "*":
                    continue
                other = get_index(other_path)
                orig_name = orig or name
                found = other.defines(orig_name)
                if found is not None:
                    add_def(other_path, orig_name, found)
                    pending.append((other_path, found))
                continue
            for sp in star_paths:
                other = get_index(sp)
                found = other.defines(name)
                if found is not None:
                    add_def(sp, name, found)
                    pending.append((sp, found))
                    break

    kept_imports: list[str] = []
    seen_imp = set()
    for node in start.imports:
        src = slice_node(start.lines, node).strip()
        if "manim_imports_ext" in src:
            continue
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("_20"):
            continue
        if src not in seen_imp:
            seen_imp.add(src)
            kept_imports.append(src)

    items: list[tuple[Path, ast.AST, str]] = []
    for path, name in order:
        node = needed[(path, name)]
        kind = type(node).__name__
        items.append((path, node, kind))
    return items, kept_imports


def inherits_engine_scene(node: ast.ClassDef, by_name: dict[str, ast.ClassDef]) -> bool:
    stack = list(base_ids(node))
    seen = {node.name}
    while stack:
        base = stack.pop()
        if base in ENGINE_NAMES:
            return True
        if base in seen:
            continue
        seen.add(base)
        parent = by_name.get(base)
        if parent is not None:
            stack.extend(base_ids(parent))
    return False


def _kahn(nodes: list[ast.ClassDef], by_name: dict[str, ast.ClassDef]) -> list[ast.ClassDef]:
    if not nodes:
        return []
    names = {node.name for node in nodes}
    indeg = {node.name: 0 for node in nodes}
    children: dict[str, list[str]] = {node.name: [] for node in nodes}
    for node in nodes:
        for base in base_ids(node):
            if base in names and base != node.name:
                children[base].append(node.name)
                indeg[node.name] += 1
    queue = [node.name for node in nodes if indeg[node.name] == 0]
    ordered: list[ast.ClassDef] = []
    seen: set[str] = set()
    while queue:
        name = queue.pop(0)
        if name in seen:
            continue
        seen.add(name)
        ordered.append(by_name[name])
        for child in children[name]:
            indeg[child] -= 1
            if indeg[child] == 0:
                queue.append(child)
    for node in nodes:
        if node.name not in seen:
            ordered.append(node)
    return ordered


def topo_order_classes(class_nodes: list[ast.ClassDef]) -> list[ast.ClassDef]:
    by_name: dict[str, ast.ClassDef] = {}
    for node in class_nodes:
        by_name.setdefault(node.name, node)
    unique = list(by_name.values())
    helpers = [n for n in unique if not inherits_engine_scene(n, by_name)]
    scenes = [n for n in unique if inherits_engine_scene(n, by_name)]
    return _kahn(helpers, by_name) + _kahn(scenes, by_name)


def ordered_nodes(items: list[tuple[Path, ast.AST, str]]) -> list[tuple[Path, ast.AST]]:
    others: list[tuple[Path, ast.AST]] = []
    classes: list[tuple[Path, ast.ClassDef]] = []
    seen: set[int] = set()
    for path, node, _kind in items:
        if id(node) in seen:
            continue
        seen.add(id(node))
        if isinstance(node, ast.ClassDef):
            classes.append((path, node))
        else:
            others.append((path, node))
    path_by_name = {node.name: path for path, node in classes}
    sorted_classes = topo_order_classes([node for _, node in classes])
    class_items = [(path_by_name[node.name], node) for node in sorted_classes]
    return others + class_items


def render_reference(entry: dict) -> str:
    rel = entry["source_relpath"]
    class_name = entry["class_name"]
    path = VIDEOS / rel
    items, kept_imports = collect_needed(path, class_name)

    chunks: list[str] = []
    seen_src = set()
    for p, node in ordered_nodes(items):
        src = slice_node(get_index(p).lines, node)
        if src in seen_src:
            continue
        seen_src.add(src)
        chunks.append(src.rstrip() + "\n")

    header = (
        f'"""Reference scene extracted from 3b1b/videos.\n'
        f"\n"
        f"Source: {rel}\n"
        f"Class: {class_name}\n"
        f"Year: {entry['year']}\n"
        f"License: CC BY-NC-SA 4.0 (Grant Sanderson / 3Blue1Brown)\n"
        f'"""\n'
        f"from manim_imports_ext import *\n"
    )
    extra_imports = ""
    if kept_imports:
        extra_imports = "\n".join(kept_imports) + "\n"
    body = "\n".join(chunks)
    return header + extra_imports + "\n" + body


def write_placeholders(folder: Path) -> None:
    for name in ("problem.json", "visual_events.json", "coverage.json", "version_notes.json"):
        (folder / name).write_text("", encoding="utf-8")


def main() -> None:
    curated = json.loads(CURATED.read_text(encoding="utf-8"))
    PROBLEMS.mkdir(parents=True, exist_ok=True)
    index = []
    failures = []
    for entry in curated:
        pid = entry["id"]
        folder = PROBLEMS / pid
        folder.mkdir(parents=True, exist_ok=True)
        try:
            text = render_reference(entry)
            (folder / "reference.py").write_text(text, encoding="utf-8")
            ast.parse(text)
            write_placeholders(folder)
            index.append(
                {
                    "id": pid,
                    "source_relpath": entry["source_relpath"],
                    "class_name": entry["class_name"],
                    "year": entry["year"],
                    "topic": entry["topic"],
                }
            )
            print(f"OK {pid} {entry['class_name']} {entry['source_relpath']}")
        except Exception as exc:  # noqa: BLE001
            failures.append({"id": pid, "error": repr(exc), **entry})
            print(f"FAIL {pid} {entry['class_name']}: {exc!r}")

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    if failures:
        fail_path = ROOT / "data" / "extract_failures.json"
        fail_path.write_text(json.dumps(failures, indent=2) + "\n", encoding="utf-8")
        raise SystemExit(f"{len(failures)} extract failures; see {fail_path}")
    print(f"wrote {len(index)} problems -> {PROBLEMS}")


if __name__ == "__main__":
    main()
