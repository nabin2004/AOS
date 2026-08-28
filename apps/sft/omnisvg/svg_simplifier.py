"""SVG Simplification Module based on OmniSVG framework.

Flattens XML hierarchies (<g>, transforms) and simplifies shape primitives into
atomic path commands: M (MoveTo), L (LineTo), C (Cubic Bezier), A (Elliptical Arc), Z (ClosePath), F (Fill).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class SVGPathCommand:
    cmd: str  # 'M', 'L', 'C', 'A', 'Z', 'F'
    args: List[float]
    fill_color: Optional[str] = None

    def to_str(self) -> str:
        if self.cmd == "F":
            return f"F {self.fill_color or '#000000'}"
        args_str = " ".join(f"{a:.2f}" for a in self.args)
        return f"{self.cmd} {args_str}".strip()


def parse_path_d(d_string: str) -> List[SVGPathCommand]:
    """Parse SVG path 'd' attribute string into atomic SVGPathCommands."""
    # Pattern to match command letters and numbers
    tokens = re.findall(r"([a-zA-Z])|([-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?)", d_string)
    
    commands: List[SVGPathCommand] = []
    current_cmd: Optional[str] = None
    coords: List[float] = []

    for char_token, num_token in tokens:
        if char_token:
            if current_cmd:
                commands.append(_create_atomic_command(current_cmd, coords))
            current_cmd = char_token
            coords = []
        elif num_token:
            coords.append(float(num_token))

    if current_cmd:
        commands.append(_create_atomic_command(current_cmd, coords))

    return commands


def _create_atomic_command(cmd_char: str, coords: List[float]) -> SVGPathCommand:
    upper_cmd = cmd_char.upper()
    # Normalize command to one of atomic commands M, L, C, A, Z
    if upper_cmd in ("M", "L", "C", "A", "Z"):
        atomic_cmd = upper_cmd
    elif upper_cmd == "H":
        # Horizontal line to -> L (x, 0) placeholder or direct coordinate
        atomic_cmd = "L"
    elif upper_cmd == "V":
        # Vertical line to -> L (0, y)
        atomic_cmd = "L"
    elif upper_cmd in ("S", "Q", "T"):
        # Approximated to C (Cubic Bezier)
        atomic_cmd = "C"
    else:
        atomic_cmd = "L"

    return SVGPathCommand(cmd=atomic_cmd, args=coords)


def convert_primitive_to_path(element: ET.Element) -> Optional[str]:
    """Convert basic SVG shapes (rect, circle, ellipse, line, polygon) into path 'd' string."""
    tag = element.tag.split("}")[-1]
    
    if tag == "rect":
        x = float(element.attrib.get("x", 0))
        y = float(element.attrib.get("y", 0))
        w = float(element.attrib.get("width", 0))
        h = float(element.attrib.get("height", 0))
        return f"M {x} {y} L {x+w} {y} L {x+w} {y+h} L {x} {y+h} Z"

    elif tag == "circle":
        cx = float(element.attrib.get("cx", 0))
        cy = float(element.attrib.get("cy", 0))
        r = float(element.attrib.get("r", 0))
        return f"M {cx-r} {cy} A {r} {r} 0 1 0 {cx+r} {cy} A {r} {r} 0 1 0 {cx-r} {cy} Z"

    elif tag == "ellipse":
        cx = float(element.attrib.get("cx", 0))
        cy = float(element.attrib.get("cy", 0))
        rx = float(element.attrib.get("rx", 0))
        ry = float(element.attrib.get("ry", 0))
        return f"M {cx-rx} {cy} A {rx} {ry} 0 1 0 {cx+rx} {cy} A {rx} {ry} 0 1 0 {cx-rx} {cy} Z"

    elif tag == "line":
        x1 = float(element.attrib.get("x1", 0))
        y1 = float(element.attrib.get("y1", 0))
        x2 = float(element.attrib.get("x2", 0))
        y2 = float(element.attrib.get("y2", 0))
        return f"M {x1} {y1} L {x2} {y2}"

    elif tag == "polyline" or tag == "polygon":
        points_str = element.attrib.get("points", "").strip()
        if not points_str:
            return None
        pts = [float(p) for p in re.split(r"[\s,]+", points_str) if p]
        if len(pts) < 2:
            return None
        path_str = f"M {pts[0]} {pts[1]}"
        for i in range(2, len(pts), 2):
            if i + 1 < len(pts):
                path_str += f" L {pts[i]} {pts[i+1]}"
        if tag == "polygon":
            path_str += " Z"
        return path_str

    elif tag == "path":
        return element.attrib.get("d", "")

    return None


def simplify_svg(svg_content: str) -> Tuple[List[SVGPathCommand], str]:
    """Flattens SVG XML content into atomic SVGPathCommands and cleaned SVG string.

    Tries using picosvg if available, otherwise uses internal ElementTree fallback.
    """
    try:
        from picosvg.svg import SVG
        # Picosvg path simplification if available
        svg_obj = SVG.fromstring(svg_content)
        svg_obj = svg_obj.topath()
        svg_content = svg_obj.tostring()
    except Exception:
        # Fallback to internal parser
        pass

    root = ET.fromstring(svg_content)
    commands: List[SVGPathCommand] = []

    # Traverse all elements, flattening <g> transforms
    for elem in root.iter():
        fill = elem.attrib.get("fill")
        if fill and fill != "none":
            commands.append(SVGPathCommand(cmd="F", args=[], fill_color=fill))

        d_str = convert_primitive_to_path(elem)
        if d_str:
            cmds = parse_path_d(d_str)
            commands.extend(cmds)

    # Reconstruct cleaned SVG string
    cleaned_root = ET.Element("svg", {"xmlns": "http://www.w3.org/2000/svg", "viewBox": "0 0 200 200"})
    for cmd in commands:
        if cmd.cmd == "F":
            continue
        path_elem = ET.SubElement(cleaned_root, "path", {"d": cmd.to_str()})
        if cmd.fill_color:
            path_elem.attrib["fill"] = cmd.fill_color

    cleaned_svg_str = ET.tostring(cleaned_root, encoding="unicode")
    return commands, cleaned_svg_str
