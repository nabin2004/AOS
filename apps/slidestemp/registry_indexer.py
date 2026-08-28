from __future__ import annotations

import json
from pathlib import Path
from aos_manim_core import PluginRegistry


def index_ecosystem() -> None:
    """Discovers all plugin.json manifests in the workspace and prints aggregated summary."""
    root = Path(__file__).parent
    registry = PluginRegistry.get_instance()
    discovered = registry.discover(root)

    print("=" * 60)
    print(f"AOS MANIM ECOSYSTEM: Discovered {len(discovered)} Plugin Manifests")
    print("=" * 60)

    for p in discovered:
        print(f"\n* {p.plugin} (v{p.version})")
        print(f"   Layer: {p.layer} | Domain: {p.domain}")
        print(f"   Description: {p.description}")
        print(f"   Dependencies: {', '.join(p.dependencies)}")
        print(f"   Capabilities ({len(p.capabilities)}):")
        for cap in p.capabilities:
            print(f"     - [{cap.category}] {cap.name}: {cap.description}")
            print(f"       Backends: {', '.join(cap.backends)}")
            print(f"       Validators: {', '.join(cap.validators) if cap.validators else 'None'}")


if __name__ == "__main__":
    index_ecosystem()
