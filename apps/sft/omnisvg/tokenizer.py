"""OmniSVG Linear Tokenizer Module.

Normalizes canvas viewbox to (200x200), flattens 2D coordinates (x, y) into 1D tokens:
token_id = x * w + y, and wraps sequences with special control tokens (<SOP>, <EOS>).
"""

from __future__ import annotations

from typing import List, Tuple, Dict
from .svg_simplifier import SVGPathCommand


class OmniSVGTokenizer:
    SOP = "<SOP>"  # Start of Path
    EOP = "<EOP>"  # End of Path
    EOS = "<EOS>"  # End of SVG
    FILL = "<FILL>"

    def __init__(self, canvas_width: int = 200, canvas_height: int = 200):
        self.w = canvas_width
        self.h = canvas_height
        
        # Build vocabulary
        self.special_tokens = [self.SOP, self.EOP, self.EOS, self.FILL, "M", "L", "C", "A", "Z"]
        self.coord_vocab_size = self.w * self.h
        
        self.token_to_id: Dict[str, int] = {}
        self.id_to_token: Dict[int, str] = {}
        
        idx = 0
        for st in self.special_tokens:
            self.token_to_id[st] = idx
            self.id_to_token[idx] = st
            idx += 1
            
        self.coord_offset = idx
        # Map 1D coordinate integers to token strings (e.g. "<C_452>")
        for c in range(self.coord_vocab_size):
            token_str = f"<C_{c}>"
            self.token_to_id[token_str] = self.coord_offset + c
            self.id_to_token[self.coord_offset + c] = token_str

    def coord_2d_to_1d(self, x: float, y: float) -> int:
        """Convert 2D (x, y) coordinate within viewbox into 1D index."""
        x_norm = max(0, min(self.w - 1, int(round(x))))
        y_norm = max(0, min(self.h - 1, int(round(y))))
        return x_norm * self.w + y_norm

    def coord_1d_to_2d(self, token_idx: int) -> Tuple[float, float]:
        """Convert 1D index back to 2D (x, y) coordinates."""
        x = token_idx // self.w
        y = token_idx % self.w
        return float(x), float(y)

    def encode(self, commands: List[SVGPathCommand]) -> List[str]:
        """Encode a list of SVGPathCommands into token strings."""
        tokens: List[str] = [self.SOP]

        for cmd in commands:
            if cmd.cmd == "F":
                tokens.append(self.FILL)
                if cmd.fill_color:
                    tokens.append(cmd.fill_color)
                continue

            tokens.append(cmd.cmd)
            # Encode coordinates in pairs (x, y)
            for i in range(0, len(cmd.args) - 1, 2):
                x, y = cmd.args[i], cmd.args[i + 1]
                coord_1d = self.coord_2d_to_1d(x, y)
                tokens.append(f"<C_{coord_1d}>")

        tokens.append(self.EOP)
        tokens.append(self.EOS)
        return tokens

    def decode(self, tokens: List[str]) -> List[SVGPathCommand]:
        """Decode token strings back into a list of SVGPathCommands."""
        commands: List[SVGPathCommand] = []
        current_cmd: str = ""
        current_args: List[float] = []

        for token in tokens:
            if token in (self.SOP, self.EOS, self.EOP):
                if current_cmd:
                    commands.append(SVGPathCommand(cmd=current_cmd, args=current_args))
                    current_cmd = ""
                    current_args = []
                continue

            if token in ("M", "L", "C", "A", "Z"):
                if current_cmd:
                    commands.append(SVGPathCommand(cmd=current_cmd, args=current_args))
                    current_args = []
                current_cmd = token
            elif token.startswith("<C_") and token.endswith(">"):
                coord_idx = int(token[3:-1])
                x, y = self.coord_1d_to_2d(coord_idx)
                current_args.extend([x, y])

        if current_cmd:
            commands.append(SVGPathCommand(cmd=current_cmd, args=current_args))

        return commands
