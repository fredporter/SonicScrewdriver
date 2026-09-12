"""Spool round-trip and diagnostics tests."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from sonic.lib.envelope import EventLevel, SpoolEvent
from sonic.lib.spool import emit, read_recent, write_spool


def test_spool_write_and_read(temp_spool: Path) -> None:
    """Emit an event then read it back. Verifies JSONL round-trip."""
    write_spool(SpoolEvent(
        module="test.spool",
        message="round-trip test",
        level=EventLevel.INFO,
        tags=["test", "roundtrip"],
    ))

    entries = read_recent(limit=10)
    assert len(entries) == 1
    assert entries[0]["module"] == "test.spool"
    assert entries[0]["message"] == "round-trip test"
    assert entries[0]["level"] == "INFO"
    assert "test" in entries[0]["tags"]
    assert "timestamp" in entries[0]


def test_emit_convenience(temp_spool: Path) -> None:
    """emit() should produce the same JSONL as write_spool()."""
    emit("test.spool", "convenience emit", EventLevel.WARNING,
         tags=["test", "emit"])

    entries = read_recent(limit=1)
    assert entries[0]["module"] == "test.spool"
    assert entries[0]["message"] == "convenience emit"
    assert entries[0]["level"] == "WARNING"
    assert "emit" in entries[0]["tags"]


def test_read_recent_empty(temp_spool: Path) -> None:
    """read_recent on empty journal returns []."""
    entries = read_recent(limit=50)
    assert entries == []


def test_read_recent_limit(temp_spool: Path) -> None:
    """read_recent respects the limit parameter."""
    for i in range(10):
        emit("test.spool", f"event {i}", EventLevel.INFO)
    entries = read_recent(limit=3)
    assert len(entries) == 3


def test_spool_event_schema(temp_spool: Path) -> None:
    """Every SpoolEvent.to_dict() has all required keys."""
    e = SpoolEvent(
        module="test.schema",
        message="schema check",
        level=EventLevel.ERROR,
        tags=["ci", "test"],
    )
    d = e.to_dict()
    required = {"timestamp", "level", "module", "message", "tags", "metadata"}
    assert required.issubset(set(d.keys()))
    assert d["level"] == "ERROR"


def test_diagnostics_summary(temp_spool: Path) -> None:
    """sonic diagnostics summary lists recent events."""
    from sonic.cli import cli

    emit("sonic.usb", "test usb event", EventLevel.INFO,
         tags=["test", "usb"])
    emit("sonic.bootloader", "test error", EventLevel.ERROR,
         tags=["test", "error"])

    runner = CliRunner()
    result = runner.invoke(cli, ["diagnostics", "summary", "--limit", "10"])
    assert result.exit_code == 0
    # Should mention the 2 events
    assert "test usb event" in result.output or "2" in result.output


def test_diagnostics_health(temp_spool: Path) -> None:
    """sonic diagnostics health returns passing checks."""
    from sonic.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["diagnostics", "health"])
    assert result.exit_code == 0
    assert "Spool Directory" in result.output
    assert "Sonic CLI" in result.output