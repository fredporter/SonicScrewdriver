---
title: "Part 4: Recycled Tech & Physical Robotics"
level: "intermediate"
relevance: 85
category: "Hardware Revival"
description: "Repurpose decommissioned POS peripherals, touchscreens, and motors for robotics using the uDos way."
---

# Part 4: Recycled Tech & Physical Robotics

Recycled technology is filled with robust industrial components: high-torque stepper motors from old receipt printers, resistive and capacitive touchscreens from checkout counters, RS-232 serial interfaces, and sturdy 12V/24V power supplies.

## The uDos Way for Physical Computing

In standard hobbyist setups, students are often forced to install complex multi-gigabyte Python environments, battle Linux device drivers, and troubleshoot finicky Wi-Fi connection scripts.

Under the **uDos way**:
1. **Sonic handles hardware discovery**: Plug in a USB-to-serial adapter or recycled POS peripheral, and Sonic detects the chip (FTDI, CH340, CP2102) and announces the device over local mDNS.
2. **uCore-Networking manages the link**: Whether connecting over Bluetooth Serial or private LAN Wi-Fi, uCore-Networking pairs the device cleanly without requiring manual IP address or subnet configuration.
3. **uCode / BBC BASIC drives the logic**: You write straightforward, readable control loops in BBC BASIC:
   ```basic
   10 REM Drive Recycled Stepper Motor
   20 OPEN#1, "SER:9600"
   30 FOR S% = 1 TO 200
   40   PRINT#1, "STEP 1"
   50   WAIT 10
   60 NEXT S%
   70 CLOSE#1
   ```

No external cloud accounts, no fragile Python package collisions—just sovereign hardware running reliably with simple, traditional code.
