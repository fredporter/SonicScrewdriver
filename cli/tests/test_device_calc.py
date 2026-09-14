"""Tests for display geometry capability, storage/capsule capacity, and scan integration."""
import json
from pathlib import Path
import pytest
from click.testing import CliRunner

from sonic.cli import cli
from sonic.lib.device_calc import (
    calc_display_capability,
    calc_storage_capacity,
    detect_host_display,
)
from sonic.lib.plan import create_plan, dry_run_apply

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_calc_display_capability_desktop_hd():
    cap = calc_display_capability(1920, 1080)
    assert cap["aspect_ratio"] == "16:9"
    assert cap["device_type"] == "desktop_hd"
    assert cap["zen_viewport"]["scale_factor"] == 1.5
    assert cap["gridcore"]["square_register"]["cols"] == 240
    assert cap["gridcore"]["square_register"]["rows"] == 135
    assert cap["gridcore"]["tall_register"]["cols"] == 160
    assert cap["gridcore"]["tall_register"]["rows"] == 54
    assert cap["gridcore"]["super_cells"]["cols"] == 80
    assert cap["gridcore"]["super_cells"]["rows"] == 27
    assert cap["gridcore"]["teletext_standard"]["fits_1x"] is True
    assert cap["gridcore"]["teletext_standard"]["fits_2x"] is True
    assert cap["prose"]["layout_mode"] == "optimal_zen"
    assert cap["prose"]["recommended_measure_ch"] == 72
    assert cap["prose"]["max_width_px"] == 680


def test_calc_display_capability_pos_kiosk():
    cap = calc_display_capability(1024, 768)
    assert cap["aspect_ratio"] == "4:3"
    assert cap["device_type"] == "pos_kiosk"
    assert cap["zen_viewport"]["scale_factor"] == 1.28
    assert cap["gridcore"]["square_register"]["cols"] == 128
    assert cap["gridcore"]["square_register"]["rows"] == 96
    assert cap["gridcore"]["tall_register"]["cols"] == 85
    assert cap["gridcore"]["tall_register"]["rows"] == 38
    assert cap["gridcore"]["teletext_standard"]["fits_1x"] is True
    assert cap["prose"]["recommended_measure_ch"] == 72


def test_calc_display_capability_retro_crt_small():
    # 640x480 CRT
    cap = calc_display_capability(640, 480, device_type="retro_crt")
    assert cap["aspect_ratio"] == "4:3"
    assert cap["device_type"] == "retro_crt"
    assert cap["zen_viewport"]["scale_factor"] == 0.8
    # 640x480 cannot fit 480x500 (height 480 < 500)
    assert cap["gridcore"]["teletext_standard"]["fits_1x"] is False
    assert cap["prose"]["layout_mode"] == "compact_tablet"
    assert cap["prose"]["recommended_measure_ch"] == 60


def test_calc_display_capability_ten_foot_tv():
    cap = calc_display_capability(1280, 720)
    assert cap["aspect_ratio"] == "16:9"
    assert cap["device_type"] == "ten_foot_tv"
    assert cap["zen_viewport"]["scale_factor"] == 1.0
    assert cap["zen_viewport"]["scaled_width"] == 1280
    assert cap["zen_viewport"]["scaled_height"] == 720
    assert cap["zen_viewport"]["letterbox"]["horizontal_padding_px"] == 0
    assert cap["zen_viewport"]["letterbox"]["vertical_padding_px"] == 0


def test_calc_display_capability_mobile():
    cap = calc_display_capability(390, 844, device_type="mobile_portal")
    assert cap["aspect_ratio"] == "4:3"  # aspect < 1.5 (0.46)
    assert cap["prose"]["layout_mode"] == "mobile_reflow"
    assert cap["prose"]["recommended_measure_ch"] == 40


def test_calc_storage_capacity_live_usb():
    # 4 GB USB Flash Drive, 2.5 GB OS overhead
    cap = calc_storage_capacity(4_000_000_000, sys_bytes=2_500_000_000)
    assert cap["storage_vault_usable_bytes"] == 1_500_000_000
    assert cap["storage_vault_usable_gb"] == 1.397  # GiB
    kc = cap["knowledge_capacity"]
    assert kc["plain_prose_notes"] >= 400_000
    assert kc["indexed_notes_fts5"] >= 300_000
    assert kc["curated_bobs_gif"] >= 50_000
    assert kc["mini_capsules_10mb"] == 150
    assert kc["encyclopedia_zim_capsules_1gb"] == 1


def test_calc_storage_capacity_pos_terminal():
    # 16 GB POS Terminal
    cap = calc_storage_capacity(16_000_000_000, sys_bytes=3_500_000_000)
    assert cap["storage_vault_usable_bytes"] == 12_500_000_000
    kc = cap["knowledge_capacity"]
    assert kc["encyclopedia_zim_capsules_1gb"] == 12


def test_detect_host_display():
    w, h = detect_host_display()
    assert w > 0
    assert h > 0


def test_scan_with_geometry_and_storage(runner):
    fixture = str(FIXTURES_DIR / "clean_linux_pc.json")
    res = runner.invoke(cli, ["scan", "--fixture", fixture])
    assert res.exit_code == 0
    assert "Display & GridCore Geometry:" in res.output
    assert "Vault Knowledge & Capsule Storage Capacity:" in res.output
    assert "Square" in res.output
    assert "Teletext Standard" in res.output
    assert "Usable Vault" in res.output


def test_scan_with_custom_resolution_override(runner):
    fixture = str(FIXTURES_DIR / "clean_linux_pc.json")
    res = runner.invoke(cli, [
        "scan",
        "--fixture", fixture,
        "--resolution", "1024x768",
        "--device-type", "pos_kiosk",
        "--json",
    ])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert "display_capability" in data
    assert data["display_capability"]["resolution"]["width"] == 1024
    assert data["display_capability"]["resolution"]["height"] == 768
    assert data["display_capability"]["device_type"] == "pos_kiosk"
    assert data["display_capability"]["aspect_ratio"] == "4:3"
    assert "storage_capacity" in data
    assert data["storage_capacity"]["storage_vault_usable_bytes"] > 0


def test_doctor_with_display_and_capsule_checks(runner):
    fixture = str(FIXTURES_DIR / "clean_linux_pc.json")
    res = runner.invoke(cli, ["doctor", "--fixture", fixture, "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    probe_names = [c["probe"] for c in data["checks"]]
    assert "display_geometry" in probe_names
    assert "capsule_storage" in probe_names
    assert data["display_capability"] is not None
    assert data["storage_capacity"] is not None


def test_capsule_provisioning_recipe_plan(tmp_path):
    plan_file = tmp_path / "capsule_plan.json"
    runner = CliRunner()
    res = runner.invoke(cli, [
        "plan",
        "--target", "/dev/sdb",
        "--recipe", "capsule-provisioning",
        "--out", str(plan_file),
        "--json",
    ])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["recipe_id"] == "capsule-provisioning"
    assert len(data["steps"]) == 6

    # Test dry run apply
    res_apply = runner.invoke(cli, [
        "apply",
        "--plan", str(plan_file),
        "--confirm",
        "--json",
    ])
    assert res_apply.exit_code == 0
    report = json.loads(res_apply.output)
    assert report["status"] == "dry_run_success"
    assert report["safe_to_apply"] is True
