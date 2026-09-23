"""AI Agents module using PydanticAI.

This module contains agents that handle AI-powered interactions.
Tools are defined in the tools/ subdirectory.
"""

try:
    from app.agents.assistant import AssistantAgent, Deps
    __all__ = ["AssistantAgent", "Deps"]
except ImportError:
    __all__ = []
