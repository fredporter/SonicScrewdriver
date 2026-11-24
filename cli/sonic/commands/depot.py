"""Sonic Depot CLI Commands.

Manage decentralized offline libraries of ISOs, installers, and patches.
Download once locally and serve across the home network.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional
import click

from sonic.lib.depot import (
    DepotError,
    list_artifacts,
    register_artifact,
    verify_artifact,
)
from sonic.lib.depot_gc import DepotGcError, build_gc_plan, format_bytes
from sonic.lib.serve import ServeError, build_artifact_index, serve_depot


@click.group("depot")
def depot_cmd():
    """Manage offline repository of ISOs, installers, patches, and firmware."""
    pass


@depot_cmd.command("list")
@click.option("--kind", "-k", help="Filter by artifact kind (iso, package, tool, installer)")
@click.option("--depot", "depot_dir", type=click.Path(file_okay=False, path_type=Path), help="Explicit depot root")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def list_depot(kind: Optional[str], depot_dir: Optional[Path], as_json: bool):
    """List all cached installers, ISOs, and tools in the local depot."""
    artifacts = list_artifacts(kind=kind, depot_dir=depot_dir)
    if as_json:
        click.echo(json.dumps(artifacts, indent=2))
        return

    roots = [depot_dir] if depot_dir else get_default_depot_roots()
    click.echo(f"Active Depot Roots: {', '.join(str(r) for r in roots if r.exists())}\n")

    if not artifacts:
        click.echo("No artifacts registered in the local depot.")
        return

    click.echo("Offline Depot Artifacts:")
    for a in artifacts:
        sz_mb = a['size_bytes'] / (1024 * 1024)
        click.echo(f"  • [{a['kind']}] {a['id']} (v{a['version']}) - {sz_mb:.1f} MB")
        click.echo(f"    File: {a['file_name']}")
        click.echo(f"    SHA256: {a['sha256'][:16]}...")
        if a.get("target_profiles"):
            click.echo(f"    Target Profiles: {', '.join(a['target_profiles'])}")


@depot_cmd.command("register")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--id", "-i", "artifact_id", required=True, help="Unique identifier for the artifact (e.g. mint-22-cinnamon)")
@click.option("--kind", "-k", default="iso", help="Artifact kind (iso, package, installer, tool)")
@click.option("--version", "-v", default="latest", help="Version tag (e.g. 22.0)")
@click.option("--sha256", help="Expected SHA-256 checksum for verification")
@click.option("--url", default="", help="Upstream origin URL")
@click.option("--profile", "-p", multiple=True, help="Target Mint profiles (e.g. cinnamon-full, xfce-light)")
@click.option("--description", default="", help="Description of the artifact")
@click.option("--depot", "depot_dir", type=click.Path(file_okay=False, path_type=Path), help="Explicit depot root")
def register(
    file_path: Path,
    artifact_id: str,
    kind: str,
    version: str,
    sha256: Optional[str],
    url: str,
    profile: tuple,
    description: str,
    depot_dir: Optional[Path],
):
    """Register and verify a local ISO or installer into the offline depot."""
    explicit = depot_dir or (os.environ.get("SONIC_DEPOT_ROOT") or "")
    if not explicit:
        click.secho(
            "An explicit depot root is required: pass --depot or set SONIC_DEPOT_ROOT.",
            fg="red",
            err=True,
        )
        raise click.Abort()
    root = Path(explicit).expanduser()

    try:
        rec = register_artifact(
            file_path=file_path,
            artifact_id=artifact_id,
            kind=kind,
            version=version,
            expected_sha256=sha256,
            upstream_url=url,
            target_profiles=list(profile),
            description=description,
            depot_dir=root,
        )
        click.secho(f"Successfully registered '{artifact_id}' in local depot.", fg="green")
        click.echo(json.dumps(rec.to_dict(), indent=2))
    except DepotError as e:
        click.secho(f"Registration failed: {e}", fg="red", err=True)
        raise click.Abort()


@depot_cmd.command("verify")
@click.argument("artifact_id")
@click.option("--depot", "depot_dir", type=click.Path(file_okay=False, path_type=Path), help="Explicit depot root")
def verify(artifact_id: str, depot_dir: Optional[Path]):
    """Verify presence and cryptographic SHA-256 integrity of a cached artifact."""
    try:
        res = verify_artifact(artifact_id, depot_dir=depot_dir)
        if res.get("healthy"):
            click.secho(f"Artifact '{artifact_id}' integrity OK (SHA-256 match).", fg="green")
        else:
            click.secho(f"Artifact '{artifact_id}' check FAILED: {res.get('status')}", fg="red", err=True)
            raise click.Abort()
        click.echo(json.dumps(res, indent=2))
    except DepotError as e:
        click.secho(f"Verification error: {e}", fg="red", err=True)
        raise click.Abort()


@depot_cmd.command("serve")
@click.option("--depot", "depot_dir", type=click.Path(file_okay=False, path_type=Path), help="Explicit artifact root (required)")
@click.option("--port", "-p", default=8088, show_default=True, help="Port to serve the depot on")
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind address; loopback by default")
@click.option("--lan", is_flag=True, help="Bind all interfaces (0.0.0.0); a deliberate LAN publication")
@click.option("--no-verify", is_flag=True, help="Skip per-file checksum verification")
def serve(depot_dir: Optional[Path], port: int, host: str, lan: bool, no_verify: bool):
    """Serve only the artifacts registered in the depot manifest."""
    explicit = depot_dir or (os.environ.get("SONIC_DEPOT_ROOT") or "")
    if not explicit:
        click.secho(
            "An explicit artifact root is required: pass --depot or set SONIC_DEPOT_ROOT.",
            fg="red",
            err=True,
        )
        raise click.Abort()

    root = Path(explicit).expanduser()
    bind = "0.0.0.0" if lan else host

    try:
        index = build_artifact_index(root)
    except ServeError as exc:
        click.secho(f"Depot serve error: {exc}", fg="red", err=True)
        raise click.Abort()

    click.secho(f"Serving {len(index)} registered artifact(s) from {root}", fg="green")
    click.echo(f"Listening on http://{bind}:{port}")
    if bind != "127.0.0.1":
        click.secho("Warning: this is visible on the network. Only registered artifacts are exposed.", fg="yellow")
    click.echo("Unregistered files, directories and paths outside the root are not reachable. Ctrl+C stops.")

    try:
        serve_depot(root, host=bind, port=port, verify=not no_verify)
    except ServeError as exc:
        click.secho(f"Depot serve error: {exc}", fg="red", err=True)
        raise click.Abort()
    except KeyboardInterrupt:
        click.echo("\nServer stopped.")


def _render_gc_plan(plan: dict) -> None:
    totals = plan["totals"]
    click.echo(f"Depot GC dry run · plan {plan['plan_id']}")
    click.echo(f"Root: {plan['depot_root']}")
    click.echo(
        f"Catalogue: {plan['catalogue']['status']} ({plan['catalogue']['path']}) · "
        f"receipts: {plan['receipts']['count']} · local pins: {plan['pins']['count']}"
    )
    click.echo("")

    if not plan["artifacts"]:
        click.echo("No registered artifacts.")

    for artifact in plan["artifacts"]:
        verdict = "REMOVE" if artifact["decision"] == "remove" else "KEEP"
        click.secho(
            f"  {verdict:<6} {artifact['id']} [{artifact['kind']} {artifact['version']}] "
            f"{format_bytes(artifact['bytes'])}",
            fg="yellow" if artifact["decision"] == "remove" else None,
        )
        click.echo(f"         path: {artifact['relative_path'] or '<none recorded>'}")
        click.echo(f"         why:  {artifact['reason']}")
        verified = artifact["verified_at"] or "not recorded"
        click.echo(f"         verified: {verified}")
        if artifact["pins"]:
            click.echo(
                "         pins: " + ", ".join(f"{p['source']} ({p['detail']})" for p in artifact["pins"])
            )
        if artifact["references"]:
            click.echo("         refs: " + ", ".join(ref["source"] for ref in artifact["references"]))
        links = artifact["hardlink"]["link_count"]
        if links and links > 1:
            click.echo(f"         hardlinks: {links} names — unlinking one frees no file data")

    click.echo("")
    click.echo(
        f"Artifacts {totals['artifact_count']} · retained {totals['retained_count']} · "
        f"eligible {totals['eligible_count']}"
    )
    click.echo(
        f"Artifact bytes {format_bytes(totals['artifact_bytes'])} · "
        f"unique inodes {format_bytes(totals['unique_inode_bytes'])}"
    )
    click.echo(f"Eligible artifact bytes {format_bytes(totals['eligible_artifact_bytes'])}")
    click.echo(
        f"Estimated reclaimable {format_bytes(totals['estimated_reclaimable_bytes'])} "
        "(zero while another hardlink remains; APFS measured at apply time)"
    )
    volume = plan["volume"]
    click.echo(
        f"Volume used before {format_bytes(volume['used_bytes'])} of "
        f"{format_bytes(volume['total_bytes'])} · after not predicted"
    )

    if plan["problems"]:
        click.echo("")
        click.secho("Unresolved inputs (no removals are proposed):", fg="yellow")
        for problem in plan["problems"]:
            click.echo(f"  - {problem}")

    click.echo("")
    click.echo(
        f"Plan {plan['plan_id']} is read-only. Nothing was removed. "
        "Apply is a later milestone and must quote this plan id."
    )


@depot_cmd.command("gc")
@click.option("--depot", "depot_dir", type=click.Path(file_okay=False, path_type=Path), help="Explicit depot root")
@click.option("--retain-days", type=click.IntRange(min=0), default=None, help="Expire artifacts added more than N days ago")
@click.option("--supersede", multiple=True, metavar="OLD=NEW@VERSION", help="Declare NEW@VERSION supersedes OLD (repeatable)")
@click.option("--verify", is_flag=True, help="Hash retained artifacts too, not only candidates and their keepers")
@click.option("--catalogue", "catalogue_path", type=click.Path(path_type=Path), help="Layer 0 catalogue used for pins")
@click.option("--pins", "pins_path", type=click.Path(path_type=Path), help="Local pins file (default <depot>/pins.json)")
@click.option("--json", "as_json", is_flag=True, help="Emit the full plan document")
def gc(
    depot_dir: Optional[Path],
    retain_days: Optional[int],
    supersede: tuple,
    verify: bool,
    catalogue_path: Optional[Path],
    pins_path: Optional[Path],
    as_json: bool,
):
    """Plan retention for the depot. Read-only: prints a plan id, removes nothing."""
    explicit = depot_dir or (os.environ.get("SONIC_DEPOT_ROOT") or "")
    if not explicit:
        click.secho(
            "An explicit depot root is required: pass --depot or set SONIC_DEPOT_ROOT.",
            fg="red",
            err=True,
        )
        raise click.Abort()

    try:
        plan = build_gc_plan(
            Path(explicit),
            retain_days=retain_days,
            supersede=supersede,
            verify=verify,
            catalogue_path=catalogue_path,
            pins_path=pins_path,
        )
    except DepotGcError as exc:
        click.secho(f"Depot GC error: {exc}", fg="red", err=True)
        raise click.Abort()

    if as_json:
        click.echo(json.dumps(plan, indent=2))
        return

    _render_gc_plan(plan)
