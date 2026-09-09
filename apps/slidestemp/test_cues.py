import sys
from pathlib import Path
sys.path.insert(0, str(Path("C:/Users/nabin/Desktop/myall/AOS/apps/slidestemp/aos-manim-slides/src")))
sys.path.insert(0, str(Path("C:/Users/nabin/Desktop/myall/AOS/apps/slidestemp/aos-manim-core/src")))
# Actually, let's just run from the slidestemp directory where it should be available via uv/PYTHONPATH.

from aos_manim_slides.document.model import Slide
from aos_manim_slides.narration import script_for_slide, auto_cues_from_spec

with open("agent_narration_demo.md", "r", encoding="utf-8") as f:
    md_content = f.read()

deck = list(Slide.deck_from_markdown(md_content))
slide = deck[0]

cues = auto_cues_from_spec(slide.spec)
print("Auto Cues:")
for c in cues:
    print(f"  {c.mark} -> {c.target_id}")

print("\nDefault Script:")
script = script_for_slide(slide.spec)
print(script.text)
print("Script Cues:")
for c in script.cues:
    print(f"  {c.mark} -> {c.target_id}")
