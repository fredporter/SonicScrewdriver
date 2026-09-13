---
title: "The Sonic Hardware Revival & Universal OS Guide"
level: "basic"
relevance: 95
category: "Hardware Revival"
description: "Learn to rebirth older PCs, kiosks, and recycled hardware into sovereign workstations using Sonic Screwdriver and Linux/CMMint."
---

# The Sonic Hardware Revival & Universal OS Guide

Welcome to the **Sonic Screwdriver Hardware Revival Guide**. This course teaches you how to rescue older PCs, decommissioned POS terminals, interactive kiosks, and older Intel Macs, rebirthing them into modern, resilient, sovereign workstations.

## The Core Doctrine: Non-Destructive Universal Layer

- **Modern Apple Silicon Macs (M-series)**: Run uDos and uCore natively on macOS. Linux installation is not required.
- **Older Machines & Everything Else**: A Sonic-prepared bootable USB flash drive preconfigured with Linux/CMMint (`cinnamon-full` or `xfce-light`) is the universal OS standard.
- **Non-Destructive**: uDos is a universal layer on top of hardware that does not necessarily scrub what was there before. Live USB persistence keeps your personal workspace portable without wiping existing drives.

---

## Course Syllabus

| Part | Title | Focus & Key Concepts | Level |
|---|---|---|---|
| **[Part 1: Rebirthing an Old PC](01-rebirth-an-old-pc.md)** | Rebirthing an Old PC or Kiosk | Rescuing obsolete hardware, understanding RAM/CPU requirements | Beginner |
| **[Part 2: Bootable USB with Live Persistence](02-bootable-usb-live.md)** | The Universal Bootable USB | Preparing a non-destructive CMMint USB flash drive with live persistence | Basic |
| **[Part 3: Hardware Diagnostics & Safety](03-hardware-inspection-and-safety.md)** | Hardware Inspection & Safety Gates | Safe read-only inspection, device classification, and gate enforcement | Intermediate |
| **[Part 4: Recycled Tech & Robotics](04-recycled-tech-robotics.md)** | Recycled Tech & Robotics | Interfacing recycled POS touchscreens, serial sensors, and motors | Intermediate |

---

## Quick Reference Commands

- `sonic profile inspect` — Safe read-only assessment of current hardware.
- `sonic profile inspect --device <catalog-id>` — Check compatibility for a cataloged machine.
- `sonic depot list` — Enumerate verified offline ISOs, packages, and capsules.
- `sonic depot serve --port 8088` — Serve depot artifacts across the LAN to save bandwidth.
