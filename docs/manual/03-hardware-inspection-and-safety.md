---
title: "Part 3: Hardware Diagnostics, Classification Tiers & Safety Gates"
level: "intermediate"
relevance: 85
category: "Hardware Revival"
description: "Understand hardware tiers, safety gates, and how Sonic prevents accidental data destruction."
---

# Part 3: Hardware Diagnostics, Classification Tiers & Safety Gates

When working with recycled computers and physical hardware, safety discipline is paramount. Sonic Screwdriver enforces strict programmatic **safety gates** to ensure you never accidentally overwrite personal documents or firmware.

## Hardware Classification Tiers

Sonic automatically categorizes connected machines into known hardware tiers:

| Tier ID | Description | Verified Features & Quirks |
|---|---|---|
| `apple-silicon` | Modern Mac (M1–M4) | **Native macOS host**. Runs uDos directly on macOS; Linux install blocked. |
| `pc-x86_64` | Standard x86-64 PC | UEFI/BIOS boot, Intel/Realtek Ethernet/Wi-Fi, standard displays. |
| `intel-mac` | Intel MacBook/Mac Mini (2012–2015) | Retina scaling, Apple backlight, requires Broadcom Wi-Fi driver & `macfanctld`. |
| `recycled-pos-kiosk` | Recycled Terminals & Kiosks | Touchscreen calibration, low-power Atom/Celeron, serial barcode/scales. |
| `arm-sbc` | Single-board computers | Raspberry Pi, custom device trees, GPIO control. |

## The Three Safety Gates

Sonic classifies every operation into three distinct authorization gates:

### Gate 1: Inspect (Read-Only)
- **Privilege**: User (no root required).
- **Risk**: None.
- **Action**: Queries system parameters, CPU flags, and disk topology without writing a single byte to disk.

### Gate 2: USB Live (Non-Destructive Target)
- **Privilege**: User / standard write.
- **Risk**: Low (writes only to the selected removable USB media).
- **Action**: Partitions and writes live persistence to flash media while leaving internal SSDs/HDDs completely untouched.

### Gate 3: Provision / Disk Write (Destructive)
- **Privilege**: Root / Superuser.
- **Risk**: High (overwrites internal drive).
- **Enforcement**: Programmatically blocked unless:
  1. An explicit `--target-disk` is declared.
  2. The `--confirm` flag is passed.
  3. A verified partition table backup exists (`--backup-verified`).
