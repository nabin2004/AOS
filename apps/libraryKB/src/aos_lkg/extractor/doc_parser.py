"""Docstring parser for NumPy, Google, and standard docstrings."""

from __future__ import annotations

import inspect
import re
from typing import Dict, List, Optional, Tuple


class ParsedDocstring:
    def __init__(
        self,
        summary: str = "",
        extended_summary: str = "",
        parameters: Optional[Dict[str, Dict[str, str]]] = None,
        returns: Optional[Dict[str, str]] = None,
        examples: Optional[str] = None,
        notes: Optional[str] = None,
    ):
        self.summary = summary
        self.extended_summary = extended_summary
        self.parameters = parameters or {}
        self.returns = returns or {}
        self.examples = examples
        self.notes = notes

    def to_dict(self) -> Dict:
        return {
            "summary": self.summary,
            "extended_summary": self.extended_summary,
            "parameters": self.parameters,
            "returns": self.returns,
            "examples": self.examples,
            "notes": self.notes,
        }


def parse_docstring(doc: Optional[str]) -> ParsedDocstring:
    """Parse a docstring into structured sections."""
    if not doc:
        return ParsedDocstring()

    cleaned_doc = inspect.cleandoc(doc)
    lines = cleaned_doc.splitlines()
    if not lines:
        return ParsedDocstring()

    # Skip leading blank lines
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1

    summary_lines = []
    while i < len(lines) and lines[i].strip():
        summary_lines.append(lines[i].strip())
        i += 1
    summary = " ".join(summary_lines)

    # Section regex for NumPy/Sphinx headers (e.g. Parameters\n----------)
    sections: Dict[str, List[str]] = {}
    current_section = "body"
    sections[current_section] = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check for NumPy style header: Name followed by dashes on next line
        if i + 1 < len(lines) and lines[i + 1].strip().startswith("---") and len(lines[i + 1].strip()) >= 3:
            current_section = stripped.lower()
            sections[current_section] = []
            i += 2
            continue

        # Check for Google/Sphinx style: "Parameters:"
        if stripped.endswith(":") and stripped[:-1].lower() in (
            "parameters",
            "args",
            "arguments",
            "returns",
            "yields",
            "examples",
            "notes",
            "references",
            "see also",
        ):
            current_section = stripped[:-1].lower()
            sections[current_section] = []
            i += 1
            continue

        sections[current_section].append(line)
        i += 1

    # Process parameters
    param_dict: Dict[str, Dict[str, str]] = {}
    raw_params = sections.get("parameters", []) or sections.get("args", []) or sections.get("arguments", [])
    if raw_params:
        current_param = None
        for line in raw_params:
            if not line.strip():
                continue
            param_match = re.match(r"^([a-zA-Z0-9_]+)\s*(?::|\s*:\s*(.*))?$", line.strip())
            if not line.startswith("  ") and param_match:
                current_param = param_match.group(1).strip()
                type_desc = param_match.group(2).strip() if param_match.group(2) else ""
                param_dict[current_param] = {"type": type_desc, "description": ""}
            elif current_param and line.strip():
                if param_dict[current_param]["description"]:
                    param_dict[current_param]["description"] += " " + line.strip()
                else:
                    param_dict[current_param]["description"] = line.strip()

    # Process returns
    return_dict: Dict[str, str] = {}
    raw_returns = sections.get("returns", []) or sections.get("yields", [])
    if raw_returns:
        ret_text = "\n".join(raw_returns).strip()
        return_dict["description"] = ret_text

    # Process examples
    examples_str = None
    raw_examples = sections.get("examples", [])
    if raw_examples:
        examples_str = "\n".join(raw_examples).strip()

    # Process notes
    notes_str = None
    raw_notes = sections.get("notes", [])
    if raw_notes:
        notes_str = "\n".join(raw_notes).strip()

    extended = "\n".join(sections.get("body", [])).strip()

    return ParsedDocstring(
        summary=summary,
        extended_summary=extended,
        parameters=param_dict,
        returns=return_dict,
        examples=examples_str,
        notes=notes_str,
    )
