"""Sonic Depot CLI Commands.

Manage decentralized offline libraries of ISOs, installers, and patches.
Download once locally and serve across the home network.
"""

from __future__ import annotations

import http.server
import json
import socketserver
from pathlib import Path
from typing import Optional
import click

from sonic.lib.depot import (
    DepotError,
    get_default_depot_roots,
    list_artifacts,
    register_artifact,
    verify_artifact,
)


@click.group("depot")
def depot_cmd():
    """Manage offline repository of ISOs, installers, patches, and firmware."""
    pass


@depot_cmd.command("list")
@click.option("--kind", "-k", help="Filter by artifact kind (iso, package, tool, installer)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def list_depot(kind: Optional[str], as_json: bool):
    """List all cached installers, ISOs, and tools in the local depot."""
    artifacts = list_artifacts(kind=kind)
    if as_json:
        click.echo(json.dumps(artifacts, indent=2))
        return

    roots = get_default_depot_roots()
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
def register(
    file_path: Path,
    artifact_id: str,
    kind: str,
    version: str,
    sha256: Optional[str],
    url: str,
    profile: tuple,
    description: str,
):
    """Register and verify a local ISO or installer into the offline depot."""
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
        )
        click.secho(f"Successfully registered '{artifact_id}' in local depot.", fg="green")
        click.echo(json.dumps(rec.to_dict(), indent=2))
    except DepotError as e:
        click.secho(f"Registration failed: {e}", fg="red", err=True)
        raise click.Abort()


@depot_cmd.command("verify")
@click.argument("artifact_id")
def verify(artifact_id: str):
    """Verify presence and cryptographic SHA-256 integrity of a cached artifact."""
    try:
        res = verify_artifact(artifact_id)
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
@click.option("--port", "-p", default=8088, help="Port to serve offline depot on")
def serve(port: int):
    """Serve offline depot artifacts over local network for other nodes (decentralized server)."""
    roots = get_default_depot_roots()
    primary_root = next((r for r in roots if r.exists()), None)
    if not primary_root:
        click.secho("No existing depot directory found.", fg="red", err=True)
        raise click.Abort()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(primary_root), **kwargs)

    click.secho(f"Starting Sonic Decentralized Depot Server on port {port}...", fg="green")
    click.echo(f"Serving from: {primary_root}")
    click.echo("Other machines on the LAN can pull installers directly at local gigabit speeds without internet access.")
    click.echo("Press Ctrl+C to stop.")

    try:
        with socketserver.TCPServer(("", port), Handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        click.echo("\nServer stopped.")
