from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .model import (
    AnimationSlot,
    Callout,
    CodeBlock,
    DiagramRef,
    Equation,
    Heading,
    ImageBlock,
    ListBlock,
    Paragraph,
    Presentation,
    SlideSpec,
)


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
SLIDE_SPLIT_RE = re.compile(r"\n---\s*\n")
FENCE_RE = re.compile(r"^```([^\n]*)\n(.*?)^```\s*$", re.DOTALL | re.MULTILINE)
COLON_FENCE_RE = re.compile(r"^:::([^\n]*)\n(.*?)^:::\s*$", re.DOTALL | re.MULTILINE)
IMAGE_RE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
CALL_RE = re.compile(r"^([A-Za-z_][\w]*)\s*(?:\((.*)\))?\s*$")


def parse_simple_yaml(text: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if ":" not in stripped:
            i += 1
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value in ("|", ">"):
            base_indent = len(line) - len(line.lstrip(" "))
            i += 1
            block_lines: List[str] = []
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() == "":
                    block_lines.append("")
                    i += 1
                    continue
                nxt_indent = len(nxt) - len(nxt.lstrip(" "))
                if nxt_indent <= base_indent:
                    break
                block_lines.append(nxt)
                i += 1
            if block_lines:
                indents = [len(ln) - len(ln.lstrip(" ")) for ln in block_lines if ln.strip()]
                pad = min(indents) if indents else 0
                data[key] = "\n".join(ln[pad:] if len(ln) >= pad else ln for ln in block_lines).strip("\n")
            else:
                data[key] = ""
            continue
        data[key] = _parse_scalar(value)
        i += 1
    return data


def _parse_scalar(value: str) -> Any:
    if not value:
        return ""
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    lower = value.lower()
    if lower in ("true", "yes"):
        return True
    if lower in ("false", "no"):
        return False
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _parse_call(source: str) -> Tuple[str, Dict[str, Any]]:
    text = source.strip().splitlines()[0].strip() if source.strip() else ""
    match = CALL_RE.match(text)
    if not match:
        return text or "unknown", {}
    name = match.group(1)
    raw_args = match.group(2) or ""
    kwargs: Dict[str, Any] = {}
    if raw_args.strip():
        for part in _split_args(raw_args):
            if "=" in part:
                k, v = part.split("=", 1)
                kwargs[k.strip()] = _parse_scalar(v.strip())
            else:
                kwargs.setdefault("f", _parse_scalar(part))
    extra_lines = source.strip().splitlines()[1:]
    if extra_lines:
        kwargs["body"] = "\n".join(extra_lines)
    return name, kwargs


def _split_args(raw: str) -> List[str]:
    parts: List[str] = []
    buf: List[str] = []
    depth = 0
    for ch in raw:
        if ch in "([{":
            depth += 1
            buf.append(ch)
        elif ch in ")]}":
            depth = max(depth - 1, 0)
            buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return [p for p in parts if p]


def _spec_from_meta(meta: Dict[str, Any]) -> SlideSpec:
    layout = str(meta.get("layout") or "title-content")
    spec = SlideSpec(
        title=meta.get("title"),
        subtitle=meta.get("subtitle"),
        layout=layout,
        footer=meta.get("footer"),
        author=meta.get("author"),
        date=str(meta.get("date")) if meta.get("date") is not None else None,
        affiliation=meta.get("affiliation"),
        section_number=meta.get("section_number"),
        voiceover=str(meta["voiceover"]) if meta.get("voiceover") not in (None, "") else None,
    )
    if meta.get("ratios"):
        raw = meta["ratios"]
        if isinstance(raw, str):
            spec.ratios = [float(x) for x in raw.strip("[]").split(",") if x.strip()]
    return spec


def parse_slide_markdown(text: str, default_meta: Optional[Dict[str, Any]] = None) -> SlideSpec:
    body = text
    meta: Dict[str, Any] = dict(default_meta or {})
    fm = FRONTMATTER_RE.match(text)
    if fm:
        meta.update(parse_simple_yaml(fm.group(1)))
        body = text[fm.end() :]
    spec = _spec_from_meta(meta)
    spec.blocks = _parse_body(body, spec)
    if spec.title is None:
        for block in spec.blocks:
            if isinstance(block, Heading) and block.level == 1:
                spec.title = block.text
                spec.blocks.remove(block)
                break
    return spec


def _parse_body(body: str, spec: SlideSpec) -> list:
    blocks: list = []
    # Extract fenced regions first by replacing with placeholders? Sequential scan is clearer.
    lines = body.replace("\r\n", "\n").split("\n")
    i = 0
    para_buf: List[str] = []
    list_items: List[str] = []

    def flush_para() -> None:
        nonlocal para_buf
        text = " ".join(line.strip() for line in para_buf).strip()
        para_buf = []
        if text:
            blocks.append(Paragraph(text=text))

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            blocks.append(ListBlock(items=list(list_items)))
            list_items = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_para()
            flush_list()
            lang = stripped[3:].strip()
            i += 1
            fence_lines: List[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                fence_lines.append(lines[i])
                i += 1
            i += 1
            content = "\n".join(fence_lines).strip("\n")
            if lang in ("diagram", "aos-diagram"):
                name, kwargs = _parse_call(content)
                blocks.append(DiagramRef(name=name, kwargs=kwargs))
            elif lang in ("animation", "aos-animation"):
                name, kwargs = _parse_call(content)
                blocks.append(AnimationSlot(name=name, kwargs=kwargs))
            else:
                blocks.append(CodeBlock(code=content, language=lang or "python"))
            continue

        if stripped.startswith(":::"):
            flush_para()
            flush_list()
            kind = stripped[3:].strip()
            i += 1
            inner: List[str] = []
            while i < len(lines) and not lines[i].strip().startswith(":::"):
                inner.append(lines[i])
                i += 1
            i += 1
            inner_text = "\n".join(inner).strip()
            if kind.startswith("diagram"):
                payload = kind[len("diagram") :].strip() + ("\n" + inner_text if inner_text else "")
                name, kwargs = _parse_call(payload.strip() or inner_text)
                blocks.append(DiagramRef(name=name, kwargs=kwargs))
            elif kind.startswith("animation"):
                payload = kind[len("animation") :].strip() + ("\n" + inner_text if inner_text else "")
                name, kwargs = _parse_call(payload.strip() or inner_text)
                blocks.append(AnimationSlot(name=name, kwargs=kwargs))
            elif kind.startswith("callout"):
                title = "Note"
                body_text = inner_text
                if inner and ":" in inner[0] and not inner[0].startswith(" "):
                    maybe = parse_simple_yaml(inner_text)
                    if "title" in maybe or "body" in maybe:
                        title = str(maybe.get("title", "Note"))
                        body_text = str(maybe.get("body", "") or inner_text)
                blocks.append(Callout(title=title, body=body_text))
            else:
                blocks.append(Paragraph(text=inner_text))
            continue

        if stripped.startswith("$$"):
            flush_para()
            flush_list()
            if stripped.count("$$") >= 2 and len(stripped) > 2:
                latex = stripped.strip("$").strip()
                blocks.append(Equation(latex=latex))
                i += 1
                continue
            i += 1
            math_lines: List[str] = []
            while i < len(lines) and "$$" not in lines[i]:
                math_lines.append(lines[i])
                i += 1
            if i < len(lines):
                before, _, after = lines[i].partition("$$")
                if before.strip():
                    math_lines.append(before)
                i += 1
            blocks.append(Equation(latex="\n".join(math_lines).strip()))
            continue

        heading = HEADING_RE.match(stripped)
        if heading:
            flush_para()
            flush_list()
            level = len(heading.group(1))
            text = heading.group(2).strip()
            if level == 1:
                if spec.title is None:
                    spec.title = text
            else:
                blocks.append(Heading(text=text, level=level))
            i += 1
            continue

        img = IMAGE_RE.match(stripped)
        if img:
            flush_para()
            flush_list()
            blocks.append(ImageBlock(path=img.group(2), caption=img.group(1)))
            i += 1
            continue

        if stripped.startswith(">"):
            flush_para()
            flush_list()
            quote_lines = [stripped.lstrip("> ").strip()]
            i += 1
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip().lstrip("> ").strip())
                i += 1
            quote = " ".join(quote_lines).strip()
            blocks.append(Callout(title="Note", body=quote))
            continue

        if stripped.startswith(("- ", "* ", "+ ")) or re.match(r"^\d+\.\s+", stripped):
            flush_para()
            item = re.sub(r"^(?:[-*+]|\d+\.)\s+", "", stripped)
            list_items.append(item)
            i += 1
            continue

        if not stripped:
            flush_para()
            flush_list()
            i += 1
            continue

        if list_items:
            flush_list()
        para_buf.append(stripped)
        i += 1

    flush_para()
    flush_list()
    return blocks


def _closing_yaml_index(lines: List[str], open_idx: int) -> Optional[int]:
    j = open_idx + 1
    while j < len(lines) and lines[j].strip() != "---":
        stripped = lines[j].strip()
        if stripped.startswith("```"):
            return None
        if stripped and not stripped.startswith("#") and ":" not in stripped:
            if not (lines[j].startswith(" ") or lines[j].startswith("\t")):
                return None
        j += 1
    if j >= len(lines):
        return None
    return j


def _is_frontmatter_open(lines: List[str], i: int) -> bool:
    if lines[i].strip() != "---":
        return False
    close = _closing_yaml_index(lines, i)
    if close is None:
        return False
    body_ok = True
    for ln in lines[i + 1 : close]:
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if ":" in s or ln.startswith(" ") or ln.startswith("\t"):
            continue
        body_ok = False
        break
    return True if close == i + 1 else body_ok


def _split_deck_chunks(source: str) -> List[str]:
    lines = source.replace("\r\n", "\n").split("\n")
    n = len(lines)
    starts: List[int] = []
    in_fence = False
    i = 0
    while i < n:
        if lines[i].strip().startswith("```"):
            in_fence = not in_fence
            i += 1
            continue
        if not in_fence and _is_frontmatter_open(lines, i):
            starts.append(i)
            close = _closing_yaml_index(lines, i)
            i = (close + 1) if close is not None else i + 1
            continue
        i += 1
    if not starts:
        return [source.strip()] if source.strip() else []
    if starts[0] != 0:
        preamble = "\n".join(lines[: starts[0]]).strip()
        chunks = [preamble] if preamble else []
    else:
        chunks = []
    for k, start in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else n
        chunk = "\n".join(lines[start:end]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def parse_markdown(text: str) -> Presentation:
    """Parse a Marp-like markdown deck into a Presentation AST."""
    source = text.replace("\r\n", "\n").strip() + "\n"
    chunks = _split_deck_chunks(source)
    default_meta: Dict[str, Any] = {}
    slides: List[SlideSpec] = []

    for chunk in chunks:
        fm = FRONTMATTER_RE.match(chunk + "\n")
        meta = parse_simple_yaml(fm.group(1)) if fm else {}
        body = chunk[fm.end() :].strip() if fm else chunk
        slide_keys = {"layout", "title", "subtitle", "author", "affiliation", "section_number", "date", "voiceover"}
        is_global_only = fm and not body and not (slide_keys & set(meta.keys()))
        if is_global_only:
            default_meta.update(meta)
            continue
        merged = dict(default_meta)
        merged.update(meta)
        slides.append(parse_slide_markdown(chunk, default_meta=merged))

    if not slides:
        slides.append(parse_slide_markdown(source))

    title = default_meta.get("title")
    if title is None and slides and slides[0].title:
        title = slides[0].title
    return Presentation(title=title, slides=slides, footer=default_meta.get("footer"))
