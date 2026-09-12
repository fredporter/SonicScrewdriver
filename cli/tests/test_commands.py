"""Regression checks: removed prototypes must never claim success."""
import pytest
from sonic.cli import cli

@pytest.mark.parametrize("group", ["usb", "device", "mint", "bootloader", "security", "mesh", "chasis"])
def test_unimplemented_or_retired_groups_are_not_executable(runner, group):
    result = runner.invoke(cli, [group])
    assert result.exit_code != 0
    assert "No such command" in result.output
    assert "successfully" not in result.output

def test_diagnostics_help(runner):
    result = runner.invoke(cli, ["diagnostics", "--help"])
    assert result.exit_code == 0
    assert "summary" in result.output
