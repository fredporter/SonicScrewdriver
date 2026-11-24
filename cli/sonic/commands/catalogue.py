"""Sonic Catalogue CLI.

Reads the distributable base catalogue (Layer 0 seed) and emits the library
snapshot consumed by GridCore teletext pages 600-609.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click

from sonic.lib.catalogue import (
    CatalogueError,
    build_snapshot,
    catalogue_summary,
    default_catalogue_path,
    load_catalogue,
)


@click.group("catalogue")
def catalogue_cmd():
    """Inspect the base distribution catalogue and emit a library snapshot."""


@catalogue_cmd.command("status")
@click.option("--catalogue", "catalogue_path", type=click.Path(path_type=Path), help="Base catalogue file")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def status(catalogue_path: Optional[Path], as_json: bool):
    """Summarise the declared titles, editions, capsules and managed lanes."""
    try:
        data = load_catalogue(catalogue_path)
    except CatalogueError as exc:
        click.secho(f"Catalogue error: {exc}", fg="red", err=True)
        raise click.Abort()

    summary = catalogue_summary(data)
    if as_json:
        summary["path"] = str(Path(catalogue_path) if catalogue_path else default_catalogue_path())
        click.echo(json.dumps(summary, indent=2))
        return

    click.echo(f"Base catalogue: {Path(catalogue_path) if catalogue_path else default_catalogue_path()}")
    click.echo(f"Layer {summary['layer']} v{summary['version']} ({summary['schema']})")
    click.echo(
        f"Titles {summary['titles']} · Editions {summary['editions']} · "
        f"Capsules {summary['capsules']} · Managed lanes {summary['managed_lanes']}"
    )
    if summary["statuses"]:
        rendered = "  ".join(f"{name} {count}" for name, count in sorted(summary["statuses"].items()))
        click.echo(f"Status: {rendered}")


@catalogue_cmd.command("snapshot")
@click.option("--catalogue", "catalogue_path", type=click.Path(path_type=Path), help="Base catalogue file")
@click.option("--depot", "depot_dir", type=click.Path(path_type=Path), help="Depot root to merge retention state from")
def snapshot(catalogue_path: Optional[Path], depot_dir: Optional[Path]):
    """Emit the ucode-library/1 snapshot used by the GridCore library pages."""
    try:
        data = load_catalogue(catalogue_path)
    except CatalogueError as exc:
        click.secho(f"Catalogue error: {exc}", fg="red", err=True)
        raise click.Abort()

    click.echo(json.dumps(build_snapshot(data, depot_dir=depot_dir), indent=2))
