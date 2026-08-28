from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from aos_manim_core import (
    Cue,
    CueAction,
    CueResolver,
    NarrationScript,
    bind_authored_script,
    is_cueable,
)

from .document.model import (
    AnimationSlot,
    Callout,
    CodeBlock,
    ContentBlock,
    DiagramRef,
    Equation,
    Heading,
    ImageBlock,
    ListBlock,
    Paragraph,
    SlideSpec,
)
from .layout.box import LayoutNode


def assign_content_ids(spec: SlideSpec) -> None:
    """Fill missing block / list-item ids used as cue targets."""
    counts: Dict[str, int] = {}

    def next_id(prefix: str) -> str:
        n = counts.get(prefix, 0)
        counts[prefix] = n + 1
        return f"{prefix}{n}"

    def visit(block: ContentBlock) -> None:
        if isinstance(block, Paragraph):
            block.id = block.id or next_id("p")
        elif isinstance(block, Heading):
            block.id = block.id or next_id("h")
        elif isinstance(block, Equation):
            block.id = block.id or next_id("eq")
        elif isinstance(block, ListBlock):
            block.id = block.id or next_id("l")
            if not block.item_ids or len(block.item_ids) != len(block.items):
                block.item_ids = [next_id("li") for _ in block.items]
        elif isinstance(block, Callout):
            block.id = block.id or next_id("c")
        elif isinstance(block, CodeBlock):
            block.id = block.id or next_id("code")
        elif isinstance(block, DiagramRef):
            block.id = block.id or next_id("d")
        elif isinstance(block, AnimationSlot):
            block.id = block.id or next_id("anim")
        elif isinstance(block, ImageBlock):
            block.id = block.id or next_id("img")
        else:
            if getattr(block, "id", None) is None:
                block.id = next_id("b")

    for block in spec.all_blocks():
        visit(block)


def spoken_for_block(block: ContentBlock) -> List[Tuple[str, str, CueAction, Dict[str, Any]]]:
    """Return (target_id, spoken_fragment, action, payload) rows for auto-scripts."""
    rows: List[Tuple[str, str, CueAction, Dict[str, Any]]] = []
    if isinstance(block, Paragraph) and block.id:
        rows.append((block.id, block.text, CueAction.REVEAL, {}))
    elif isinstance(block, Heading) and block.id:
        rows.append((block.id, block.text, CueAction.REVEAL, {}))
    elif isinstance(block, Equation) and block.id:
        rows.append((block.id, "the equation", CueAction.REVEAL, {}))
    elif isinstance(block, ListBlock):
        for item, iid in zip(block.items, block.item_ids):
            rows.append((iid, item, CueAction.REVEAL, {}))
    elif isinstance(block, Callout) and block.id:
        spoken = f"{block.title}. {block.body}".strip()
        rows.append((block.id, spoken, CueAction.REVEAL, {}))
    elif isinstance(block, CodeBlock) and block.id:
        rows.append((block.id, "this code", CueAction.REVEAL, {}))
    elif isinstance(block, DiagramRef) and block.id:
        name = block.name.replace("_", " ")
        rows.append((block.id, f"watch the {name} diagram", CueAction.REVEAL, {}))
    elif isinstance(block, AnimationSlot) and block.id:
        name = block.name.replace("_", " ")
        rows.append((block.id, f"watch the {name} animation", CueAction.PLAY, {}))
    elif isinstance(block, ImageBlock) and block.id:
        rows.append((block.id, block.caption or "this figure", CueAction.REVEAL, {}))
    return rows


def auto_cues_from_spec(spec: SlideSpec) -> List[Cue]:
    assign_content_ids(spec)
    cues: List[Cue] = []
    if spec.layout == "title":
        cues.append(Cue(mark="title", target_id="title", action=CueAction.REVEAL, payload={"draw": True}))
        if spec.subtitle:
            cues.append(Cue(mark="subtitle", target_id="subtitle", action=CueAction.REVEAL, payload={"draw": True}))
        cues.append(Cue(mark="meta", target_id="meta", action=CueAction.REVEAL, payload={"draw": True}))
    elif spec.layout == "section":
        cues.append(Cue(mark="section", target_id="section", action=CueAction.REVEAL, payload={"draw": True}))
    else:
        for block in spec.all_blocks():
            for target_id, _spoken, action, payload in spoken_for_block(block):
                cues.append(Cue(mark=target_id, target_id=target_id, action=action, payload=payload))
    return cues


def append_step_cues(cues: List[Cue], cueables: Dict[str, Any]) -> List[Cue]:
    extra: List[Cue] = []
    existing = {c.mark for c in cues}
    for cid, obj in cueables.items():
        n = int(getattr(obj, "step_count", lambda: 0)())
        if n <= 0:
            continue
        for i in range(n):
            mark = f"{cid}s{i}"
            if mark in existing:
                continue
            extra.append(
                Cue(mark=mark, target_id=cid, action=CueAction.STEP, payload={"i": i})
            )
    return cues + extra


def auto_script_from_spec(spec: SlideSpec, cueables: Optional[Dict[str, Any]] = None) -> NarrationScript:
    assign_content_ids(spec)
    parts: List[str] = []
    cues: List[Cue] = []
    if spec.layout == "title":
        cue1 = Cue(mark="title", target_id="title", action=CueAction.REVEAL, payload={"draw": True})
        cues.append(cue1)
        parts.append(f"<bookmark mark='title'/>{spec.title or 'Title'}.")
        if spec.subtitle:
            cue_sub = Cue(mark="subtitle", target_id="subtitle", action=CueAction.REVEAL, payload={"draw": True})
            cues.append(cue_sub)
            parts.append(f" <bookmark mark='subtitle'/>{spec.subtitle}.")
        cue2 = Cue(mark="meta", target_id="meta", action=CueAction.REVEAL, payload={"draw": True})
        cues.append(cue2)
        meta_str = ", ".join(x for x in (spec.author, spec.affiliation, spec.date) if x) or "Introduction"
        parts.append(f" <bookmark mark='meta'/>{meta_str}.")
    elif spec.layout == "section":
        cue = Cue(mark="section", target_id="section", action=CueAction.REVEAL, payload={"draw": True})
        cues.append(cue)
        parts.append(f"<bookmark mark='section'/>Section {spec.section_number or ''}: {spec.title or ''}.")
    else:
        for block in spec.all_blocks():
            for target_id, spoken, action, payload in spoken_for_block(block):
                cue = Cue(mark=target_id, target_id=target_id, action=action, payload=payload)
                cues.append(cue)
                fragment = spoken.strip() or target_id
                parts.append(f"<bookmark mark='{cue.mark}'/>{fragment}.")
    cues = append_step_cues(cues, cueables or {})
    for cue in cues:
        if cue.action == CueAction.STEP:
            i = int(cue.payload.get("i", 0)) + 1
            parts.append(f" <bookmark mark='{cue.mark}'/>Step {i}.")
    return NarrationScript(text=" ".join(parts).strip(), cues=cues)


def script_for_slide(spec: SlideSpec, cueables: Optional[Dict[str, Any]] = None) -> NarrationScript:
    auto = auto_cues_from_spec(spec)
    auto = append_step_cues(auto, cueables or {})
    voiceover_text = spec.total_bookmark_for_this_slide or spec.total_this_slide_bookmark or spec.voiceover or ""
    if spec.cues:
        return bind_authored_script(voiceover_text, auto, spec.cues)
    if voiceover_text:
        return bind_authored_script(voiceover_text, auto, None)
    return auto_script_from_spec(spec, cueables)


def collect_cue_index(node: LayoutNode) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    targets: Dict[str, Any] = {}
    cueables: Dict[str, Any] = {}

    def walk(n: LayoutNode) -> None:
        mob = n.mobject
        cid = getattr(n, "cue_id", None)
        if cid and mob is not None:
            targets[cid] = mob
            if is_cueable(mob):
                cueables[cid] = mob
                for key, child in mob.cue_targets().items():
                    if key:
                        targets[f"{cid}.{key}"] = child
        for child_node in n.children():
            walk(child_node)

    walk(node)
    return targets, cueables


def hide_lecture_body(slide: Any) -> None:
    cueables = getattr(slide, "cueables", {}) or {}
    cue_index = getattr(slide, "cue_index", {}) or {}
    hidden_ids = set()
    for cid, obj in cueables.items():
        for mob in obj.cue_targets().values():
            if hasattr(mob, "set_opacity"):
                mob.set_opacity(0)
        hidden_ids.add(cid)
    for cid, mob in cue_index.items():
        if cid in hidden_ids or "." in cid:
            continue
        if cid in cueables:
            continue
        if hasattr(mob, "set_opacity"):
            mob.set_opacity(0)
