"""DBOS durable-execution bootstrap for AOS agents.

Configure early so `@DBOS.step` on tools can register. Call
`ensure_dbos_launched()` before durable agent runs when `AOS_DBOS=1`.
"""

from __future__ import annotations

import os
from pathlib import Path

from dbos import DBOS
from dbos import DBOSConfig

from observability import configure_logfire, logfire_enabled

# Logfire must be configured before DBOS so enable_otlp can attach exporters.
configure_logfire()

_AGENTS_ROOT = Path(__file__).resolve().parent
_DEFAULT_SQLITE = f"sqlite:///{_AGENTS_ROOT / 'workspace' / 'dbos_sys.sqlite'}"

_launched = False
_FALSE = frozenset({"0", "false", "no", "off"})


def dbos_enabled() -> bool:
    """True when durable execution should be used for graph/batch runs."""
    flag = os.getenv("AOS_DBOS", "").strip().lower()
    if flag in _FALSE:
        return False
    if flag in ("1", "true", "yes", "on"):
        return True
    return bool(os.getenv("DBOS_SYSTEM_DATABASE_URL", "").strip())


def _system_database_url() -> str:
    return (
        os.getenv("DBOS_SYSTEM_DATABASE_URL", _DEFAULT_SQLITE).strip()
        or _DEFAULT_SQLITE
    )


_dbos_config: DBOSConfig = {
    "name": "aos-agents",
    "system_database_url": _system_database_url(),
    "enable_otlp": logfire_enabled(),
}
DBOS(config=_dbos_config)


def ensure_dbos_launched() -> None:
    """Idempotent DBOS.launch() when durable mode is enabled."""
    global _launched
    if not dbos_enabled():
        return
    if _launched:
        return
    # Ensure workspace exists for default SQLite path.
    (_AGENTS_ROOT / "workspace").mkdir(parents=True, exist_ok=True)
    DBOS.launch()
    _launched = True
