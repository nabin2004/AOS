"""Tests for system logs and ring buffer diagnostic observability."""

from app.core.log_buffer import LogBufferManager, RingBufferLoggingHandler
import logging


def test_log_buffer_append_and_query():
    """Verify in-memory circular buffer append, query, and filtering."""
    mgr = LogBufferManager(max_capacity=5)
    for i in range(10):
        mgr.append(
            level="INFO" if i % 2 == 0 else "ERROR",
            logger_name="test_logger",
            message=f"Log message {i}",
        )

    # Should retain only the last 5 entries due to max_capacity
    entries = mgr.query(limit=10)
    assert len(entries) == 5
    assert entries[-1].message == "Log message 9"

    # Filter by level
    errors = mgr.query(level="ERROR")
    assert all(e.level == "ERROR" for e in errors)

    # Filter by query substring
    found = mgr.query(query="message 8")
    assert len(found) == 1
    assert found[0].message == "Log message 8"


def test_ring_buffer_handler_interception():
    """Verify logging.Handler intercepts records into log_buffer."""
    test_logger = logging.getLogger("test_interception")
    handler = RingBufferLoggingHandler()
    test_logger.addHandler(handler)
    test_logger.setLevel(logging.INFO)

    test_logger.info("Captured log event through standard logging")

    from app.core.log_buffer import log_buffer
    entries = log_buffer.query(query="Captured log event through standard logging")
    assert len(entries) >= 1
    assert entries[-1].logger == "test_interception"
