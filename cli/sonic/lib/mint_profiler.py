"""Linux Mint Hardware Profiler and Safety Gate Enforcement.

Per uDOS Product Refactor Plan Section 11:
- Pinned Linux Mint 22 (Wilma) baseline.
- Two qualified desktop profiles: cinnamon-full and xfce-light.
- Hardware tiers: PC x86-64, older Intel Mac (2012-2015), and ARM tracked separately.
- Strict separation between read-only inspect, disk writes, and firmware flashing.
"""

from __future__ import annotations

import os
import platform
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class ProfileError(Exception):
    """Base exception for Mint profile operations."""


class SafetyGateViolation(ProfileError):
    """Raised when an operation attempts to bypass a required safety gate."""


def get_profiles_yaml_path() -> Path:
    return Path(__file__).parent.parent / "data" / "profiles" / "mint_profiles.yaml"


def load_profile_spec() -> Dict[str, Any]:
    p_path = get_profiles_yaml_path()
    if not p_path.exists():
        raise ProfileError(f"Profiles specification not found: {p_path}")
    with open(p_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def detect_hardware_tier(vendor: str, model: str, arch: str) -> str:
    """Classify hardware into qualified hardware tiers."""
    vendor_lower = vendor.lower()
    model_lower = model.lower()
    arch_lower = arch.lower()

    if "pos" in model_lower or "kiosk" in model_lower or "pos" in vendor_lower:
        return "recycled-pos-kiosk"

    if "apple" in vendor_lower or "macbook" in model_lower or "mac mini" in model_lower:
        if arch_lower in ("x86_64", "amd64", "intel"):
            return "intel-mac"
        # Apple silicon handled separately
        return "apple-silicon"

    if arch_lower in ("aarch64", "arm64", "armv7l", "armv8"):
        return "arm-sbc"

    if arch_lower in ("x86_64", "amd64"):
        return "pc-x86_64"

    return "unknown"


def inspect_hardware_compatibility(
    device_info: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate device compatibility against Linux Mint profiles without modifying any system state."""
    spec = load_profile_spec()
    profiles = spec.get("profiles", {})
    hardware_tiers = spec.get("hardware_tiers", {})

    vendor = device_info.get("vendor", "Unknown")
    model = device_info.get("model", "Unknown")
    arch = device_info.get("arch", "x86_64")
    ram_mb = int(device_info.get("ram_mb", 0))
    storage_gb = int(device_info.get("storage_gb", 0))

    tier_id = detect_hardware_tier(vendor, model, arch)
    tier_info = hardware_tiers.get(tier_id, {})

    results = {}
    recommendations: List[str] = []
    warnings: List[str] = []

    if tier_id == "unknown":
        warnings.append(f"Unrecognized hardware tier for architecture '{arch}'. Manual verification required.")
    elif tier_id == "intel-mac":
        warnings.append("Intel Mac tier detected: Broadcom Wi-Fi driver and macfanctld fan daemon required.")
        if "driver_notes" in tier_info:
            warnings.extend(tier_info["driver_notes"])
    elif tier_id == "arm-sbc":
        warnings.append("ARM Single Board Computer tier detected: experimental image required.")

    if tier_id == "apple-silicon":
        warnings.append("Apple Silicon Mac detected: uDos/uCore runs natively directly on macOS. Linux/CMMint installation is not required or recommended.")
        for p_id, p_spec in profiles.items():
            results[p_id] = {
                "title": p_spec.get("title"),
                "status": "HOST_NATIVE_MACOS",
                "compatible": False,
                "notes": ["M-series Apple Silicon runs uDos natively on macOS; Linux installation is not needed."],
                "min_ram_mb": p_spec.get("min_ram_mb", 2048),
                "min_disk_gb": p_spec.get("min_disk_gb", 15),
            }
        preferred_profile = "native-macos-host"
    else:
        for p_id, p_spec in profiles.items():
            min_ram = p_spec.get("min_ram_mb", 2048)
            rec_ram = p_spec.get("recommended_ram_mb", 4096)
            min_disk = p_spec.get("min_disk_gb", 15)
            supported_tiers = p_spec.get("supported_hardware_tiers", [])

            reasons = []
            compatible = True

            if tier_id not in supported_tiers:
                compatible = False
                reasons.append(f"Hardware tier '{tier_id}' is not in supported tiers: {supported_tiers}")

            if ram_mb > 0 and ram_mb < min_ram:
                compatible = False
                reasons.append(f"Insufficient RAM ({ram_mb} MB); minimum required is {min_ram} MB")
            elif ram_mb > 0 and ram_mb < rec_ram:
                reasons.append(f"RAM ({ram_mb} MB) below recommended {rec_ram} MB; may experience swap usage")

            if storage_gb > 0 and storage_gb < min_disk:
                compatible = False
                reasons.append(f"Insufficient storage ({storage_gb} GB); minimum required is {min_disk} GB")

            status = "COMPATIBLE" if compatible else "INCOMPATIBLE"
            if compatible and reasons:
                status = "COMPATIBLE_WITH_WARNINGS"

            results[p_id] = {
                "title": p_spec.get("title"),
                "status": status,
                "compatible": compatible,
                "notes": reasons,
                "min_ram_mb": min_ram,
                "min_disk_gb": min_disk,
            }

            if compatible:
                recommendations.append(p_id)

        # Pick top recommendation
        preferred_profile = None
        if "cinnamon-full" in recommendations and ram_mb >= 4096:
            preferred_profile = "cinnamon-full"
        elif "xfce-light" in recommendations:
            preferred_profile = "xfce-light"
        elif recommendations:
            preferred_profile = recommendations[0]

    return {
        "device": {
            "vendor": vendor,
            "model": model,
            "arch": arch,
            "ram_mb": ram_mb,
            "storage_gb": storage_gb,
        },
        "hardware_tier": {
            "id": tier_id,
            "name": tier_info.get("name", "Unknown Architecture"),
            "verified_features": tier_info.get("verified_features", []),
            "known_limits": tier_info.get("known_limits", ""),
        },
        "baseline": spec.get("baseline", {}),
        "profiles": results,
        "preferred_profile": preferred_profile,
        "warnings": warnings,
        "safety_gate": "inspect (read-only, non-destructive)",
    }


def inspect_current_system() -> Dict[str, Any]:
    """Inspect local running system hardware."""
    uname = platform.uname()
    arch = uname.machine

    # Memory in MB
    ram_mb = 4096
    try:
        if hasattr(os, "sysconf") and "SC_PAGE_SIZE" in os.sysconf_names and "SC_PHYS_PAGES" in os.sysconf_names:
            ram_mb = (os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")) // (1024 * 1024)
    except Exception:
        pass

    # Disk in GB
    storage_gb = 50
    try:
        usage = shutil.disk_usage(Path.home())
        storage_gb = usage.total // (1024 * 1024 * 1024)
    except Exception:
        pass

    device_info = {
        "vendor": "Apple" if "darwin" in platform.system().lower() else "Generic",
        "model": platform.platform(),
        "arch": arch,
        "ram_mb": ram_mb,
        "storage_gb": storage_gb,
    }
    return inspect_hardware_compatibility(device_info)


def create_provision_plan(
    profile_id: str,
    device_info: Dict[str, Any],
    target_disk: Optional[str] = None,
    confirm: bool = False,
    backup_verified: bool = False,
    mode: str = "provision",
) -> Dict[str, Any]:
    """Generate a provision plan with strict safety gate validation."""
    spec = load_profile_spec()
    profiles = spec.get("profiles", {})
    if profile_id not in profiles:
        raise ProfileError(f"Unknown profile: '{profile_id}'. Available: {list(profiles.keys())}")

    p_spec = profiles[profile_id]

    # Non-destructive USB Live Mode
    if mode in ("usb-live", "usb"):
        target_usb = target_disk or "/dev/diskX (USB Flash Drive)"
        return {
            "status": "authorized_plan",
            "gate": "usb_live (AUTHORIZED: non-destructive)",
            "mode": "usb-live",
            "profile": profile_id,
            "target_disk": target_usb,
            "destructive": False,
            "message": "Prepared bootable USB flash drive with live persistence. Non-destructive universal layer; preserves host disks.",
            "steps": [
                f"Format USB target {target_usb} with hybrid MBR/GPT live partition layout",
                f"Install Linux Mint 22 ({p_spec.get('title')}) image to USB depot",
                "Enable overlay persistence partition for writable user workspace",
                "Preload uDos runtime layer and GridCore into persistence image",
                "Verify bootloader compatibility (UEFI/BIOS/Apple-EFI picker)",
            ],
        }

    # Safety Gate Check
    if not target_disk:
        return {
            "status": "dry_run_only",
            "gate": "provision (BLOCKED: target_disk required)",
            "message": "Provisioning requires explicit --target-disk parameter. No changes made.",
            "profile": profile_id,
            "target_disk": None,
            "allowed_actions": ["inspect", "plan"],
        }

    if not confirm:
        return {
            "status": "dry_run_only",
            "gate": "provision (BLOCKED: user confirmation required)",
            "message": f"Target disk '{target_disk}' would be overwritten. Pass --confirm to authorize.",
            "profile": profile_id,
            "target_disk": target_disk,
            "destructive": True,
        }

    if not backup_verified:
        return {
            "status": "dry_run_only",
            "gate": "provision (BLOCKED: backup verification required)",
            "message": "Partition table backup must be verified before disk writes.",
            "profile": profile_id,
            "target_disk": target_disk,
            "destructive": True,
        }

    return {
        "status": "authorized_plan",
        "gate": "provision (AUTHORIZED)",
        "profile": profile_id,
        "target_disk": target_disk,
        "steps": [
            f"Write partition table (GPT) on {target_disk}",
            f"Create EFI system partition (512MB FAT32)",
            f"Create root partition (ext4) with {p_spec.get('title')}",
            f"Install baseline packages: {p_spec.get('preinstalled_packages')}",
            f"Configure desktop environment: {p_spec.get('desktop_environment')}",
        ],
    }
