#!/usr/bin/env python3
"""
Export invoke_agent spans from Logfire for SFT fine-tuning.

Usage:
    cd apps/agents
    uv run python export_traces/01_export_traces.py --days 30 --output export_traces/agent_traces.jsonl
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from export_traces.config import DEFAULT_DAYS, DEFAULT_REGION
from export_traces.logfire_export import export_traces

load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export OTel invoke_agent spans from Logfire"
    )
    parser.add_argument(
        "--token", help="Logfire read token (or set LOGFIRE_READ_TOKEN)"
    )
    parser.add_argument("--region", default=os.environ.get("LOGFIRE_REGION", DEFAULT_REGION))
    parser.add_argument(
        "--base-url",
        default=os.environ.get("LOGFIRE_BASE_URL"),
        help="Override Logfire API base URL",
    )
    parser.add_argument("--service", help="Filter by service_name")
    parser.add_argument("--agent-name", help="Filter by gen_ai.agent.name")
    parser.add_argument(
        "--output",
        default="export_traces/agent_traces.jsonl",
        help="Output JSONL path",
    )
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--page-size", type=int, default=10_000)
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument(
        "--min-timestamp",
        help="Explicit min timestamp (ISO format), overrides --days",
    )
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    token = args.token or os.environ.get("LOGFIRE_READ_TOKEN")
    if not token:
        print("ERROR: Read token required. Set LOGFIRE_READ_TOKEN or pass --token.")
        return 1

    min_ts = None
    if args.min_timestamp:
        min_ts = datetime.fromisoformat(args.min_timestamp.replace("Z", "+00:00"))

    output = Path(args.output)
    if not output.is_absolute():
        output = Path(__file__).resolve().parent.parent / output

    print(f"Endpoint region: {args.region}")
    if args.agent_name:
        print(f"Agent filter: {args.agent_name}")
    print(f"Output: {output}")

    try:
        export_traces(
            token=token,
            output=output,
            region=args.region,
            base_url_override=args.base_url,
            service=args.service,
            agent_name=args.agent_name,
            days=args.days,
            min_timestamp=min_ts,
            page_size=args.page_size,
            max_rows=args.max_rows,
            debug=args.debug,
        )
    except Exception as exc:
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
