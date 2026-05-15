"""Structured JSON logger for tool invocations.

Every tool call appends one line to logs/tool_calls.jsonl. This is the
foundation for the observability proposal in Phase 3 of the project.

Why JSON Lines and not regular logs:
- Each event is machine-parseable.
- Easy to ingest into BigQuery / Datadog / a dashboard later.
- One event per line means tools can append concurrently without corruption.

Fields per event:
    timestamp:    ISO 8601 UTC
    tool:         name of the tool invoked
    inputs:       dict of input arguments (sanitized — see SENSITIVE_FIELDS)
    outputs:      dict returned by the tool
    duration_ms:  wall-clock time
    success:      bool — False if the tool returned an error or raised
    error:        present only when success=False
    request_id:   correlates multiple tool calls within one agent run
"""
from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import LOG_DIR

LOG_FILE = LOG_DIR / "tool_calls.jsonl"
SENSITIVE_FIELDS = {"api_key", "token", "password"}


def _sanitize(d: dict[str, Any]) -> dict[str, Any]:
    return {k: ("***" if k in SENSITIVE_FIELDS else v) for k, v in d.items()}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_request_id() -> str:
    """Generate a short correlation ID for a single agent turn."""
    return uuid.uuid4().hex[:12]


def log_event(event: dict[str, Any]) -> None:
    """Append one JSON event to the log file. Best-effort: never raises."""
    event = {"timestamp": _now_iso(), **event}
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str, ensure_ascii=False) + "\n")
    except Exception:
        # Logging must never break the agent.
        pass


@contextmanager
def log_tool_call(tool_name: str, inputs: dict, request_id: str | None = None):
    """Context manager that times a tool call and logs it.

    Usage inside a tool:
        with log_tool_call("my_tool", inputs={"x": 1}) as record:
            result = ...
            record["outputs"] = result
            record["success"] = True
    """
    record: dict[str, Any] = {
        "tool": tool_name,
        "inputs": _sanitize(inputs),
        "request_id": request_id or new_request_id(),
    }
    started = time.perf_counter()
    try:
        yield record
    except Exception as exc:
        record["success"] = False
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["duration_ms"] = int((time.perf_counter() - started) * 1000)
        log_event(record)
        raise
    record.setdefault("success", True)
    record["duration_ms"] = int((time.perf_counter() - started) * 1000)
    log_event(record)


def get_log_path() -> Path:
    """Expose the log file path (useful for the Streamlit UI)."""
    return LOG_FILE
