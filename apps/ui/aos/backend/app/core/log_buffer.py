"""In-memory circular ring buffer for real-time application logs and diagnostic visualization."""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timezone
import logging
import threading
import traceback
from typing import Any

from pydantic import BaseModel, Field

try:
    from opentelemetry import trace
except ImportError:
    trace = None


class LogEntry(BaseModel):
    """Structured application log record."""

    id: int
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    level: str
    logger: str
    message: str
    exc_info: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class LogBufferManager:
    """Thread-safe circular log buffer with live-subscription queues."""

    def __init__(self, max_capacity: int = 1000) -> None:
        self.max_capacity = max_capacity
        self._buffer: deque[LogEntry] = deque(maxlen=max_capacity)
        self._counter = 0
        self._lock = threading.Lock()
        self._subscribers: set[asyncio.Queue[LogEntry]] = set()

    def append(
        self,
        *,
        level: str,
        logger_name: str,
        message: str,
        exc_info: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> LogEntry:
        """Add a log entry and broadcast to active async subscribers."""
        trace_id = None
        span_id = None
        if trace is not None:
            span = trace.get_current_span()
            if span and span.get_span_context().is_valid:
                ctx = span.get_span_context()
                trace_id = format(ctx.trace_id, "032x")
                span_id = format(ctx.span_id, "016x")

        with self._lock:
            self._counter += 1
            entry = LogEntry(
                id=self._counter,
                level=level.upper(),
                logger=logger_name,
                message=message,
                exc_info=exc_info,
                trace_id=trace_id,
                span_id=span_id,
                extra=extra or {},
            )
            self._buffer.append(entry)

        # Notify subscribers (best-effort, non-blocking)
        for q in list(self._subscribers):
            try:
                q.put_nowait(entry)
            except Exception:
                pass

        return entry

    def query(
        self,
        *,
        limit: int = 100,
        level: str | None = None,
        query: str | None = None,
        since_id: int | None = None,
    ) -> list[LogEntry]:
        """Query buffered logs with optional level filtering and substring search."""
        with self._lock:
            entries = list(self._buffer)

        if since_id is not None:
            entries = [e for e in entries if e.id > since_id]

        if level:
            target_level = level.upper()
            entries = [e for e in entries if e.level == target_level]

        if query:
            q_lower = query.lower()
            entries = [
                e
                for e in entries
                if q_lower in e.message.lower()
                or q_lower in e.logger.lower()
                or (e.exc_info and q_lower in e.exc_info.lower())
            ]

        if limit > 0:
            entries = entries[-limit:]

        return entries

    def subscribe(self) -> asyncio.Queue[LogEntry]:
        """Register a new live subscriber queue."""
        q: asyncio.Queue[LogEntry] = asyncio.Queue(maxsize=200)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[LogEntry]) -> None:
        """Remove a subscriber queue."""
        self._subscribers.discard(q)

    def clear(self) -> None:
        """Clear the buffer."""
        with self._lock:
            self._buffer.clear()


# Global resident log buffer singleton
log_buffer = LogBufferManager(max_capacity=1000)


class RingBufferLoggingHandler(logging.Handler):
    """Logging handler intercepting log records into the circular LogBufferManager."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record) if self.formatter else record.getMessage()
            exc_text = None
            if record.exc_info:
                exc_text = "".join(traceback.format_exception(*record.exc_info))
            elif record.stack_info:
                exc_text = str(record.stack_info)

            extra_attrs = {}
            for k, v in record.__dict__.items():
                if k not in (
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "message",
                ):
                    if isinstance(v, (str, int, float, bool, dict, list)):
                        extra_attrs[k] = v

            log_buffer.append(
                level=record.levelname,
                logger_name=record.name,
                message=msg,
                exc_info=exc_text,
                extra=extra_attrs,
            )
        except Exception:
            self.handleError(record)
