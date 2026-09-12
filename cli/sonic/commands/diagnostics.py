"""Operator diagnostics — spool event summary and health checks."""

from __future__ import annotations

from collections import Counter

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from sonic.lib.envelope import EventLevel
from sonic.lib.spool import emit, read_recent

console = Console()
MODULE = "sonic.diagnostics"


@click.group()
def diagnostics():
    """Operator diagnostics and spool event summary."""


@diagnostics.command()
@click.option("--limit", "-n", default=50,
              help="Number of recent events to analyze")
def summary(limit):
    """Show recent spool event summary.

    Reads the Sonic spool journal and displays:
    - Total events analyzed
    - Failure count (ERROR + CRITICAL)
    - Warning count
    - Top modules by event volume
    """
    emit(MODULE, f"Diagnostics summary requested (limit={limit})",
         EventLevel.INFO, tags=["diagnostics", "summary"])

    entries = read_recent(limit=limit)

    if not entries:
        console.print("[yellow]No spool events found.[/yellow]")
        console.print("Run any sonic command to generate spool events.")
        return

    failures = sum(
        1 for e in entries
        if e.get("level") in ("ERROR", "CRITICAL")
    )
    warnings = sum(
        1 for e in entries if e.get("level") == "WARNING"
    )
    modules = Counter(e.get("module", "unknown") for e in entries)

    # Summary panel
    console.print(
        Panel.fit(
            f"[bold]Recent Spool Events[/bold] (last {len(entries)})\n\n"
            f"  Total:    {len(entries)}\n"
            f"  Errors:   [bold red]{failures}[/bold red]\n"
            f"  Warnings: [bold yellow]{warnings}[/bold yellow]\n"
            f"  Healthy:  "
            f"[bold green]{len(entries) - failures - warnings}[/bold green]",
            title="Diagnostics Summary",
            border_style="blue",
        )
    )

    # Module breakdown
    mod_table = Table(title="Top Modules by Event Volume")
    mod_table.add_column("Module", style="cyan")
    mod_table.add_column("Events", style="bold")
    for mod, count in modules.most_common(10):
        mod_table.add_row(mod, str(count))
    console.print(mod_table)

    # Recent failures
    failure_events = [
        e for e in entries
        if e.get("level") in ("ERROR", "CRITICAL")
    ]
    if failure_events:
        fail_table = Table(title="Recent Failures")
        fail_table.add_column("Timestamp", style="dim")
        fail_table.add_column("Module", style="cyan")
        fail_table.add_column("Level", style="red")
        fail_table.add_column("Message", style="white")
        for e in failure_events[-10:]:
            fail_table.add_row(
                e.get("timestamp", "")[:19],
                e.get("module", ""),
                e.get("level", ""),
                e.get("message", "")[:60],
            )
        console.print(fail_table)

    emit(MODULE, f"Diagnostics summary complete "
         f"(failures={failures}, warnings={warnings})",
         EventLevel.INFO, tags=["diagnostics", "summary", "completed"])


@diagnostics.command()
def health():
    """Check the CLI and event journal, not hardware readiness."""
    emit(MODULE, "Health check requested", EventLevel.INFO,
         tags=["diagnostics", "health"])

    checks: list[tuple[str, bool, str]] = []

    # Check spool directory exists
    from sonic.lib.spool import _spool_path
    spool_dir = _spool_path().parent
    if spool_dir.exists():
        checks.append(("Spool Directory", True, str(spool_dir)))
    else:
        checks.append(("Spool Directory", False, f"{spool_dir} missing"))

    # Check spool journal
    spool_file = spool_dir / "sonic-events.jsonl"
    if spool_file.exists():
        entries = read_recent(limit=1)
        checks.append(("Spool Journal", True,
                       f"{spool_file} ({len(read_recent(limit=99999))} events)"))
    else:
        checks.append(("Spool Journal", False,
                       "No events written yet — run sonic commands"))

    # Check CLI is importable
    try:
        import sonic  # noqa: F401
        checks.append(("Sonic CLI", True, "importable"))
    except ImportError:
        checks.append(("Sonic CLI", False, "import failed"))

    table = Table(title="System Health Check")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Detail", style="dim")

    healthy = True
    for name, ok, detail in checks:
        status = "[bold green]✓ PASS[/bold green]" if ok else "[bold red]✗ FAIL[/bold red]"
        if not ok:
            healthy = False
        table.add_row(name, status, detail)

    console.print(table)

    if healthy:
        console.print("[bold green]All checks passed.[/bold green]")
    else:
        console.print("[bold red]Some checks failed. See details above.[/bold red]")

    emit(MODULE, f"Health check complete (healthy={healthy})",
         EventLevel.INFO if healthy else EventLevel.WARNING,
         tags=["diagnostics", "health", "completed"])