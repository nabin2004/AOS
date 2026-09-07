"""Extract complete Manim Community v0.21.0 inheritance graphs with precise Instantiable vs Abstract Base partition."""

import re
import json
from pathlib import Path
from typing import Dict, List, Any, Set

svg_sources = {
    "Cameras": Path(r"C:\Users\nabin\.gemini\antigravity-ide\brain\f41237bd-f1f1-49d1-880f-556bb3712e21\.system_generated\steps\110\content.md"),
    "Scenes": Path(r"C:\Users\nabin\.gemini\antigravity-ide\brain\f41237bd-f1f1-49d1-880f-556bb3712e21\.system_generated\steps\114\content.md"),
    "Animations": Path(r"C:\Users\nabin\.gemini\antigravity-ide\brain\f41237bd-f1f1-49d1-880f-556bb3712e21\.system_generated\steps\116\content.md"),
    "Mobjects": Path(r"C:\Users\nabin\.gemini\antigravity-ide\brain\f41237bd-f1f1-49d1-880f-556bb3712e21\.system_generated\steps\118\content.md"),
}

# The true abstract base classes and internal root abstractions that LLMs must never instantiate directly:
PURE_ABSTRACT_CLASSES: Set[str] = {
    # Mobjects
    "Mobject", "VMobject", "PMobject", "Point", "TipableVMobject", 
    "CoordinateSystem", "Polygram", "SVGMobject", "AbstractImageMobject",
    "Mobject1D", "Mobject2D", "_Updater", "_TimeBasedUpdater", "_NonTimeBasedUpdater",
    "LinearBase", "LogBase",
    # Animations
    "Animation", "Composition", "Transform", "TransformMatchingAbstractBase", 
    "TransformAnimations", "Homotopy", "ComplexHomotopy", "SmoothedVectorizedHomotopy",
    "FadeToColor", "ApplyMethod", "ApplyPointwiseFunction", "ApplyPointwiseFunctionToCenter",
    # Cameras
    "OldMultiCamera",
    # Scenes
    "VectorScene", "SpecialThreeDScene", "RerunSceneHandler", "SceneFileWriter"
}

full_data: Dict[str, Any] = {
    "title": "Manim Community v0.21.0 Reference Manual - Complete Inheritance Graph",
    "source_document": "FireShot Capture 001 - Reference Manual - Manim Community v0.21.0 - [docs.manim.community].pdf",
    "version": "v0.21.0",
    "summary": {
        "total_branches": len(svg_sources),
        "branch_names": list(svg_sources.keys()),
        "total_nodes": 0,
        "total_edges": 0,
        "total_instantiable_classes": 0,
        "total_abstract_base_classes": 0,
    },
    "branches": {},
}

all_instantiable_roster: Dict[str, List[Dict[str, Any]]] = {}

for branch_name, file_path in svg_sources.items():
    svg_text = file_path.read_text(encoding="utf-8")

    node_pattern = re.compile(
        r'<ns0:g id="node\d+" class="node">\s*'
        r'<ns0:title>(?P<name>.*?)</ns0:title>\s*'
        r'<ns0:g [^>]*>\s*'
        r'<ns0:a [^>]*ns1:href="(?P<href>[^"]*)"'
        r'(?:\s*ns1:title="(?P<title>[^"]*)")?'
    )

    nodes_dict: Dict[str, Dict[str, Any]] = {}
    for match in node_pattern.finditer(svg_text):
        name = match.group("name").strip()
        href = match.group("href") or ""
        doc_summary = (match.group("title") or "").strip()

        module_path = ""
        full_qual = ""
        m = re.search(r'reference/(manim\.[a-zA-Z0-9_\.]+)\.html', href)
        if m:
            full_qual = m.group(1)
            parts = full_qual.split(".")
            module_path = ".".join(parts[:-1])

        doc_url = f"https://docs.manim.community/en/v0.21.0/{href.replace('../', '')}" if href else ""

        is_abs = (name in PURE_ABSTRACT_CLASSES) or name.startswith("_")

        nodes_dict[name] = {
            "class_name": name,
            "module": module_path,
            "full_qualname": full_qual or f"manim.{name}",
            "doc_summary": doc_summary,
            "doc_url": doc_url,
            "parents": [],
            "children": [],
            "depth": 0,
            "is_abstract_base": is_abs,
            "is_instantiable": not is_abs,
        }

    # Extract all edges
    edge_pattern = re.compile(
        r'<ns0:g id="edge\d+" class="edge">\s*<ns0:title>(?P<parent>.*?)-&gt;(?P<child>.*?)</ns0:title>'
    )
    edges_list = []
    for match in edge_pattern.finditer(svg_text):
        p = match.group("parent").strip()
        c = match.group("child").strip()
        edges_list.append({"parent": p, "child": c})

        if p in nodes_dict:
            nodes_dict[p]["children"].append(c)
        if c in nodes_dict:
            nodes_dict[c]["parents"].append(p)

    def compute_depth(node_name: str, visited=None) -> int:
        if visited is None:
            visited = set()
        if node_name in visited:
            return 0
        visited.add(node_name)
        parents = nodes_dict.get(node_name, {}).get("parents", [])
        if not parents:
            return 0
        return 1 + max(compute_depth(p, visited.copy()) for p in parents)

    for name in nodes_dict:
        nodes_dict[name]["depth"] = compute_depth(name)

    instantiable = [name for name, d in nodes_dict.items() if d["is_instantiable"]]
    abstract = [name for name, d in nodes_dict.items() if d["is_abstract_base"]]

    all_instantiable_roster[branch_name] = [
        {
            "class_name": name,
            "module": nodes_dict[name]["module"],
            "parents": nodes_dict[name]["parents"],
            "doc_summary": nodes_dict[name]["doc_summary"],
        }
        for name in sorted(instantiable)
    ]

    branch_entry = {
        "branch_name": branch_name,
        "node_count": len(nodes_dict),
        "edge_count": len(edges_list),
        "instantiable_count": len(instantiable),
        "abstract_count": len(abstract),
        "instantiable_classes": sorted(instantiable),
        "abstract_classes": sorted(abstract),
        "edges": edges_list,
        "nodes": nodes_dict,
    }

    full_data["branches"][branch_name] = branch_entry
    full_data["summary"]["total_nodes"] += len(nodes_dict)
    full_data["summary"]["total_edges"] += len(edges_list)
    full_data["summary"]["total_instantiable_classes"] += len(instantiable)
    full_data["summary"]["total_abstract_base_classes"] += len(abstract)

full_data["instantiable_roster"] = all_instantiable_roster

# Write files
output_json_path = Path(r"C:\Users\nabin\Desktop\myall\AOS\apps\agentic\manim_inheritance_graph.json")
output_json_path.write_text(json.dumps(full_data, indent=2), encoding="utf-8")

output_leaves_path = Path(r"C:\Users\nabin\Desktop\myall\AOS\apps\agentic\manim_leaf_roster.json")
output_leaves_path.write_text(json.dumps(all_instantiable_roster, indent=2), encoding="utf-8")

print("Generated updated JSON artifacts:")
print(f"  {output_json_path.name}: {len(full_data['branches'])} branches, {full_data['summary']['total_nodes']} nodes")
print(f"  {output_leaves_path.name}: {full_data['summary']['total_instantiable_classes']} instantiable classes")
