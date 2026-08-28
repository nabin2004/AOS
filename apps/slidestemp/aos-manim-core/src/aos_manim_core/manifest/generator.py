from __future__ import annotations

from typing import List, Optional
from .schema import PluginManifest, Capability


class ManifestBuilder:
    """Convenience builder to declaratively construct a PluginManifest."""

    def __init__(self, plugin: str, domain: str, layer: str, description: str, version: str = "0.1.0") -> None:
        self._manifest = PluginManifest(
            plugin=plugin,
            version=version,
            domain=domain,
            layer=layer,
            description=description,
            capabilities=[],
            dependencies=[],
        )

    def with_dependency(self, dep: str) -> ManifestBuilder:
        self._manifest.dependencies.append(dep)
        return self

    def add_capability(
        self,
        name: str,
        category: str,
        description: str,
        backends: Optional[List[str]] = None,
        mobjects: Optional[List[str]] = None,
        animations: Optional[List[str]] = None,
        validators: Optional[List[str]] = None,
        parameters: Optional[dict] = None,
        tags: Optional[List[str]] = None,
    ) -> ManifestBuilder:
        cap = Capability(
            name=name,
            category=category,
            description=description,
            backends=backends or [],
            mobjects=mobjects or [],
            animations=animations or [],
            validators=validators or [],
            parameters=parameters or {},
            tags=tags or [],
        )
        self._manifest.capabilities.append(cap)
        return self

    def build(self) -> PluginManifest:
        return self._manifest
