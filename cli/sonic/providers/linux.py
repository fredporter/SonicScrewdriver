"""Real read-only Linux hardware discovery provider."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import platform
import re
import subprocess
import sys
import time
from typing import Any

from sonic.lib.catalog import DeviceModel
from sonic.lib.device_calc import (
    calc_display_capability,
    calc_storage_capacity,
    detect_host_display,
)
from sonic.providers.base import (
    BaseProvider,
    NormalizedDevice,
    ProbeResult,
    ProbeStatus,
    ScanReport,
    ScanStatus,
)

PROBE_TIMEOUT_SECONDS = 5.0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _match_catalog_models(
    device: NormalizedDevice, catalog: dict[str, DeviceModel] | None
) -> list[str]:
    if not catalog:
        return []
    candidates: list[str] = []
    hid = device.hardware_id.lower()
    vendor_lower = (device.vendor or "").lower()
    product_lower = (device.product or "").lower()

    for model_id, model in catalog.items():
        # Check if hardware_id or vendor/model appears in model definition or legacy claims
        model_vendor = model.vendor.lower()
        model_name = model.model.lower()
        legacy = model.legacy_claims

        # Exact ID match in legacy claims
        claimed_ids = [str(x).lower() for x in legacy.get("hardware_ids", [])]
        if hid in claimed_ids:
            candidates.append(model_id)
            continue

        # Substring/heuristic candidate matching
        if model_vendor in vendor_lower and model_name in product_lower:
            candidates.append(model_id)

    return sorted(set(candidates))


class LinuxProvider(BaseProvider):
    def __init__(self, timeout: float = PROBE_TIMEOUT_SECONDS):
        self.timeout = timeout

    def scan(self, catalog: dict[str, DeviceModel] | None = None) -> ScanReport:
        observed_at = _utc_now_iso()
        exec_host = platform.node() or "unknown"
        current_platform = sys.platform

        if not current_platform.startswith("linux"):
            unsupported_probe = ProbeResult(
                probe="host_platform",
                tool="os_detector",
                tool_version=platform.release(),
                status="unsupported",
                duration_ms=0.0,
                error=f"Linux discovery provider is not supported on platform '{current_platform}'. Real hardware probes require Linux.",
                device_count=0,
            )
            return ScanReport(
                schema_version=1,
                platform=current_platform,
                execution_host=exec_host,
                observed_at=observed_at,
                overall_status="unsupported",
                probes=[unsupported_probe],
                devices=[],
            )

        probes: list[ProbeResult] = []
        devices: list[NormalizedDevice] = []

        # Probe 1: USB
        usb_probe, usb_devices = self._probe_usb()
        probes.append(usb_probe)
        devices.extend(usb_devices)

        # Probe 2: PCI
        pci_probe, pci_devices = self._probe_pci()
        probes.append(pci_probe)
        devices.extend(pci_devices)

        # Probe 3: Block storage
        block_probe, block_devices = self._probe_block()
        probes.append(block_probe)
        devices.extend(block_devices)

        # Correlate candidates
        for dev in devices:
            dev.model_candidates = _match_catalog_models(dev, catalog)

        # Calculate overall status
        ok_count = sum(1 for p in probes if p.status == "ok")
        if ok_count == len(probes):
            overall: ScanStatus = "ok"
        elif ok_count > 0:
            overall = "partial"
        else:
            overall = "failed"

        # Calculate display and storage capabilities
        w, h = detect_host_display()
        display_cap = calc_display_capability(w, h)
        total_block_bytes = sum(dev.size_bytes for dev in devices if dev.bus == "block" and dev.size_bytes)
        storage_cap = calc_storage_capacity(total_block_bytes or 16_000_000_000)

        return ScanReport(
            schema_version=1,
            platform=current_platform,
            execution_host=exec_host,
            observed_at=observed_at,
            overall_status=overall,
            probes=probes,
            devices=devices,
            display_capability=display_cap,
            storage_capacity=storage_cap,
        )

    def _run_tool(self, argv: list[str]) -> tuple[str | None, ProbeStatus, str | None, float]:
        start = time.perf_counter()
        try:
            res = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                shell=False,
                check=False,
            )
            duration_ms = round((time.perf_counter() - start) * 1000.0, 2)
            if res.returncode != 0:
                err = res.stderr.strip() or f"Process exited with code {res.returncode}"
                status: ProbeStatus = "permission-denied" if "permission denied" in err.lower() else "failed"
                return None, status, err, duration_ms
            return res.stdout, "ok", None, duration_ms
        except FileNotFoundError:
            duration_ms = round((time.perf_counter() - start) * 1000.0, 2)
            return None, "missing-tool", f"Executable '{argv[0]}' not found in PATH", duration_ms
        except subprocess.TimeoutExpired:
            duration_ms = round((time.perf_counter() - start) * 1000.0, 2)
            return None, "timeout", f"Probe timed out after {self.timeout}s", duration_ms
        except PermissionError as exc:
            duration_ms = round((time.perf_counter() - start) * 1000.0, 2)
            return None, "permission-denied", str(exc), duration_ms
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000.0, 2)
            return None, "failed", str(exc), duration_ms

    def _probe_usb(self) -> tuple[ProbeResult, list[NormalizedDevice]]:
        stdout, status, error, duration = self._run_tool(["lsusb"])
        if status != "ok" or stdout is None:
            return (
                ProbeResult(
                    probe="usb",
                    tool="lsusb",
                    status=status,
                    duration_ms=duration,
                    error=error,
                    device_count=0,
                ),
                [],
            )

        devices, parse_error = self.parse_lsusb(stdout)
        if parse_error:
            return (
                ProbeResult(
                    probe="usb",
                    tool="lsusb",
                    status="parse-error",
                    duration_ms=duration,
                    error=parse_error,
                    device_count=0,
                ),
                [],
            )

        return (
            ProbeResult(
                probe="usb",
                tool="lsusb",
                status="ok",
                duration_ms=duration,
                device_count=len(devices),
            ),
            devices,
        )

    def _probe_pci(self) -> tuple[ProbeResult, list[NormalizedDevice]]:
        stdout, status, error, duration = self._run_tool(["lspci", "-nnmm"])
        if status != "ok" or stdout is None:
            return (
                ProbeResult(
                    probe="pci",
                    tool="lspci",
                    status=status,
                    duration_ms=duration,
                    error=error,
                    device_count=0,
                ),
                [],
            )

        devices, parse_error = self.parse_lspci(stdout)
        if parse_error:
            return (
                ProbeResult(
                    probe="pci",
                    tool="lspci",
                    status="parse-error",
                    duration_ms=duration,
                    error=parse_error,
                    device_count=0,
                ),
                [],
            )

        return (
            ProbeResult(
                probe="pci",
                tool="lspci",
                status="ok",
                duration_ms=duration,
                device_count=len(devices),
            ),
            devices,
        )

    def _probe_block(self) -> tuple[ProbeResult, list[NormalizedDevice]]:
        argv = ["lsblk", "-J", "-b", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,MODEL,SERIAL,TRAN"]
        stdout, status, error, duration = self._run_tool(argv)
        if status != "ok" or stdout is None:
            return (
                ProbeResult(
                    probe="block",
                    tool="lsblk",
                    status=status,
                    duration_ms=duration,
                    error=error,
                    device_count=0,
                ),
                [],
            )

        devices, parse_error = self.parse_lsblk(stdout)
        if parse_error:
            return (
                ProbeResult(
                    probe="block",
                    tool="lsblk",
                    status="parse-error",
                    duration_ms=duration,
                    error=parse_error,
                    device_count=0,
                ),
                [],
            )

        return (
            ProbeResult(
                probe="block",
                tool="lsblk",
                status="ok",
                duration_ms=duration,
                device_count=len(devices),
            ),
            devices,
        )

    @classmethod
    def parse_lsusb(cls, output: str) -> tuple[list[NormalizedDevice], str | None]:
        devices: list[NormalizedDevice] = []
        # Matches: Bus 001 Device 002: ID 046d:c52b Logitech, Inc. Unifying Receiver
        pattern = re.compile(
            r"^Bus\s+(\d+)\s+Device\s+(\d+):\s+ID\s+([0-9a-fA-F]{4}):([0-9a-fA-F]{4})(?:\s+(.*))?$"
        )
        for line in output.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            match = pattern.match(line)
            if not match:
                # If output contains non-matching garbled text, report parse error
                if not line.startswith("Bus "):
                    return [], f"Malformed lsusb line: {line[:50]}"
                continue
            bus_num, dev_num, vid, pid, desc = match.groups()
            vid = vid.lower()
            pid = pid.lower()
            desc = (desc or "").strip()
            vendor = vid
            product = pid
            if desc:
                parts = desc.split(None, 1)
                vendor = parts[0]
                product = parts[1] if len(parts) > 1 else desc

            devices.append(
                NormalizedDevice(
                    bus="usb",
                    hardware_id=f"usb:{vid}:{pid}",
                    vendor=vendor,
                    product=product,
                    device_node=f"/dev/bus/usb/{bus_num}/{dev_num}",
                )
            )
        return devices, None

    @classmethod
    def parse_lspci(cls, output: str) -> tuple[list[NormalizedDevice], str | None]:
        devices: list[NormalizedDevice] = []
        # In lspci -nnmm, each stanza is separated by empty lines or contains key-value pairs
        # e.g.:
        # Slot:\t00:1f.6
        # Class:\tEthernet controller [0200]
        # Vendor:\tIntel Corporation [8086]
        # Device:\tEthernet Connection [15b8]
        # SVendor:\tASUSTeK Computer Inc. [1043]
        # SDevice:\tDevice [8672]
        stanzas = [s.strip() for s in re.split(r"\n\s*\n", output.strip()) if s.strip()]
        for stanza in stanzas:
            data: dict[str, str] = {}
            for line in stanza.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    data[k.strip().lower()] = v.strip().strip('"')

            if "slot" not in data:
                continue

            vendor_val = data.get("vendor", "")
            device_val = data.get("device", "")
            svendor_val = data.get("svendor", "")
            sdevice_val = data.get("sdevice", "")

            # Extract [vendor_id] and [device_id]
            v_match = re.search(r"\[([0-9a-fA-F]{4})\]", vendor_val)
            d_match = re.search(r"\[([0-9a-fA-F]{4})\]", device_val)
            sv_match = re.search(r"\[([0-9a-fA-F]{4})\]", svendor_val)
            sd_match = re.search(r"\[([0-9a-fA-F]{4})\]", sdevice_val)

            vid = v_match.group(1).lower() if v_match else "0000"
            did = d_match.group(1).lower() if d_match else "0000"
            subsystem = None
            if sv_match and sd_match:
                subsystem = f"{sv_match.group(1).lower()}:{sd_match.group(1).lower()}"

            clean_vendor = re.sub(r"\s*\[[0-9a-fA-F]{4}\]", "", vendor_val).strip() or vid
            clean_product = re.sub(r"\s*\[[0-9a-fA-F]{4}\]", "", device_val).strip() or did

            devices.append(
                NormalizedDevice(
                    bus="pci",
                    hardware_id=f"pci:{vid}:{did}",
                    vendor=clean_vendor,
                    product=clean_product,
                    subsystem=subsystem,
                    device_node=f"pci:{data.get('slot')}",
                )
            )
        return devices, None

    @classmethod
    def parse_lsblk(cls, output: str) -> tuple[list[NormalizedDevice], str | None]:
        devices: list[NormalizedDevice] = []
        try:
            parsed = json.loads(output)
        except Exception as exc:
            return [], f"Invalid lsblk JSON output: {str(exc)}"

        block_list = parsed.get("blockdevices", [])

        def _traverse(node: dict[str, Any]):
            name = node.get("name")
            if not name:
                return
            size_raw = node.get("size")
            size_bytes = None
            if size_raw is not None:
                try:
                    size_bytes = int(size_raw)
                except ValueError:
                    pass

            model = (node.get("model") or "").strip() or None
            tran = (node.get("tran") or "").strip() or None
            # Exclude serial numbers from output to protect private instance data!
            devices.append(
                NormalizedDevice(
                    bus="block",
                    hardware_id=f"block:{name}",
                    vendor=tran,
                    product=model,
                    device_node=f"/dev/{name}",
                    size_bytes=size_bytes,
                )
            )
            for child in node.get("children", []):
                _traverse(child)

        for blk in block_list:
            _traverse(blk)

        return devices, None
