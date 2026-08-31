"""PackageCrawler: Recursive introspection and extraction engine for scientific Python packages."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import types
from typing import Any, Dict, List, Optional, Set, Tuple

from aos_lkg.schema.nodes import (
    LibraryNode,
    ModuleNode,
    FunctionNode,
    ClassNode,
    NodeType,
)
from aos_lkg.schema.edges import Edge, EdgeType
from aos_lkg.schema.graph import KnowledgeGraph
from aos_lkg.extractor.inspector import (
    safe_signature,
    get_clean_docstring,
    is_compiled_object,
    safe_get_source,
)
from aos_lkg.extractor.doc_parser import parse_docstring
from aos_lkg.extractor.filters import (
    is_public_symbol,
    is_deprecated,
    get_canonical_module,
    should_skip_module,
)


class PackageCrawler:
    """Recursively crawls and extracts structured KnowledgeGraph data from Python libraries."""

    def __init__(
        self,
        max_depth: int = 4,
        include_submodules: bool = True,
        extract_sources: bool = False,
    ):
        self.max_depth = max_depth
        self.include_submodules = include_submodules
        self.extract_sources = extract_sources
        self.visited_modules: Set[str] = set()

    def crawl_package(
        self,
        package_name: str,
        target_submodules: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> KnowledgeGraph:
        """Crawl a package and return the extracted KnowledgeGraph."""
        kg = KnowledgeGraph()
        self.exclude_patterns = exclude_patterns or []

        try:
            pkg = importlib.import_module(package_name)
        except ImportError as e:
            # Package not installed or error importing
            return kg

        pkg_version = getattr(pkg, "__version__", None)
        pkg_file = getattr(pkg, "__file__", None)
        pkg_doc = get_clean_docstring(pkg)

        lib_node = LibraryNode(
            id=f"lib:{package_name}",
            name=package_name,
            version=str(pkg_version) if pkg_version else None,
            location=str(pkg_file) if pkg_file else None,
            description=pkg_doc[:300] if pkg_doc else None,
            docstring=pkg_doc,
        )
        kg.add_node(lib_node)

        # Determine target modules
        if target_submodules:
            # Crawl root package module and direct public symbols
            self._crawl_module_recursive(pkg, package_name, lib_node.id, kg, depth=0, recurse_submodules=False)
            for sub_name in target_submodules:
                full_mod_name = f"{package_name}.{sub_name}" if not sub_name.startswith(package_name) else sub_name
                try:
                    sub_mod = importlib.import_module(full_mod_name)
                    self._crawl_module_recursive(sub_mod, package_name, lib_node.id, kg, depth=1)
                except Exception:
                    continue
        else:
            self._crawl_module_recursive(pkg, package_name, lib_node.id, kg, depth=0)

        return kg

    def _crawl_module_recursive(
        self,
        mod: types.ModuleType,
        lib_name: str,
        parent_id: str,
        kg: KnowledgeGraph,
        depth: int,
        recurse_submodules: bool = True,
    ) -> None:
        mod_name = getattr(mod, "__name__", "")
        if not mod_name or mod_name in self.visited_modules:
            return

        if depth > self.max_depth or should_skip_module(mod_name):
            return

        if any(pat in mod_name for pat in getattr(self, "exclude_patterns", [])):
            return

        self.visited_modules.add(mod_name)

        mod_doc = get_clean_docstring(mod)
        mod_all = getattr(mod, "__all__", None)
        if mod_all is not None:
            try:
                mod_all = list(mod_all)
            except Exception:
                mod_all = None

        mod_node_id = f"mod:{mod_name}"
        mod_node = ModuleNode(
            id=mod_node_id,
            name=mod_name.split(".")[-1],
            library=lib_name,
            qualified_name=mod_name,
            docstring=mod_doc,
            exported_symbols=mod_all or [],
        )
        kg.add_node(mod_node)

        # Edge: Parent (Library or Module) -> Module
        kg.add_edge(
            Edge(
                source=parent_id,
                target=mod_node_id,
                type=EdgeType.CONTAINS,
            )
        )

        # Inspect symbols inside module
        try:
            dir_symbols = dir(mod)
        except Exception:
            dir_symbols = []

        submodules_to_recurse: List[types.ModuleType] = []

        for symbol_name in dir_symbols:
            if not is_public_symbol(symbol_name, mod_all):
                continue

            try:
                obj = getattr(mod, symbol_name)
            except Exception:
                continue

            # Submodule check
            if inspect.ismodule(obj):
                child_mod_name = getattr(obj, "__name__", "")
                if child_mod_name.startswith(lib_name) and not should_skip_module(child_mod_name):
                    mod_node.submodules.append(child_mod_name)
                    if self.include_submodules and child_mod_name not in self.visited_modules:
                        submodules_to_recurse.append(obj)
                continue

            # Function / Callable check
            if inspect.isfunction(obj) or inspect.isbuiltin(obj) or type(obj).__name__ == "ufunc":
                fn_node = self._extract_function(obj, symbol_name, mod_name, lib_name)
                if fn_node:
                    kg.add_node(fn_node)
                    kg.add_edge(
                        Edge(
                            source=mod_node_id,
                            target=fn_node.id,
                            type=EdgeType.CONTAINS,
                        )
                    )

            # Class check
            elif inspect.isclass(obj):
                cls_mod = getattr(obj, "__module__", "")
                if cls_mod and (cls_mod.startswith(lib_name) or cls_mod.startswith(mod_name)):
                    cls_node = self._extract_class(obj, symbol_name, mod_name, lib_name)
                    if cls_node:
                        kg.add_node(cls_node)
                        kg.add_edge(
                            Edge(
                                source=mod_node_id,
                                target=cls_node.id,
                                type=EdgeType.CONTAINS,
                            )
                        )

        # Recurse into discovered submodules
        if recurse_submodules:
            for child_mod in submodules_to_recurse:
                self._crawl_module_recursive(child_mod, lib_name, mod_node_id, kg, depth + 1)

    def _extract_function(
        self,
        func: Any,
        name: str,
        mod_name: str,
        lib_name: str,
    ) -> Optional[FunctionNode]:
        qualname = f"{mod_name}.{name}"
        fn_id = f"fn:{qualname}"

        doc = get_clean_docstring(func)
        sig_str, params, returns = safe_signature(func)
        parsed_doc = parse_docstring(doc)

        # Augment param descriptions from docstring if available
        for p in params:
            if p.name in parsed_doc.parameters:
                p_meta = parsed_doc.parameters[p.name]
                if not p.type_str and p_meta.get("type"):
                    p.type_str = p_meta["type"]
                if p_meta.get("description"):
                    p.description = p_meta["description"]

        if returns and not returns.description and parsed_doc.returns.get("description"):
            returns.description = parsed_doc.returns["description"]

        is_comp = is_compiled_object(func)
        is_dep = is_deprecated(func, doc)
        source = safe_get_source(func) if self.extract_sources else None

        return FunctionNode(
            id=fn_id,
            name=name,
            library=lib_name,
            module=mod_name,
            qualified_name=qualname,
            signature_str=sig_str,
            parameters=params,
            returns_info=returns,
            is_compiled=is_comp,
            is_deprecated=is_dep,
            docstring=doc,
            example_code=parsed_doc.examples,
            source_code=source,
        )

    def _extract_class(
        self,
        cls_obj: type,
        name: str,
        mod_name: str,
        lib_name: str,
    ) -> Optional[ClassNode]:
        qualname = f"{mod_name}.{name}"
        cls_id = f"cls:{qualname}"

        doc = get_clean_docstring(cls_obj)
        sig_str, _, _ = safe_signature(cls_obj)

        bases = [b.__name__ for b in cls_obj.__bases__ if b is not object]
        methods = [
            m for m in dir(cls_obj)
            if not m.startswith("_") and callable(getattr(cls_obj, m, None))
        ]
        props = [
            p for p in dir(cls_obj)
            if not p.startswith("_") and isinstance(getattr(cls_obj, p, None), property)
        ]

        return ClassNode(
            id=cls_id,
            name=name,
            library=lib_name,
            module=mod_name,
            qualified_name=qualname,
            constructor_sig=sig_str,
            bases=bases,
            methods=methods,
            properties=props,
            docstring=doc,
        )
