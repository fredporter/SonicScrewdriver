"""Sonic Package Management Commands.

Provides offline dependency installation, integrity verification, shared dependency tracking,
and safe non-destructive uninstallation.
"""

from __future__ import annotations

import json
from pathlib import Path
import click

from sonic.lib.capsule_tomb import (
    compute_file_sha256,
    pack_capsule,
    seal_tomb,
    verify_container,
)
from sonic.lib.dependency_installer import (
    PackageError,
    install_package,
    list_installed_packages,
    uninstall_package,
    verify_package,
)


@click.group("package")
def package_cmd():
    """Manage offline packages, versioned artifacts, and shared dependencies."""
    pass


@package_cmd.command("pack")
@click.argument("source_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--out", "-o", type=click.Path(dir_okay=False, path_type=Path), help="Output .capsule archive path")
@click.option("--title", "-t", help="Capsule human title")
@click.option("--author", "-a", help="Capsule author")
@click.option("--version", "-v", default="1.0.0", help="Capsule semantic version")
def pack(source_dir: Path, out: Optional[Path], title: Optional[str], author: Optional[str], version: str):
    """Package a directory or binder into a signed .capsule bundle."""
    try:
        archive_path = pack_capsule(source_dir, output_file=out, title=title, author=author, version=version)
        click.secho(f"Successfully packaged capsule: {archive_path}", fg="green")
        click.echo(f"SHA-256: {compute_file_sha256(archive_path)}")
    except Exception as e:
        click.secho(f"Capsule packaging failed: {e}", fg="red", err=True)
        raise click.Abort()


@package_cmd.command("seal")
@click.argument("source_path", type=click.Path(exists=True, path_type=Path))
@click.option("--out", "-o", type=click.Path(dir_okay=False, path_type=Path), help="Output .tomb archive path")
@click.option(
    "--reason",
    "-r",
    default="archived_historical_witness",
    type=click.Choice(["dissolved_to_ether", "archived_historical_witness", "frozen_edition"]),
    help="Reason for sealing tomb",
)
@click.option("--notes", "-n", default="", help="Audit or reviewer rationale notes")
def seal(source_path: Path, out: Optional[Path], reason: str, notes: str):
    """Seal an edition, binder, or completed dispatch into an immutable .tomb archive."""
    try:
        tomb_path = seal_tomb(source_path, output_file=out, reason=reason, notes=notes)
        click.secho(f"Successfully sealed immutable tomb: {tomb_path}", fg="green")
        click.echo(f"Tomb Seal SHA-256: {compute_file_sha256(tomb_path)}")
        click.echo(f"Tombstone Reason: {reason}")
    except Exception as e:
        click.secho(f"Tomb sealing failed: {e}", fg="red", err=True)
        raise click.Abort()


@package_cmd.command("install")
@click.argument("archive", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--consumer", "-c", required=True, help="Consumer/product ID registering dependency (e.g. uCode, HomeNest)")
def install(archive: Path, consumer: str):
    """Install an offline package artifact (.spkg)."""
    try:
        res = install_package(archive, consumer)
        status = res.get("status")
        name = res.get("name")
        version = res.get("version")
        if status == "reused":
            click.secho(f"Package '{name} v{version}' already installed; added '{consumer}' to consumers.", fg="green")
        else:
            click.secho(f"Successfully installed '{name} v{version}' for '{consumer}'.", fg="green")
        click.echo(json.dumps(res, indent=2))
    except PackageError as e:
        click.secho(f"Package installation failed: {e}", fg="red", err=True)
        raise click.Abort()


@package_cmd.command("list")
def list_pkgs():
    """List installed packages and their consumers."""
    pkgs = list_installed_packages()
    if not pkgs:
        click.echo("No packages installed.")
        return
    for p in pkgs:
        consumers = ", ".join(p.get("required_by", [])) or "none"
        click.echo(f"- {p['name']} ({p['version']}): required by [{consumers}]")


@package_cmd.command("verify")
@click.argument("target")
def verify(target: str):
    """Verify integrity of an installed package or a .capsule / .tomb archive."""
    target_path = Path(target)
    if target_path.is_file() and (target.endswith(".capsule") or target.endswith(".tomb") or target.endswith(".zip")):
        try:
            report = verify_container(target_path)
            if report.get("valid"):
                click.secho(f"Container '{target}' ({report.get('container_type')}) integrity OK ({report.get('verified_files')}/{report.get('total_files')} files verified).", fg="green")
            else:
                click.secho(f"Container '{target}' integrity FAILED: {report.get('corrupt_files')}", fg="red", err=True)
                raise click.Abort()
        except Exception as e:
            click.secho(f"Container verification error: {e}", fg="red", err=True)
            raise click.Abort()
    else:
        try:
            report = verify_package(target)
            if report.get("healthy"):
                click.secho(f"Package '{target}' integrity OK.", fg="green")
            else:
                click.secho(f"Package '{target}' integrity check FAILED: {report}", fg="red", err=True)
                raise click.Abort()
        except PackageError as e:
            click.secho(f"Verification error: {e}", fg="red", err=True)
            raise click.Abort()


@package_cmd.command("uninstall")
@click.argument("package_name")
@click.option("--consumer", "-c", required=True, help="Consumer/product ID unregistering the package")
def uninstall(package_name: str, consumer: str):
    """Safely uninstall a package or unregister a consumer without removing user documents."""
    try:
        res = uninstall_package(package_name, consumer)
        if res.get("status") == "retained":
            click.secho(f"Package '{package_name}' retained: {res.get('reason')}", fg="yellow")
        else:
            click.secho(f"Package '{package_name}' uninstalled successfully ({res.get('removed_files')} files removed).", fg="green")
        click.echo(json.dumps(res, indent=2))
    except PackageError as e:
        click.secho(f"Uninstall failed: {e}", fg="red", err=True)
        raise click.Abort()
