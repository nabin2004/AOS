from dataclasses import dataclass
try:
    from pydantic_ai import CustomEvent
except ImportError:
    class CustomEvent:
        pass

@dataclass(kw_only=True)
class ToolProgressEvent(CustomEvent):
    """Event emitted during tool execution to stream status to the AG-UI frontend."""
    message: str
