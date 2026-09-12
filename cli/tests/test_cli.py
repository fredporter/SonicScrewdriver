"""Tests for the sonic CLI entrypoint and top-level behavior."""

from __future__ import annotations

from click.testing import CliRunner

from sonic.cli import cli


def test_cli_no_args_shows_help(runner: CliRunner) -> None:
    result = runner.invoke(cli)
    assert result.exit_code == 0
    assert "Sonic-Screwdriver" in result.output


def test_cli_version(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "sonic, version" in result.output


def test_cli_verbose_flag(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--verbose", "--help"])
    assert result.exit_code == 0


def test_cli_help_lists_command_groups(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    for group in [
        "diagnostics",
    ]:
        assert group in result.output