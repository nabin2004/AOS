"""RuntimeChecker: Live introspection and signature drift verification against installed libraries."""

from __future__ import annotations

import importlib
import inspect
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from aos_lkg.schema.nodes import FunctionNode, LibraryNode, NodeType
from aos_lkg.schema.graph import KnowledgeGraph
from aos_lkg.extractor.inspector import safe_signature


class ApiValidationResult(BaseModel):
    api_id: str
    qualified_name: str
    exists: bool
    signature_matches: bool
    live_signature: Optional[str] = None
    recorded_signature: str
    error_message: Optional[str] = None


class LibraryValidationResult(BaseModel):
    library_name: str
    recorded_version: Optional[str] = None
    live_version: Optional[str] = None
    version_matches: bool = True
    api_results: List[ApiValidationResult] = Field(default_factory=list)


class RuntimeChecker:
    """Validates LKG nodes against live runtime Python environment."""

    @staticmethod
    def validate_library_versions(kg: KnowledgeGraph) -> List[LibraryValidationResult]:
        """Check all LibraryNode records against installed versions."""
        results = []
        for node in kg.nodes.values():
            if isinstance(node, LibraryNode):
                lib_name = node.name
                live_ver = None
                try:
                    pkg = importlib.import_module(lib_name)
                    live_ver = getattr(pkg, "__version__", None)
                except ImportError:
                    pass

                ver_matches = (node.version == str(live_ver)) if node.version and live_ver else True
                results.append(
                    LibraryValidationResult(
                        library_name=lib_name,
                        recorded_version=node.version,
                        live_version=str(live_ver) if live_ver else None,
                        version_matches=ver_matches,
                    )
                )
        return results

    @staticmethod
    def validate_apis(kg: KnowledgeGraph, sample_limit: Optional[int] = None) -> List[ApiValidationResult]:
        """Verify that indexed FunctionNode instances exist in live modules and signatures match."""
        results = []
        fn_nodes = [n for n in kg.nodes.values() if isinstance(n, FunctionNode)]
        if sample_limit:
            fn_nodes = fn_nodes[:sample_limit]

        for fn in fn_nodes:
            qualname = fn.qualified_name
            parts = qualname.rsplit(".", 1)
            if len(parts) != 2:
                continue
            mod_name, func_name = parts

            exists = False
            sig_matches = False
            live_sig = None
            err = None

            try:
                mod = importlib.import_module(mod_name)
                if hasattr(mod, func_name):
                    exists = True
                    obj = getattr(mod, func_name)
                    live_sig, _, _ = safe_signature(obj)

                    # Flexible signature check (normalize whitespace)
                    rec_sig_norm = fn.signature_str.replace(" ", "")
                    live_sig_norm = live_sig.replace(" ", "")
                    sig_matches = (rec_sig_norm == live_sig_norm) or (live_sig_norm in rec_sig_norm)
                else:
                    err = f"Symbol '{func_name}' not found in module '{mod_name}'"
            except Exception as e:
                err = str(e)

            results.append(
                ApiValidationResult(
                    api_id=fn.id,
                    qualified_name=qualname,
                    exists=exists,
                    signature_matches=sig_matches,
                    live_signature=live_sig,
                    recorded_signature=fn.signature_str,
                    error_message=err,
                )
            )

        return results
