"""Selector registry and resolver for Manim submobjects."""

from __future__ import annotations

import re

# Embedded resolver code injected into emitted standalone Manim Python scripts
EMBEDDED_SELECTOR_RESOLVER_CODE = r'''
import re

def resolve_submobject(mob, selector: str):
    """Resolve semantic selector (e.g. entry[0,0], brackets, term[x]) on a Manim mobject."""
    if not selector or selector in ("self", "root", ""):
        return mob
    
    mob_type = type(mob).__name__
    
    # Direct index access: [0] or index[0]
    m_idx = re.match(r"^(?:index)?\[(\d+)\]$", selector)
    if m_idx:
        return mob[int(m_idx.group(1))]

    # Matrix family
    if "Matrix" in mob_type:
        m_entry = re.match(r"^entry\[(\d+),\s*(\d+)\]$", selector)
        if m_entry:
            r, c = int(m_entry.group(1)), int(m_entry.group(2))
            rows = mob.get_rows()
            if r < len(rows) and c < len(rows[r]):
                return rows[r][c]
            return mob.get_entries()[r * len(rows[0]) + c]
        
        m_row = re.match(r"^row\[(\d+)\]$", selector)
        if m_row:
            return mob.get_rows()[int(m_row.group(1))]
            
        m_col = re.match(r"^col\[(\d+)\]$", selector)
        if m_col:
            return mob.get_columns()[int(m_col.group(1))]
            
        if selector == "brackets":
            return mob.get_brackets()
        if selector in ("bracket.left", "left_bracket"):
            return mob.get_brackets()[0]
        if selector in ("bracket.right", "right_bracket"):
            return mob.get_brackets()[1]

    # MathTex family
    if "MathTex" in mob_type or "Tex" in mob_type:
        m_term = re.match(r"^term\[(.*?)\]$", selector)
        if m_term:
            tex_str = m_term.group(1)
            part = mob.get_part_by_tex(tex_str)
            if part is not None:
                return part
        m_part = re.match(r"^part\[(\d+)\]$", selector)
        if m_part:
            return mob[int(m_part.group(1))]

    # Axes family
    if "Axes" in mob_type:
        if selector in ("x_axis", "x"):
            return mob.x_axis
        if selector in ("y_axis", "y"):
            return mob.y_axis
        if selector in ("z_axis", "z") and hasattr(mob, "z_axis"):
            return mob.z_axis
        m_pt = re.match(r"^(?:point|c2p)\[([-\d\.]+),\s*([-\d\.]+)\]$", selector)
        if m_pt:
            x, y = float(m_pt.group(1)), float(m_pt.group(2))
            return mob.c2p(x, y)

    # Table family
    if "Table" in mob_type:
        m_cell = re.match(r"^cell\[(\d+),\s*(\d+)\]$", selector)
        if m_cell:
            r, c = int(m_cell.group(1)), int(m_cell.group(2))
            # Manim Table rows/cols are 1-indexed in get_cell
            return mob.get_cell((r + 1, c + 1))
        m_row = re.match(r"^row\[(\d+)\]$", selector)
        if m_row:
            return mob.get_rows()[int(m_row.group(1))]
        m_col = re.match(r"^col\[(\d+)\]$", selector)
        if m_col:
            return mob.get_columns()[int(m_col.group(1))]

    # Fallback to direct attribute if exists
    if hasattr(mob, selector):
        return getattr(mob, selector)

    return mob
'''


class SelectorRegistry:
    """Registry for validating and resolving semantic selectors."""

    @staticmethod
    def validate_selector_syntax(mobject_type: str, selector: str) -> bool:
        """Validate if a selector string has valid syntax for a given mobject type."""
        if not selector or selector in ("self", "root"):
            return True

        if re.match(r"^(?:index)?\[\d+\]$", selector):
            return True

        if "Matrix" in mobject_type:
            if re.match(r"^entry\[\d+,\s*\d+\]$", selector):
                return True
            if re.match(r"^(row|col)\[\d+\]$", selector):
                return True
            matrix_bracket_selectors = (
                "brackets",
                "bracket.left",
                "bracket.right",
                "left_bracket",
                "right_bracket",
            )
            if selector in matrix_bracket_selectors:
                return True

        if "MathTex" in mobject_type or "Tex" in mobject_type:
            if re.match(r"^term\[.*?\]$", selector):
                return True
            if re.match(r"^part\[\d+\]$", selector):
                return True

        if "Axes" in mobject_type:
            if selector in ("x_axis", "y_axis", "z_axis", "x", "y", "z"):
                return True
            if re.match(r"^(?:point|c2p)\[[-\d\.]+,\s*[-\d\.]+\]$", selector):
                return True

        if "Table" in mobject_type:
            if re.match(r"^cell\[\d+,\s*\d+\]$", selector):
                return True
            if re.match(r"^(row|col)\[\d+\]$", selector):
                return True

        # Generic attribute identifier
        return bool(re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", selector))
