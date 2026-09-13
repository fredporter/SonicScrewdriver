"""Read-only hardware discovery and diagnostic commands."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import click

from sonic.lib.catalog import load_catalog
from sonic.lib.device_calc import calc_display_capability
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
@click.option("--width", "-w", type=int, help="Screen width in pixels to calculate display geometry.")
@click.option("--height", "-h", type=int, help="Screen height in pixels to calculate display geometry.")
@click.option("--resolution", "-r", type=str, help="Target resolution formatted as WxH (e.g. 1024x768, 1920x1080).")
@click.option("--device-type", "-t", type=str, help="Hardware display profile (e.g. pos_kiosk, retro_crt, ten_foot_tv, desktop_hd).")
@click.pass_context
def scan(
    ctx: click.Context,
    as_json: bool,
    fixture: str | None,
    width: int | None = None,
    height: int | None = None,
    resolution: str | None = None,
    device_type: str | None = None,
):
    """Execute non-destructive read-only hardware discovery."""
    provider = _get_provider(fixture)
    try:
        catalog = load_catalog()
    except Exception:
        catalog = None

    report = provider.scan(catalog=catalog)

    # Apply manual display geometry overrides if specified
    override_w = width
    override_h = height
    if resolution:
        parts = resolution.lower().split("x")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            override_w = int(parts[0])
            override_h = int(parts[1])

    if override_w or override_h or device_type:
        base_disp = report.display_capability or {}
        cur_w = override_w or base_disp.get("resolution", {}).get("width", 1920)
        cur_h = override_h or base_disp.get("resolution", {}).get("height", 1080)
        report.display_capability = calc_display_capability(cur_w, cur_h, device_type=device_type)

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

        if report.display_capability:
            disp = report.display_capability
            res = disp["resolution"]
            gc = disp["gridcore"]
            prose = disp["prose"]
            zen = disp["zen_viewport"]
            click.echo("\nDisplay & GridCore Geometry:")
            click.echo(f"  - Target Resolution: {res['width']}x{res['height']} ({disp['aspect_ratio']}, Profile: {disp['device_type']})")
            click.echo(f"  - Zen Viewport Scale: {zen['scale_factor']}x (Canvas: {zen['scaled_width']}x{zen['scaled_height']}, Letterbox Margin: H {zen['letterbox']['horizontal_padding_px']}px / V {zen['letterbox']['vertical_padding_px']}px)")
            click.echo(f"  - GridCore Capacity: Square {gc['square_register']['cols']}x{gc['square_register']['rows']} | Tall {gc['tall_register']['cols']}x{gc['tall_register']['rows']} | Super {gc['super_cells']['cols']}x{gc['super_cells']['rows']}")
            tt_fit = "FITS 1x" if gc['teletext_standard']['fits_1x'] else "REQUIRES SCALE"
            click.echo(f"  - Teletext Standard (40x25 / 480x500px): {tt_fit}")
            click.echo(f"  - Prose Line Measure: {prose['char_capacity_ch']}ch capacity -> Clamped to {prose['recommended_measure_ch']}ch ({prose['layout_mode']})")

        if report.storage_capacity:
            store = report.storage_capacity
            kc = store["knowledge_capacity"]
            click.echo("\nVault Knowledge & Capsule Storage Capacity:")
            click.echo(f"  - Total Storage: {store['storage_total_bytes'] / 1e9:.2f} GB | Usable Vault: {store['storage_vault_usable_gb']} GB (Reserved: {store['storage_system_bytes'] / 1e9:.2f} GB)")
            click.echo(f"  - Plain Prose Notes: {kc['plain_prose_notes']:,} notes (~3.5 KB each)")
            click.echo(f"  - Indexed Notes (FTS5): {kc['indexed_notes_fts5']:,} searchable notes (~4.9 KB each)")
            click.echo(f"  - Curated Animated BOBs: {kc['curated_bobs_gif']:,} sprites (~25 KB each)")
            click.echo(f"  - Offline Capsule Allocation: {kc['mini_capsules_10mb']:,} Mini (10 MB) | {kc['encyclopedia_zim_capsules_1gb']} ZIM Encyclopedias (1.0 GB)")

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

    if report.display_capability:
        disp = report.display_capability
        checks.append({
            "probe": "display_geometry",
            "tool": "device_calc",
            "status": "ok",
            "ready": True,
            "message": f"{disp['resolution']['width']}x{disp['resolution']['height']} ({disp['aspect_ratio']}, {disp['device_type']}) - Zen Scale {disp['zen_viewport']['scale_factor']}x",
        })

    if report.storage_capacity:
        store = report.storage_capacity
        checks.append({
            "probe": "capsule_storage",
            "tool": "device_calc",
            "status": "ok",
            "ready": True,
            "message": f"{store['storage_vault_usable_gb']} GB usable vault ({store['knowledge_capacity']['encyclopedia_zim_capsules_1gb']} ZIM capsules capacity)",
        })

    doc_data = {
        "platform": report.platform,
        "supported": report.platform.startswith("linux"),
        "overall_status": report.overall_status,
        "checks": checks,
        "display_capability": report.display_capability,
        "storage_capacity": report.storage_capacity,
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
