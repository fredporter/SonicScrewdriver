"""Offline model lookup, without device matching or write eligibility."""
import json

import click

from sonic.lib.catalog import load_catalog


@click.group()
def library():
    """Read the bundled, unverified device-model catalog offline."""


def _records():
    try:
        return load_catalog()
    except (OSError, ValueError) as exc:
        raise click.ClickException(f"Invalid catalog: {exc}") from exc


@library.command()
@click.argument("query", default="")
@click.option("--json", "as_json", is_flag=True)
def search(query, as_json):
    """Search model names, vendors, IDs and types (not user documents)."""
    q = query.casefold()
    items = [item for item in _records().values()
             if q in " ".join([item.id, item.vendor, item.model, item.type]).casefold()]
    if as_json:
        click.echo(json.dumps({"schema": "sonic.library-search/1", "devices": [i.model_dump() for i in items]}, indent=2))
    else:
        for item in items:
            click.echo(f"{item.id}: {item.vendor} {item.model} [unverified]")
        click.echo(f"{len(items)} model(s). Model records do not establish flash compatibility.")


@library.command()
@click.argument("model_id")
def show(model_id):
    """Show an exact model ID as JSON, including historical claims."""
    item = _records().get(model_id)
    if item is None:
        raise click.ClickException(f"Unknown model ID: {model_id}")
    click.echo(json.dumps(item.model_dump(), indent=2))
