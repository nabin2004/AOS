"""Layout generator for translating layout specs into Manim code expressions."""

from __future__ import annotations

from motiongram.manimgram.schema import LayoutSpec


def _format_coord_list(coords: list[float]) -> str:
    parts = [str(int(c)) if isinstance(c, (int, float)) and c == int(c) else str(c) for c in coords]
    return f"[{', '.join(parts)}]"


def render_layout_statements(mob_id: str, layout: LayoutSpec | None) -> list[str]:
    """Generate Manim positioning and alignment statements for a mobject."""
    if layout is None:
        return []

    stmts: list[str] = []

    # 1. Base scale if specified before positioning
    if layout.scale is not None:
        stmts.append(f"{mob_id}.scale({layout.scale})")

    # 2. Centering or explicit move_to
    if layout.center:
        stmts.append(f"{mob_id}.center()")
    elif layout.move_to is not None:
        if isinstance(layout.move_to, list):
            stmts.append(f"{mob_id}.move_to(np.array({_format_coord_list(layout.move_to)}))")
        elif isinstance(layout.move_to, str):
            stmts.append(f"{mob_id}.move_to({layout.move_to})")

    # 3. next_to constraint
    if layout.next_to is not None:
        tgt = layout.next_to.target
        direction = layout.next_to.direction
        buff = layout.next_to.buff
        aligned_edge = layout.next_to.aligned_edge
        edge_param = f", aligned_edge={aligned_edge}" if aligned_edge else ""
        stmts.append(f"{mob_id}.next_to({tgt}, {direction}, buff={buff}{edge_param})")

    # 4. to_edge constraint
    if layout.to_edge is not None:
        edge = layout.to_edge.edge
        buff = layout.to_edge.buff
        stmts.append(f"{mob_id}.to_edge({edge}, buff={buff})")

    # 5. to_corner constraint
    if layout.to_corner is not None:
        corner = layout.to_corner.corner
        buff = layout.to_corner.buff
        stmts.append(f"{mob_id}.to_corner({corner}, buff={buff})")

    # 6. align_to constraint
    if layout.align_to is not None:
        tgt = layout.align_to.target
        direction = layout.align_to.direction
        stmts.append(f"{mob_id}.align_to({tgt}, {direction})")

    # 7. shift offset (applied relative to positioned location)
    if layout.shift is not None:
        stmts.append(f"{mob_id}.shift(np.array({_format_coord_list(layout.shift)}))")

    return stmts
