# Language Server Protocol (LSP) Module

This document describes the **LSP diagnostics and symbol indexing module** in EduClaw (`educlaw/lsp/ty.py`).

---

## Overview

In a coding agent harness, fast feedback loops prevent the agent from brute-forcing syntax or type errors at compile-time. The LSP module provides:
1. **AST Post-Write Diagnostics**: Instant syntax check after file edits (`ast.parse`) with line/column pointers.
2. **Type Checking Integration**: Runs `ty check` when available (or custom runner).
3. **AST Symbol Indexer (`find_definition`)**: Locates where classes, functions, async functions, or signatures are defined in the workspace.
4. **Workspace & File Symbol Search (`file_symbols`, `workspace_symbols`)**: Generates AST-backed symbol tables without requiring a full heavyweight language server daemon.

---

## Agent Tools

Registered on the agent in [`educlaw/agent/tools.py`](../educlaw/agent/tools.py):

| Tool | Purpose |
|------|---------|
| `syntax_check` | Parse a Python file with `ast.parse` and return syntax errors |
| `lsp_diagnostics` | Combined syntax check + `ty check` diagnostics |
| `lsp_definition` | Find symbol definition, line number, signature, and docstring |
| `lsp_symbols` | List all symbols in a file or search workspace symbols |

---

## Developer Usage

```python
from pathlib import Path
from educlaw.lsp.ty import LspClient

client = LspClient(cwd=Path.cwd())

# 1. Syntax check
print(client.syntax_check(Path("main.py")))

# 2. Find definition of a symbol
print(client.find_definition("WorkflowOrchestrator"))

# 3. List symbols in a file
print(client.file_symbols(Path("educlaw/animateworkflow/loop.py")))

# 4. Search workspace symbols
print(client.workspace_symbols("Agent"))
```
