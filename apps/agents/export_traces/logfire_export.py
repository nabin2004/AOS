from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from logfire.query_client import LogfireQueryClient

from export_traces.config import DEFAULT_PAGE_SIZE, DEFAULT_REGION, SCHEMA_VERSION

INVOKE_AGENT_OP = "invoke_agent"


def get_base_url(region: str, override: str | None = None) -> str:
    if override:
        return override.rstrip("/")
    return (
        "https://logfire-eu.pydantic.dev"
        if region.lower() == "eu"
        else "https://logfire-us.pydantic.dev"
    )


def _escape_sql_literal(value: str) -> str:
    return value.replace("'", "''")


def build_query(
    *,
    service: str | None = None,
    agent_name: str | None = None,
    cursor_timestamp: str | None = None,
    cursor_span_id: str | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
) -> str:
    where_clauses = [
        f"attributes->>'gen_ai.operation.name' = '{INVOKE_AGENT_OP}'",
    ]
    if service:
        where_clauses.append(f"service_name = '{_escape_sql_literal(service)}'")
    if agent_name:
        escaped = _escape_sql_literal(agent_name)
        where_clauses.append(
            f"(attributes->>'gen_ai.agent.name' = '{escaped}' "
            f"OR attributes->>'agent_name' = '{escaped}')"
        )
    if cursor_timestamp and cursor_span_id:
        escaped_ts = _escape_sql_literal(cursor_timestamp)
        escaped_span = _escape_sql_literal(cursor_span_id)
        where_clauses.append(
            f"(start_timestamp > '{escaped_ts}' "
            f"OR (start_timestamp = '{escaped_ts}' "
            f"AND span_id > '{escaped_span}'))"
        )
    where = " AND ".join(where_clauses)

    return f"""
    SELECT
        start_timestamp,
        trace_id,
        span_id,
        parent_span_id,
        span_name,
        attributes,
        service_name,
        duration,
        otel_status_code,
        is_exception,
        exception_type
    FROM records
    WHERE {where}
    ORDER BY start_timestamp ASC, span_id ASC
    LIMIT {limit}
    """


def write_schema_header(output_path: Path) -> None:
    header = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "export_header",
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    with output_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(header, default=str) + "\n")


def append_spans(output_path: Path, rows: list[dict[str, Any]]) -> None:
    with output_path.open("a", encoding="utf-8") as f:
        for row in rows:
            record = {"schema_version": SCHEMA_VERSION, "record_type": "span", **row}
            f.write(json.dumps(record, default=str) + "\n")


def export_traces(
    *,
    token: str,
    output: Path,
    region: str = DEFAULT_REGION,
    base_url_override: str | None = None,
    service: str | None = None,
    agent_name: str | None = None,
    days: int = 30,
    min_timestamp: datetime | None = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_rows: int | None = None,
    debug: bool = False,
) -> int:
    if min_timestamp is None:
        min_timestamp = datetime.now(timezone.utc) - timedelta(days=days)

    base_url = get_base_url(region, base_url_override)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_schema_header(output)

    total_fetched = 0
    cursor_timestamp: str | None = None
    cursor_span_id: str | None = None
    page = 0

    with LogfireQueryClient(read_token=token, base_url=base_url) as client:
        while True:
            if max_rows is not None and total_fetched >= max_rows:
                break

            limit = page_size
            if max_rows is not None:
                limit = min(limit, max_rows - total_fetched)

            sql = build_query(
                service=service,
                agent_name=agent_name,
                cursor_timestamp=cursor_timestamp,
                cursor_span_id=cursor_span_id,
                limit=limit,
            )
            result = client.query_json_rows(sql=sql, min_timestamp=min_timestamp, limit=limit)
            rows = result.get("rows", [])

            if debug and page == 0 and rows:
                print("\n--- DEBUG: First row attributes ---")
                print(json.dumps(rows[0].get("attributes", {}), indent=2))
                print("--- END DEBUG ---\n")

            if not rows:
                break

            append_spans(output, rows)
            total_fetched += len(rows)
            page += 1

            last = rows[-1]
            cursor_timestamp = str(last.get("start_timestamp"))
            cursor_span_id = str(last.get("span_id"))

            print(f"Page {page}: fetched {len(rows)} rows (total {total_fetched})")

            if len(rows) < limit:
                break

    print(f"Export complete. Total rows: {total_fetched}")
    print(f"   File: {output}")
    return total_fetched


def load_spans(input_path: Path) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("record_type") == "export_header":
                continue
            if record.get("record_type") == "span":
                spans.append({k: v for k, v in record.items() if k not in ("record_type", "schema_version")})
            else:
                spans.append(record)
    return spans
