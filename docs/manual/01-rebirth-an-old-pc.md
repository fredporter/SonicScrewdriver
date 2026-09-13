---
title: "Part 1: Rebirthing an Old PC, Kiosk, or POS Terminal"
level: "basic"
relevance: 90
category: "Hardware Revival"
description: "How to rescue older computers and recycled terminals into modern sovereign workstations using Sonic."
---

# Part 1: Rebirthing an Old PC, Kiosk, or POS Terminal

Millions of fully functional computers are discarded every year simply because commercial operating systems bloat beyond what older processors and memory can sustain. 

With **Sonic Screwdriver** and **Classic Modern Mint (CMMint)**, you can give these machines a second life as fast, reliable, and beautiful workstations.

## Why We Don't Setup Windows or Proprietary Clouds

In the uDos ecosystem, we do not teach "how to setup a Windows machine and install Microsoft Office". Why?
1. Commercial cloud operating systems demand constant telemetry, forced updates, and planned obsolescence.
2. Older PCs (2012–2018), decommissioned point-of-sale (POS) terminals, and library kiosks have perfectly capable multi-core CPUs, durable metal chassis, and decent RAM.
3. By layering a sovereign universal OS on top, the machine becomes faster than the day it was bought, runs completely offline, and connects seamlessly to local vaults.

## The Two Revival Profiles

Sonic maintains two pinned, verified Linux Mint 22 profiles:

1. **Cinnamon (Full Workstation)**:
   - Requires: 4GB+ RAM, 20GB storage.
   - Ideal for: Core i5/i7 desktops, ThinkPads, older Intel MacBooks (2012–2015).
   - Features: Full 3D visual compositing, modern dock, complete multimedia and uCode suite.

2. **Xfce (Lightweight Revival)**:
   - Requires: 2GB to 4GB RAM, 15GB storage.
   - Ideal for: Atom/Celeron POS terminals, interactive kiosks, netbooks, workshop machines.
   - Features: Ultra-lean 2D window manager, instant responsiveness, minimal RAM idle (<600MB).

## Step-by-Step Hardware Inspection

Before making any changes to a machine, Sonic uses a strict **read-only inspection gate**:

```bash
# On the target machine, run a non-destructive hardware scan
sonic profile inspect
```

Sonic checks CPU architecture, total physical RAM, storage capacity, and hardware quirks (like Broadcom Wi-Fi chips on older Macs or touchscreen drivers on POS units). It immediately outputs a recommendation:

```
=== Linux Mint Profile Compatibility Assessment ===
Device: Lenovo ThinkPad T480 (x86_64)
Specs: 8192 MB RAM, 256 GB Storage
Classified Hardware Tier: pc-x86_64 (Standard PC x86-64)

Profile Compatibility Results:
  [COMPATIBLE] cinnamon-full - Linux Mint 22 Cinnamon (Full Workstation)
  [COMPATIBLE] xfce-light - Linux Mint 22 Xfce (Lightweight Revival)

Recommended Profile: cinnamon-full
```
