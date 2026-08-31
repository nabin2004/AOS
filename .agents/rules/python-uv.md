# Python and UV Workspace Guidelines

## Environment & Dependency Management
- Always use `uv` for environment management, dependency resolution, and running scripts.
- To execute scripts in workspace packages: `uv run python <path_to_script>` or `uv run --package <pkg_name> <command>`.
- Use `uv sync` to update the virtual environment after modifying `pyproject.toml` dependencies.
- Never use global `python` or `pip` without `uv`.

## Code Style & Standards
- **Python Version**: Minimum Python 3.12.
- **Type Annotations**: Use strict type hinting everywhere (`typing` or built-in generics like `list[str]`, `dict[str, Any]`, `Optional[T]`).
- **Pydantic V2**: All schemas and data transfer objects must use Pydantic V2 (`BaseModel`, `Field`, `model_validator`, `field_validator`).
- **Asyncio**: Use `async`/`await` for I/O-bound operations (LLM calls, audio synthesis, file system operations in agent graph).
- **Linter & Formatting**: Adhere to Ruff configuration defined in root `pyproject.toml`.
