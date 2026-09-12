"""Inspect settings and explicitly import legacy state."""
import json
from pathlib import Path

import click

from sonic.lib.settings import import_legacy, state_root


@click.group()
def config():
    """Standalone settings and legacy-state intake."""


@config.command()
def paths():
    """Print resolved paths without creating directories."""
    try:
        root = state_root()
        click.echo(json.dumps({"schema": "sonic.paths/1", "state": str(root),
                               "spool": str(root / "spool")}, indent=2))
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


@config.command("import-legacy")
@click.argument("source", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--apply", is_flag=True, help="Copy files; default only previews the import.")
def legacy(source, apply):
    """Preview or copy SOURCE into isolated imports/legacy; retain originals."""
    try:
        click.echo(json.dumps(import_legacy(source, apply), indent=2))
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
