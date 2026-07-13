import re
from pathlib import Path

MODULE_RE = re.compile(r"- \*\*Module:\*\* `([^`]+)`")
CONSTRUCTOR_RE = re.compile(r"- \*\*Constructor:\*\* `([^`]+)`")
SIGNATURE_RE = re.compile(r"- \*\*Signature:\*\* `([^`]+)`")
METHOD_RE = re.compile(r"^\s*-\s+`([^`]+)`")
H2_RE = re.compile(r"^## (.+)$")
H3_RE = re.compile(r"^### (.+)$")


def _parse_module(text: str) -> str:
    match = MODULE_RE.search(text)
    return match.group(1) if match else ""


def _section_label(section: str) -> str:
    """Turn 'Classes (256)' into 'Classes'."""
    return section.split("(")[0].strip()


def _make_embed_text(name: str, module: str, entry_text: str) -> str:
    """Shorter text for embedding — skip long inherited method lists."""
    lines = [f"### {name}"]
    if module:
        lines.append(f"Module: {module}")

    for line in entry_text.splitlines():
        if line.startswith("- **Methods:**"):
            break
        lines.append(line)
        if sum(len(l) for l in lines) > 1200:
            break

    return "\n".join(lines).strip()


def _make_entry_id(section: str, name: str) -> str:
    label = _section_label(section).lower().replace(" ", "_")
    return f"{label}:{name}"


def _make_sig_id(parent: str, name: str) -> str:
    safe_name = name.replace(".", "_")
    return f"sig:{parent}.{safe_name}"


def _extract_signatures(
    entry_text: str,
    section: str,
    parent: str,
    module: str,
) -> list[dict]:
    """Pull constructor, function signature, and method lines into micro-chunks."""
    sigs: list[dict] = []
    seen: set[str] = set()

    for match in CONSTRUCTOR_RE.finditer(entry_text):
        sig = match.group(1)
        if sig in seen:
            continue
        seen.add(sig)
        sigs.append(_build_sig_chunk(section, parent, "__init__", module, sig))

    for match in SIGNATURE_RE.finditer(entry_text):
        sig = match.group(1)
        if sig in seen:
            continue
        seen.add(sig)
        func_name = sig.split("(")[0].strip()
        sigs.append(_build_sig_chunk(section, parent, func_name, module, sig))

    for line in entry_text.splitlines():
        if "_(from " in line:
            continue
        match = METHOD_RE.match(line)
        if not match:
            continue
        sig = match.group(1)
        if "(" not in sig:
            continue
        func_name = sig.split("(")[0].strip()
        if func_name in ("__init__", parent):
            continue
        if sig in seen:
            continue
        seen.add(sig)
        sigs.append(_build_sig_chunk(section, parent, func_name, module, sig))

    return sigs


def _build_sig_chunk(
    section: str,
    parent: str,
    name: str,
    module: str,
    signature: str,
) -> dict:
    qualified = f"{parent}.{name}" if parent else name
    text_parts = [signature]
    if parent:
        text_parts.append(f"Class: {parent}")
    if module:
        text_parts.append(f"Module: {module}")
    if section:
        text_parts.append(f"Section: {_section_label(section)}")

    return {
        "id": _make_sig_id(parent or name, name),
        "chunk_type": "signature",
        "section": _section_label(section),
        "name": name,
        "parent": parent,
        "module": module,
        "signature": signature,
        "text": " | ".join(text_parts),
        "embed_text": " | ".join(text_parts),
    }


def chunk_manim_kb(path: Path) -> list[dict]:
    """Split manim_kb.md into entry chunks and signature micro-chunks."""
    content = path.read_text(encoding="utf-8")
    chunks: list[dict] = []

    current_section = ""
    current_name = ""
    current_lines: list[str] = []

    def flush_entry() -> None:
        nonlocal current_name, current_lines
        if not current_name or not current_lines:
            return

        entry_text = "\n".join(current_lines).strip()
        module = _parse_module(entry_text)
        section_label = _section_label(current_section)

        chunks.append({
            "id": _make_entry_id(current_section, current_name),
            "chunk_type": "entry",
            "section": section_label,
            "name": current_name,
            "heading": f"### {current_name}",
            "module": module,
            "text": entry_text,
            "embed_text": _make_embed_text(current_name, module, entry_text),
        })

        chunks.extend(
            _extract_signatures(entry_text, current_section, current_name, module)
        )

        current_lines = []

    for line in content.splitlines():
        h2 = H2_RE.match(line)
        if h2:
            flush_entry()
            current_section = h2.group(1).strip()
            current_name = ""
            continue

        h3 = H3_RE.match(line)
        if h3:
            flush_entry()
            current_name = h3.group(1).strip()
            current_lines = []
            continue

        if current_name:
            current_lines.append(line)

    flush_entry()
    return chunks
