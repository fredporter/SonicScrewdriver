"""Shared fixtures for SonicScrewdriver CLI tests."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Generator

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    """Click CLI test runner with mixed stderr/stdout."""
    return CliRunner()


@pytest.fixture
def temp_spool() -> Generator[Path, None, None]:
    """Temporary spool directory that isolates test writes."""
    import sonic.lib.spool as spool_mod  # noqa: F811

    original = spool_mod._spool_path
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "spool"
        tmp.mkdir(parents=True, exist_ok=True)

        def _override() -> Path:
            return tmp / "sonic-events.jsonl"

        spool_mod._spool_path = _override  # type: ignore[assignment]
        try:
            yield tmp / "sonic-events.jsonl"
        finally:
            spool_mod._spool_path = original  # type: ignore[assignment]