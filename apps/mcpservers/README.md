## Manim documentation MCP server

This server exposes semantic search over `manim_kb.md`:

- `search_manim_kb` for API documentation
- `search_manim_signatures` for constructor and method signatures
- `repair_manim_source` for documentation-guided, deterministic source repair

`repair_manim_source` accepts the generated Python source and the Manim error
log. It searches the local documentation index, applies only narrow known
compatibility fixes, validates the resulting Python with `ast.parse`, and
returns the candidate source, changes, and documentation evidence. A caller
should review the returned source before rendering it.
