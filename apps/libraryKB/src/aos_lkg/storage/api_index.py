"""APIIndex: High-performance exact lookup index for library APIs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from aos_lkg.schema.nodes import FunctionNode, ClassNode, BaseNode
from aos_lkg.schema.graph import KnowledgeGraph


class ApiEntry(BaseModel):
    id: str
    name: str
    qualified_name: str
    library: str
    module: str
    signature_str: str
    doc_summary: Optional[str] = None
    parameters: List[str] = Field(default_factory=list)
    return_type: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    example_code: Optional[str] = None


class ApiIndex:
    """Exact API lookup table and fast search directory."""

    def __init__(self):
        self.by_qualname: Dict[str, ApiEntry] = {}
        self.by_id: Dict[str, ApiEntry] = {}
        self.by_name: Dict[str, List[ApiEntry]] = {}
        self.by_module: Dict[str, List[ApiEntry]] = {}

    def add_entry(self, entry: ApiEntry) -> None:
        self.by_qualname[entry.qualified_name] = entry
        self.by_id[entry.id] = entry
        self.by_name.setdefault(entry.name, []).append(entry)
        self.by_module.setdefault(entry.module, []).append(entry)
        # Also index short qualname if possible (e.g. scipy.optimize.brentq)
        parts = entry.qualified_name.split(".")
        if len(parts) >= 2:
            short_qual = f"{parts[0]}.{parts[1]}.{parts[-1]}" if len(parts) > 2 else entry.qualified_name
            if short_qual not in self.by_qualname:
                self.by_qualname[short_qual] = entry

    @classmethod
    def from_knowledge_graph(cls, kg: KnowledgeGraph) -> ApiIndex:
        index = cls()
        for node in kg.nodes.values():
            if isinstance(node, FunctionNode):
                params = [f"{p.name}: {p.type_str or 'Any'}" for p in node.parameters]
                ret_str = node.returns_info.type_str if node.returns_info else None
                summary = node.docstring.split("\n")[0] if node.docstring else None

                entry = ApiEntry(
                    id=node.id,
                    name=node.name,
                    qualified_name=node.qualified_name,
                    library=node.library,
                    module=node.module,
                    signature_str=node.signature_str,
                    doc_summary=summary,
                    parameters=params,
                    return_type=ret_str,
                    capabilities=node.capabilities,
                    example_code=node.example_code,
                )
                index.add_entry(entry)
            elif isinstance(node, ClassNode):
                summary = node.docstring.split("\n")[0] if node.docstring else None
                entry = ApiEntry(
                    id=node.id,
                    name=node.name,
                    qualified_name=node.qualified_name,
                    library=node.library,
                    module=node.module,
                    signature_str=node.constructor_sig,
                    doc_summary=summary,
                    parameters=[],
                    return_type=node.name,
                    capabilities=getattr(node, "capabilities", []),
                    example_code=None,
                )
                index.add_entry(entry)
        return index

    def get_by_qualname(self, qualname: str) -> Optional[ApiEntry]:
        if qualname in self.by_qualname:
            return self.by_qualname[qualname]
        # Try matching by suffix or direct class/function name
        for qname, entry in self.by_qualname.items():
            if qname.endswith(f".{qualname}") or entry.name == qualname:
                return entry
        return None

    def get_by_id(self, node_id: str) -> Optional[ApiEntry]:
        return self.by_id.get(node_id)

    def search_by_name(self, name: str) -> List[ApiEntry]:
        return self.by_name.get(name, [])

    def get_module_apis(self, module_name: str) -> List[ApiEntry]:
        return self.by_module.get(module_name, [])

    def save_jsonl(self, filepath: str | Path) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for entry in self.by_qualname.values():
                f.write(json.dumps(entry.model_dump(), ensure_ascii=False) + "\n")

    @classmethod
    def load_jsonl(cls, filepath: str | Path) -> ApiIndex:
        path = Path(filepath)
        index = cls()
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    entry = ApiEntry(**data)
                    index.add_entry(entry)
        return index
