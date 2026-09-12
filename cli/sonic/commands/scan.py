"""Read-only hardware discovery and diagnostic commands."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import click

from sonic.lib.catalog import load_catalog
from sonic.providers.base import BaseProvider, ScanReport
from sonic.providers.fixture import FixtureProvider
from sonic.providers.linux import LinuxProvider


def _get_provider(fixture: str | None) -> BaseProvider:
    if fixture:
        return FixtureProvider(Path(fixture))
    return LinuxProvider()


@click.command("scan")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON scan report without formatting.")
@click.option("--fixture", type=click.Path(exists=True, dir_okay=False), help="Path to offline probe fixture for testing.")
@click.pass_context
def scan(ctx: click.Context, as_json: bool, fixture: str | None):
    """Execute non-destructive read-only hardware discovery."""
    provider = _get_provider(fixture)
    try:
        catalog = load_catalog()
    except Exception:
        catalog = None

    report = provider.scan(catalog=catalog)

    if as_json:
        click.echo(report.model_dump_json(indent=2))
    else:
        click.echo(f"Sonic Hardware Scan — Host: {report.execution_host} ({report.platform})")
        click.echo(f"Status: {report.overall_status.upper()} | Observed: {report.observed_at}")
        click.echo("\nProbes:")
        for p in report.probes:
            stat = f"[{p.status.upper()}]"
            err = f" - {p.error}" if p.error else ""
            click.echo(f"  - {p.probe} ({p.tool}): {stat} ({p.duration_ms}ms, {p.device_count} devices){err}")

        click.echo(f"\nNormalized Devices Discovered ({len(report.devices)}):")
        if not report.devices:
            click.echo("  (no devices detected)")
        for dev in report.devices:
            cands = f" -> candidates: {', '.join(dev.model_candidates)}" if dev.model_candidates else ""
            size_str = f" ({dev.size_bytes} bytes)" if dev.size_bytes else ""
            click.echo(f"  - [{dev.bus}] {dev.hardware_id}: {dev.vendor or ''} {dev.product or ''}{size_str}{cands}")

    if report.overall_status == "ok":
        ctx.exit(0)
    else:
        # Partial, unsupported, or failed must exit non-zero (code 1)
        ctx.exit(1)


@click.command("doctor")
@click.option("--json", "as_json", is_flag=True, help="Emit doctor report in JSON format.")
@click.option("--fixture", type=click.Path(exists=True, dir_okay=False), help="Path to offline probe fixture.")
@click.pass_context
def doctor(ctx: click.Context, as_json: bool, fixture: str | None):
    """Diagnose hardware discovery tool availability and host platform support."""
    provider = _get_provider(fixture)
    try:
        catalog = load_catalog()
    except Exception:
        catalog = None

    report = provider.scan(catalog=catalog)

    checks = []
    for p in report.probes:
        checks.append({
            "probe": p.probe,
            "tool": p.tool,
            "status": p.status,
            "ready": p.status == "ok",
            "message": p.error or "Ready and responsive",
        })

    doc_data = {
        "platform": report.platform,
        "supported": report.platform.startswith("linux"),
        "overall_status": report.overall_status,
        "checks": checks,
    }

    if as_json:
        click.echo(json.dumps(doc_data, indent=2))
    else:
        click.echo(f"Sonic Hardware Doctor — Platform: {report.platform}")
        plat_status = "SUPPORTED" if doc_data["supported"] else "UNSUPPORTED"
        click.echo(f"Host OS: [{plat_status}]")
        click.echo("\nTool Availability & Probes:")
        for c in checks:
            indicator = "OK" if c["ready"] else "FAIL"
            click.echo(f"  [{indicator}] {c['probe']} ({c['tool']}): {c['status']} - {c['message']}")

    if report.overall_status == "ok":
        ctx.exit(0)
    else:
        ctx.exit(1)
