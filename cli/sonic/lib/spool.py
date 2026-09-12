"""Spool/feed event writer for uCore-compatible telemetry.

Writes structured SpoolEvent records to
$UDOS_HOME/sonic/spool/sonic-events.jsonl
in the uCore spool shape: timestamp, module, level, message, tags.
"""

from __future__ import annotations

import json
from pathlib import Path

from sonic.lib.envelope import SpoolEvent, EventLevel
from sonic.lib.settings import state_root


def _spool_path() -> Path:
    """Return the path to the Sonic spool journal file."""
    base = state_root() / "spool"
    base.mkdir(parents=True, exist_ok=True)
    return base / "sonic-events.jsonl"


def write_spool(event: SpoolEvent) -> None:
    """Append a single spool event to the journal as a JSON line."""
    path = _spool_path()
    with open(path, "a") as fh:
        fh.write(json.dumps(event.to_dict(), default=str) + "\n")


def emit(
    module: str,
    message: str,
    level: EventLevel = EventLevel.INFO,
    tags: list[str] | None = None,
    metadata: dict | None = None,
) -> None:
    """Convenience function: build and write a SpoolEvent in one call."""
    write_spool(
        SpoolEvent(
            module=module,
            message=message,
            level=level,
            tags=tags or [],
            metadata=metadata or {},
        )
    )


def read_recent(limit: int = 50) -> list[dict]:
    """Return the most recent *limit* spool events as dicts."""
    path = _spool_path()
    if not path.exists():
        return []
    with open(path) as fh:
        lines = fh.readlines()
    entries: list[dict] = []
    for line in lines[-limit:]:
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries