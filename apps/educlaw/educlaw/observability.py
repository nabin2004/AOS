"""Optional Logfire spans around Pydantic AI."""

from __future__ import annotations

from educlaw.settings import Settings

_configured = False


def configure_logfire(settings: Settings | None = None) -> None:
    global _configured
    settings = settings or Settings.from_env()
    if _configured or not settings.logfire:
        return
    try:
        import logfire
    except ImportError:
        return
    logfire.configure(send_to_logfire="if-token-present")
    logfire.instrument_pydantic_ai()
    _configured = True
