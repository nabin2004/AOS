from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional
from ..manifest.schema import PluginManifest, Capability


class PluginRegistry:
    """Central discovery and registry service for all AOS Manim plugins."""
    _instance: Optional[PluginRegistry] = None

    def __init__(self) -> None:
        self._plugins: Dict[str, PluginManifest] = {}

    @classmethod
    def get_instance(cls) -> PluginRegistry:
        if cls._instance is None:
            cls._instance = PluginRegistry()
        return cls._instance

    def register(self, manifest: PluginManifest) -> None:
        self._plugins[manifest.plugin] = manifest

    def unregister(self, plugin_name: str) -> None:
        self._plugins.pop(plugin_name, None)

    def get_plugin(self, name: str) -> Optional[PluginManifest]:
        return self._plugins.get(name)

    def list_plugins(self) -> List[PluginManifest]:
        return list(self._plugins.values())

    def find_capabilities(
        self,
        domain: Optional[str] = None,
        category: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[Capability]:
        results: List[Capability] = []
        for plugin in self._plugins.values():
            if domain and plugin.domain.lower() != domain.lower():
                continue
            for cap in plugin.capabilities:
                if category and cap.category.lower() != category.lower():
                    continue
                if tag and tag.lower() not in [t.lower() for t in cap.tags]:
                    continue
                results.append(cap)
        return results

    def discover(self, root_dir: Path | str) -> List[PluginManifest]:
        """Scan directory tree for plugin.json manifests and register them."""
        discovered: List[PluginManifest] = []
        root = Path(root_dir)
        if not root.exists():
            return discovered

        for json_path in root.glob("**/plugin.json"):
            try:
                manifest = PluginManifest.from_file(json_path)
                self.register(manifest)
                discovered.append(manifest)
            except Exception:
                continue

        return discovered


# Convenience helper functions
def register_plugin(manifest: PluginManifest) -> None:
    PluginRegistry.get_instance().register(manifest)


def get_plugin_registry() -> PluginRegistry:
    return PluginRegistry.get_instance()
