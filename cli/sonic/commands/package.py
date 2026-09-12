"""Sonic Package Management Commands.

Provides offline dependency installation, integrity verification, shared dependency tracking,
and safe non-destructive uninstallation.
"""

from __future__ import annotations

import json
from pathlib import Path
import click

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
@click.argument("package_name")
def verify(package_name: str):
    """Verify disk integrity of an installed package."""
    try:
        report = verify_package(package_name)
        if report.get("healthy"):
            click.secho(f"Package '{package_name}' integrity OK.", fg="green")
        else:
            click.secho(f"Package '{package_name}' integrity check FAILED: {report}", fg="red", err=True)
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
