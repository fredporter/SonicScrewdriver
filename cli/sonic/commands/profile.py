"""Sonic Hardware Profiling and Safety Gate Commands.

Inspects hardware against pinned Linux Mint profiles (cinnamon-full, xfce-light)
and enforces strict safety gates for provisioning.
"""

from __future__ import annotations

import json
from typing import Optional
import click

from sonic.lib.catalog import load_catalog
from sonic.lib.mint_profiler import (
    ProfileError,
    create_provision_plan,
    inspect_current_system,
    inspect_hardware_compatibility,
    load_profile_spec,
)


@click.group("profile")
def profile_cmd():
    """Manage and inspect Linux Mint hardware revival profiles."""
    pass


@profile_cmd.command("list")
def list_profiles():
    """List available Linux Mint profiles and baseline specification."""
    spec = load_profile_spec()
    baseline = spec.get("baseline", {})
    profiles = spec.get("profiles", {})
    hardware_tiers = spec.get("hardware_tiers", {})

    click.echo(f"Baseline: {baseline.get('distribution')} {baseline.get('version')} ({baseline.get('codename')})")
    click.echo(f"Kernel: {baseline.get('kernel_baseline')}\n")

    click.echo("Available Desktop Profiles:")
    for p_id, p in profiles.items():
        click.echo(f"  • {p_id}: {p.get('title')}")
        click.echo(f"    Desktop: {p.get('desktop_environment')} (Compositor: {p.get('compositor')})")
        click.echo(f"    RAM: min {p.get('min_ram_mb')} MB, rec {p.get('recommended_ram_mb')} MB | Disk: {p.get('min_disk_gb')} GB")
        click.echo(f"    Tiers: {', '.join(p.get('supported_hardware_tiers', []))}")
        click.echo(f"    Desc: {p.get('description')}\n")

    click.echo("Hardware Tiers:")
    for t_id, t in hardware_tiers.items():
        click.echo(f"  - {t_id} ({t.get('name')}) [{t.get('arch')}]: {t.get('known_limits')}")


@profile_cmd.command("inspect")
@click.option("--device", "-d", help="Device model ID from catalog to evaluate")
@click.option("--system", "-s", is_flag=True, help="Inspect current host machine")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def inspect(device: Optional[str], system: bool, as_json: bool):
    """Inspect hardware compatibility against Linux Mint profiles (read-only, non-destructive)."""
    if device:
        cat = load_catalog()
        item = cat.get(device)
        if not item:
            click.secho(f"Error: Unknown device model ID: {device}", fg="red", err=True)
            raise click.Abort()

        claims = getattr(item, "legacy_claims", {})
        ram_mb = claims.get("ram_mb", 0)
        storage_gb = claims.get("storage_gb", 0)
        cpu = claims.get("cpu", "")
        arch = "arm64" if "arm" in cpu.casefold() or "cortex" in cpu.casefold() else "x86_64"

        device_info = {
            "vendor": item.vendor,
            "model": item.model,
            "arch": arch,
            "ram_mb": ram_mb,
            "storage_gb": storage_gb,
        }
        report = inspect_hardware_compatibility(device_info)
    else:
        # Default: current host system
        report = inspect_current_system()

    if as_json:
        click.echo(json.dumps(report, indent=2))
        return

    click.secho("=== Linux Mint Profile Compatibility Assessment ===", bold=True)
    dev = report["device"]
    tier = report["hardware_tier"]
    click.echo(f"Device: {dev['vendor']} {dev['model']} ({dev['arch']})")
    click.echo(f"Specs: {dev['ram_mb']} MB RAM, {dev['storage_gb']} GB Storage")
    click.echo(f"Classified Hardware Tier: {tier['id']} ({tier['name']})")

    if report.get("warnings"):
        click.secho("\nSafety & Hardware Quirks:", fg="yellow", bold=True)
        for w in report["warnings"]:
            click.secho(f"  ⚠ {w}", fg="yellow")

    click.echo("\nProfile Compatibility Results:")
    for p_id, p_res in report["profiles"].items():
        color = "green" if p_res["status"] == "COMPATIBLE" else "yellow" if p_res["status"] == "COMPATIBLE_WITH_WARNINGS" else "red"
        click.secho(f"  [{p_res['status']}] {p_id} - {p_res['title']}", fg=color)
        for note in p_res.get("notes", []):
            click.echo(f"      • {note}")

    pref = report.get("preferred_profile")
    if pref:
        click.secho(f"\nRecommended Profile: {pref}", fg="green", bold=True)
    else:
        click.secho("\nNo profile fully meets hardware specifications.", fg="red")


@profile_cmd.command("plan")
@click.argument("profile_id")
@click.option("--device", "-d", required=True, help="Target device model ID")
@click.option("--target-disk", help="Target disk path (e.g. /dev/sdb)")
@click.option("--confirm", is_flag=True, help="Confirm destructive write authorization")
@click.option("--backup-verified", is_flag=True, help="Verify partition table backup exists")
def plan(profile_id: str, device: str, target_disk: Optional[str], confirm: bool, backup_verified: bool):
    """Generate a provisioning plan under strict safety gate control."""
    cat = load_catalog()
    item = cat.get(device)
    if not item:
        click.secho(f"Error: Unknown device ID: {device}", fg="red", err=True)
        raise click.Abort()

    claims = getattr(item, "legacy_claims", {})
    device_info = {
        "vendor": item.vendor,
        "model": item.model,
        "arch": "x86_64",
        "ram_mb": claims.get("ram_mb", 4096),
        "storage_gb": claims.get("storage_gb", 64),
    }

    try:
        plan_res = create_provision_plan(
            profile_id=profile_id,
            device_info=device_info,
            target_disk=target_disk,
            confirm=confirm,
            backup_verified=backup_verified,
        )
        click.echo(json.dumps(plan_res, indent=2))
        if plan_res.get("destructive"):
            click.secho(f"\n[SAFETY GATE]: {plan_res.get('gate')}", fg="yellow", bold=True)
            click.secho(f"Notice: {plan_res.get('message')}", fg="yellow")
    except ProfileError as e:
        click.secho(f"Plan error: {e}", fg="red", err=True)
        raise click.Abort()
