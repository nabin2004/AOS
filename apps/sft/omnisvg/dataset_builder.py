"""OmniSVG Dataset Builder Module.

Handles SVG curation, deduplication, viewbox standardization (200x200),
CairoSVG rasterization, and image-text dataset pairing.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

from .svg_simplifier import simplify_svg
from .tokenizer import OmniSVGTokenizer


class OmniSVGDatasetBuilder:
    def __init__(self, output_dir: str = "omnisvg_dataset"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tokenizer = OmniSVGTokenizer(canvas_width=200, canvas_height=200)
        self.hashes: set[str] = set()

    def process_svg_file(self, svg_path: str, caption: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Process a single SVG file: simplify, compute hash, rasterize, and tokenize."""
        path = Path(svg_path)
        if not path.exists():
            return None

        raw_content = path.read_text(encoding="utf-8")
        
        # Deduplication check
        content_hash = hashlib.md5(raw_content.encode("utf-8")).hexdigest()
        if content_hash in self.hashes:
            return None
        self.hashes.add(content_hash)

        # Simplify SVG
        commands, cleaned_svg = simplify_svg(raw_content)
        if not commands:
            return None

        # Tokenize SVG
        tokens = self.tokenizer.encode(commands)

        # Optional CairoSVG rasterization
        raster_path = self.output_dir / f"{content_hash}.png"
        self._rasterize_svg(cleaned_svg, str(raster_path))

        entry = {
            "id": content_hash,
            "caption": caption or f"Vector graphic of {path.stem}",
            "tokens": tokens,
            "raw_svg": cleaned_svg,
            "image_path": str(raster_path),
        }

        return entry

    def _rasterize_svg(self, svg_content: str, output_image_path: str) -> bool:
        """Rasterize SVG to PNG file using cairosvg if installed, else fallback."""
        try:
            import cairosvg
            cairosvg.svg2png(bytestring=svg_content.encode("utf-8"), write_to=output_image_path)
            return True
        except Exception:
            # Fallback placeholder if cairosvg native libraries are missing
            try:
                from PIL import Image
                img = Image.new("RGB", (200, 200), color="white")
                img.save(output_image_path)
                return True
            except Exception:
                return False

    def build_dataset_manifest(self, svg_dir: str, manifest_filename: str = "dataset.jsonl") -> str:
        """Process all SVGs in directory and write JSONL training manifest."""
        manifest_path = self.output_dir / manifest_filename
        entries: List[Dict[str, Any]] = []

        svg_files = list(Path(svg_dir).glob("*.svg"))
        for svg_file in svg_files:
            item = self.process_svg_file(str(svg_file))
            if item:
                entries.append(item)

        with open(manifest_path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        return str(manifest_path)
