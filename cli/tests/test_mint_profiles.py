"""Unit tests for Linux Mint profiles and safety gates in Sonic."""

import pytest
from sonic.lib.mint_profiler import (
    create_provision_plan,
    detect_hardware_tier,
    inspect_current_system,
    inspect_hardware_compatibility,
    load_profile_spec,
)


def test_load_profile_spec():
    spec = load_profile_spec()
    assert spec["baseline"]["distribution"] == "Linux Mint"
    assert spec["baseline"]["version"] == "22"
    assert "cinnamon-full" in spec["profiles"]
    assert "xfce-light" in spec["profiles"]
    assert "pc-x86_64" in spec["hardware_tiers"]
    assert "intel-mac" in spec["hardware_tiers"]


def test_detect_hardware_tier():
    assert detect_hardware_tier("Lenovo", "ThinkPad T480", "x86_64") == "pc-x86_64"
    assert detect_hardware_tier("Apple", "MacBookPro11,1", "x86_64") == "intel-mac"
    assert detect_hardware_tier("Apple", "MacBook Pro M1", "arm64") == "apple-silicon"
    assert detect_hardware_tier("Raspberry Pi", "Raspberry Pi 5", "aarch64") == "arm-sbc"


def test_inspect_pc_high_spec():
    device = {
        "vendor": "Lenovo",
        "model": "ThinkPad X1 Carbon Gen 11",
        "arch": "x86_64",
        "ram_mb": 16384,
        "storage_gb": 512,
    }
    report = inspect_hardware_compatibility(device)
    assert report["hardware_tier"]["id"] == "pc-x86_64"
    assert report["profiles"]["cinnamon-full"]["status"] == "COMPATIBLE"
    assert report["profiles"]["xfce-light"]["status"] == "COMPATIBLE"
    assert report["preferred_profile"] == "cinnamon-full"


def test_inspect_constrained_ram_recommends_xfce():
    device = {
        "vendor": "Dell",
        "model": "OptiPlex 3020",
        "arch": "x86_64",
        "ram_mb": 2048,
        "storage_gb": 64,
    }
    report = inspect_hardware_compatibility(device)
    assert report["hardware_tier"]["id"] == "pc-x86_64"
    assert report["profiles"]["cinnamon-full"]["status"] == "INCOMPATIBLE"
    assert report["profiles"]["xfce-light"]["status"] in ("COMPATIBLE", "COMPATIBLE_WITH_WARNINGS")
    assert report["preferred_profile"] == "xfce-light"


def test_inspect_intel_mac_quirks():
    device = {
        "vendor": "Apple",
        "model": "MacBookPro11,1",
        "arch": "x86_64",
        "ram_mb": 8192,
        "storage_gb": 256,
    }
    report = inspect_hardware_compatibility(device)
    assert report["hardware_tier"]["id"] == "intel-mac"
    # Intel Mac requires Broadcom wifi and macfanctld notes
    warnings = " ".join(report.get("warnings", []))
    assert "Broadcom" in warnings
    assert "macfanctld" in warnings


def test_safety_gates_on_provisioning_plan():
    device = {
        "vendor": "Dell",
        "model": "OptiPlex 7080",
        "arch": "x86_64",
        "ram_mb": 16384,
        "storage_gb": 512,
    }

    # Gate 1: No target disk specified
    plan1 = create_provision_plan("cinnamon-full", device, target_disk=None)
    assert plan1["status"] == "dry_run_only"
    assert "target_disk required" in plan1["gate"]

    # Gate 2: Target disk provided but no confirmation
    plan2 = create_provision_plan("cinnamon-full", device, target_disk="/dev/sdb", confirm=False)
    assert plan2["status"] == "dry_run_only"
    assert "user confirmation required" in plan2["gate"]

    # Gate 3: Confirmed but no backup verified
    plan3 = create_provision_plan("cinnamon-full", device, target_disk="/dev/sdb", confirm=True, backup_verified=False)
    assert plan3["status"] == "dry_run_only"
    assert "backup verification required" in plan3["gate"]

    # Authorized plan: all gates satisfied
    plan4 = create_provision_plan("cinnamon-full", device, target_disk="/dev/sdb", confirm=True, backup_verified=True)
    assert plan4["status"] == "authorized_plan"
    assert "AUTHORIZED" in plan4["gate"]
    assert len(plan4["steps"]) > 0


def test_apple_silicon_native_host_inspection():
    device = {
        "vendor": "Apple",
        "model": "MacBook Pro M3 Max",
        "arch": "arm64",
        "ram_mb": 36864,
        "storage_gb": 1024,
    }
    report = inspect_hardware_compatibility(device)
    assert report["hardware_tier"]["id"] == "apple-silicon"
    assert report["preferred_profile"] == "native-macos-host"
    for p in report["profiles"].values():
        assert p["status"] == "HOST_NATIVE_MACOS"
    assert any("Apple Silicon" in w for w in report["warnings"])


def test_recycled_pos_kiosk_detection_and_usb_live_plan():
    assert detect_hardware_tier("NCR", "RealPOS 70XRT", "x86_64") == "recycled-pos-kiosk"
    assert detect_hardware_tier("Elo", "Touch Kiosk E-Series", "x86_64") == "recycled-pos-kiosk"

    device = {
        "vendor": "NCR",
        "model": "RealPOS 70XRT",
        "arch": "x86_64",
        "ram_mb": 4096,
        "storage_gb": 64,
    }
    plan = create_provision_plan("xfce-light", device, mode="usb-live")
    assert plan["status"] == "authorized_plan"
    assert plan["destructive"] is False
    assert "usb_live" in plan["gate"]
    assert "live persistence" in plan["message"]
    assert len(plan["steps"]) >= 4

