"""Universal Device Display and Container Storage Capability Calculator for Sonic Screwdriver.

Implements authoritative mathematical formulas from:
- global-knowledge/standards/DEVICE-DISPLAY-STANDARDS.md
- global-knowledge/standards/CONTAINER-STANDARDS.md
"""
from __future__ import annotations

import re
import subprocess
import sys
from typing import Any, Dict, Optional, Tuple


def calc_display_capability(
    width: int,
    height: int,
    device_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate display capabilities, character grid capacity, reading measure,
    and Zen viewport scaling for a given screen resolution.
    """
    w = max(1, int(width))
    h = max(1, int(height))
    aspect_ratio_val = w / h

    # Determine reference aspect and canvas
    if aspect_ratio_val < 1.5:
        target_aspect = "4:3"
        ref_w, ref_h = 800, 600
    else:
        target_aspect = "16:9"
        ref_w, ref_h = 1280, 720

    scale_factor = round(min(w / ref_w, h / ref_h), 3)

    # GridCore Cell Algebra
    # Atomic Dot: 1 dot = 4x4 px
    sq_cols = w // 8
    sq_rows = h // 8
    tall_cols = w // 12
    tall_rows = h // 20
    super_cols = w // 24
    super_rows = h // 40

    fits_teletext_1x = (w >= 480) and (h >= 500)
    fits_teletext_2x = (w >= 960) and (h >= 1000)

    # Prose Line Measure
    # Standard character measure: 1ch approx 0.6 * 16px = 9.6px
    char_capacity = int(w / 9.6)
    if w < 480:
        layout_mode = "mobile_reflow"
        recommended_measure_ch = 40
        max_width_px = w
    elif w < 768:
        layout_mode = "compact_tablet"
        recommended_measure_ch = 60
        max_width_px = min(w - 32, 580)
    else:
        layout_mode = "optimal_zen"
        recommended_measure_ch = 72
        max_width_px = 680

    # BOB Blitter Object Memory Budget
    # Typical 64x64 BOB with 12 frames at 1 byte/pixel (indexed palette)
    typical_bob_ram = 64 * 64 * 12 * 1

    # Classify profile ID if not explicitly provided
    detected_profile = device_type
    if not detected_profile or detected_profile == "auto":
        if w >= 1920 and h >= 1080 and aspect_ratio_val >= 1.5:
            detected_profile = "desktop_hd"
        elif target_aspect == "4:3" and w <= 1024 and h <= 768:
            detected_profile = "pos_kiosk"
        elif target_aspect == "4:3":
            detected_profile = "retro_crt"
        elif aspect_ratio_val >= 1.7:
            detected_profile = "ten_foot_tv"
        else:
            detected_profile = "desktop_hd"

    return {
        "resolution": {"width": w, "height": h},
        "aspect_ratio": target_aspect,
        "aspect_ratio_ratio": round(aspect_ratio_val, 2),
        "device_type": detected_profile,
        "gridcore": {
            "dot_px": 4,
            "square_register": {"cols": sq_cols, "rows": sq_rows, "cell_px": "8x8"},
            "tall_register": {"cols": tall_cols, "rows": tall_rows, "cell_px": "12x20"},
            "super_cells": {"cols": super_cols, "rows": super_rows, "tile_px": "24x40"},
            "teletext_standard": {
                "required_px": "480x500",
                "fits_1x": fits_teletext_1x,
                "fits_2x": fits_teletext_2x,
            },
        },
        "prose": {
            "char_capacity_ch": char_capacity,
            "layout_mode": layout_mode,
            "recommended_measure_ch": recommended_measure_ch,
            "max_width_px": max_width_px,
        },
        "zen_viewport": {
            "target_aspect": target_aspect,
            "reference_resolution": {"width": ref_w, "height": ref_h},
            "scale_factor": scale_factor,
            "scaled_width": int(ref_w * scale_factor),
            "scaled_height": int(ref_h * scale_factor),
            "letterbox": {
                "horizontal_padding_px": max(0, (w - int(ref_w * scale_factor)) // 2),
                "vertical_padding_px": max(0, (h - int(ref_h * scale_factor)) // 2),
            },
        },
        "bob_budget": {
            "max_dimensions_px": {"width": 128, "height": 128},
            "typical_dimensions_px": {"width": 64, "height": 64},
            "max_frames": 24,
            "recommended_fps": 12,
            "typical_ram_bytes": typical_bob_ram,
            "max_file_size_kb": 60,
        },
    }


def calc_storage_capacity(
    total_bytes: int,
    sys_bytes: Optional[int] = None,
) -> Dict[str, Any]:
    """Calculate usable vault knowledge capacity, indexed search capacity,
    and capsule budgets for a given storage size.
    """
    total = max(0, int(total_bytes))
    # Default system overhead: 2.5 GB for base Linux/CMMint + uCore runtime
    overhead = int(sys_bytes if sys_bytes is not None else 2_500_000_000)
    usable_vault = max(0, total - overhead)

    # Document & Asset density metrics
    plain_note_bytes = 3_500
    fts5_indexed_note_bytes = 4_900  # 1.4x
    bob_asset_bytes = 25_000
    mini_capsule_bytes = 10_000_000  # 10 MB
    zim_capsule_bytes = 1_000_000_000  # 1 GB

    return {
        "storage_total_bytes": total,
        "storage_system_bytes": overhead,
        "storage_vault_usable_bytes": usable_vault,
        "storage_vault_usable_mb": round(usable_vault / (1024 * 1024), 2),
        "storage_vault_usable_gb": round(usable_vault / (1024 * 1024 * 1024), 3),
        "knowledge_capacity": {
            "plain_prose_notes": usable_vault // plain_note_bytes,
            "indexed_notes_fts5": usable_vault // fts5_indexed_note_bytes,
            "curated_bobs_gif": usable_vault // bob_asset_bytes,
            "mini_capsules_10mb": usable_vault // mini_capsule_bytes,
            "encyclopedia_zim_capsules_1gb": usable_vault // zim_capsule_bytes,
        },
    }


def detect_host_display() -> Tuple[int, int]:
    """Detect current host screen resolution non-destructively.

    Returns (width, height), falling back to 1920x1080 if headless or undetected.
    """
    # 1. Try xrandr on Linux
    if sys.platform.startswith("linux"):
        try:
            res = subprocess.run(
                ["xrandr"],
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
            )
            if res.returncode == 0:
                # Match lines like "HDMI-1 connected primary 1920x1080+0+0" or "   1920x1080    60.00*"
                m = re.search(r"(\d{3,4})x(\d{3,4})\*?", res.stdout)
                if m:
                    return int(m.group(1)), int(m.group(2))
        except Exception:
            pass

        # 2. Try DRM sysfs modes on Linux
        try:
            from pathlib import Path
            for mode_file in Path("/sys/class/drm").glob("card*-*/modes"):
                if mode_file.is_file():
                    content = mode_file.read_text().strip()
                    lines = content.splitlines()
                    if lines:
                        m = re.match(r"^(\d{3,4})x(\d{3,4})", lines[0].strip())
                        if m:
                            return int(m.group(1)), int(m.group(2))
        except Exception:
            pass

        # 3. Try framebuffer virtual_size
        try:
            from pathlib import Path
            fb_file = Path("/sys/class/graphics/fb0/virtual_size")
            if fb_file.is_file():
                w_str, h_str = fb_file.read_text().strip().split(",")
                return int(w_str), int(h_str)
        except Exception:
            pass

    # 4. Try macOS system_profiler if running on darwin
    if sys.platform == "darwin":
        try:
            res = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True,
                text=True,
                timeout=3.0,
                check=False,
            )
            if res.returncode == 0:
                m = re.search(r"Resolution:\s*(\d+)\s*x\s*(\d+)", res.stdout)
                if m:
                    return int(m.group(1)), int(m.group(2))
        except Exception:
            pass

    # Default fallback: standard 1080p
    return 1920, 1080
