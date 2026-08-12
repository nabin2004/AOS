# Dive into Deep Learning visualizers for Manim (`manim-ai`)

```python
from manim_ai import get_concept, list_concepts, LinearLayer, Network
from manim_ai import reveal_with_bookmarks  # VoiceoverScene helper

viz = get_concept("self_attention").build(tokens=["I", "love", "AI"])
print([c.id for c in list_concepts(domain="transformer")])
```

Install (agents env): editable via `apps/agents/pyproject.toml` → `manim-ai`.

**Full developer notes** (all plugins, how I extend them, agents + SFT):  
[MANIM_PLUGINS.md](../../../docs/MANIM_PLUGINS.md)
