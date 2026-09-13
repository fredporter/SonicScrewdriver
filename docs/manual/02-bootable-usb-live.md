---
title: "Part 2: Sonic Bootable USB with Live Persistence"
level: "basic"
relevance: 90
category: "Hardware Revival"
description: "Prepare a universal bootable USB flash drive with live persistence to boot any PC non-destructively."
---

# Part 2: Sonic Bootable USB with Live Persistence

The single most powerful tool in the revival toolkit is the **Sonic Screwdriver Bootable USB Flash Drive**.

## The Universal Layer Philosophy

> [!IMPORTANT]
> **Never scrub what you don't need to scrub**: uDos is a universal layer on top of a device that does not necessarily wipe existing partitions. A bootable USB flash drive allows you to plug into an old office PC, a recycled POS terminal, or a borrowed laptop, boot directly into CMMint, and have your complete workspace ready without touching internal drives.

## How Live Persistence Works

Ordinary live USBs lose your files, settings, and documents the moment you turn off the computer.

A **Sonic Live Persistent USB** adds a persistent storage overlay:
1. **Base OS Layer (Read-Only)**: Clean, immutable Linux Mint 22 ISO verified by SHA-256.
2. **Persistence Overlay (Writable)**: Saves your personal `~/Vault`, configured Wi-Fi keys, and installed uCode capsules.
3. **Multi-Boot Compatibility**: Boots on both modern UEFI systems and legacy BIOS machines (including the Apple EFI picker on older Intel Macs by holding Option/Alt at chime).

## Preparing the Drive with Sonic

1. Insert a fast USB 3.0 or USB-C flash drive (16GB or 32GB recommended).
2. Use Sonic's non-destructive USB mode:
   ```bash
   sonic profile plan xfce-light --mode usb-live
   ```
3. Sonic validates the local ISO image from the local offline depot (`Code/Vendor/01-RAW` or `UDOS_HOME/depot`), verifies integrity, and structures the drive with live persistence.

You now possess a pocketable, sovereign operating system that can boot any recycled computer into a modern workstation in under 30 seconds.
