"""Unit tests for OmniSVG Linear Tokenizer module."""

from omnisvg.tokenizer import OmniSVGTokenizer
from omnisvg.svg_simplifier import SVGPathCommand


def test_tokenizer_2d_1d_conversion():
    tokenizer = OmniSVGTokenizer(canvas_width=200, canvas_height=200)
    x, y = 50.0, 100.0
    idx_1d = tokenizer.coord_2d_to_1d(x, y)
    assert idx_1d == 50 * 200 + 100

    x_rec, y_rec = tokenizer.coord_1d_to_2d(idx_1d)
    assert x_rec == 50.0
    assert y_rec == 100.0


def test_tokenizer_encode_decode():
    tokenizer = OmniSVGTokenizer(canvas_width=200, canvas_height=200)
    commands = [
        SVGPathCommand(cmd="M", args=[10.0, 20.0]),
        SVGPathCommand(cmd="L", args=[30.0, 40.0]),
        SVGPathCommand(cmd="Z", args=[]),
    ]

    tokens = tokenizer.encode(commands)
    assert tokens[0] == "<SOP>"
    assert "<EOS>" in tokens
    assert "M" in tokens
    assert "L" in tokens
    assert "Z" in tokens

    decoded = tokenizer.decode(tokens)
    assert len(decoded) == 3
    assert decoded[0].cmd == "M"
    assert decoded[0].args == [10.0, 20.0]
    assert decoded[1].cmd == "L"
    assert decoded[1].args == [30.0, 40.0]
    assert decoded[2].cmd == "Z"
