"""Unit tests for SVG Simplifier module."""

from omnisvg.svg_simplifier import simplify_svg, parse_path_d, convert_primitive_to_path, SVGPathCommand
import xml.etree.ElementTree as ET


def test_parse_path_d():
    d = "M 10 20 L 30 40 C 50 60 70 80 90 100 Z"
    commands = parse_path_d(d)
    assert len(commands) == 4
    assert commands[0].cmd == "M"
    assert commands[0].args == [10.0, 20.0]
    assert commands[1].cmd == "L"
    assert commands[2].cmd == "C"
    assert commands[3].cmd == "Z"


def test_convert_primitive_rect():
    elem = ET.Element("rect", {"x": "10", "y": "20", "width": "50", "height": "60"})
    path_d = convert_primitive_to_path(elem)
    assert path_d == "M 10.0 20.0 L 60.0 20.0 L 60.0 80.0 L 10.0 80.0 Z"


def test_simplify_svg():
    svg_raw = '<svg><rect x="5" y="5" width="20" height="20" fill="#FF0000"/></svg>'
    commands, cleaned_svg = simplify_svg(svg_raw)
    assert len(commands) >= 1
    assert any(c.cmd == "F" and c.fill_color == "#FF0000" for c in commands)
    assert "<svg" in cleaned_svg
