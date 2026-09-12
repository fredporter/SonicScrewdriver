"""Deterministic offline fixture replay provider for Sonic discovery."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from sonic.lib.catalog import DeviceModel
from sonic.providers.base import (
    BaseProvider,
    NormalizedDevice,
    ProbeResult,
    ProbeStatus,
    ScanReport,
    ScanStatus,
)
from sonic.providers.linux import LinuxProvider, _match_catalog_models, _utc_now_iso


class FixtureProvider(BaseProvider):
    def __init__(self, fixture: str | Path | dict[str, Any]):
        if isinstance(fixture, (str, Path)):
            path = Path(fixture)
            if not path.is_file():
                raise FileNotFoundError(f"Fixture file not found: {path}")
            self.data = json.loads(path.read_text())
        else:
            self.data = fixture

    def scan(self, catalog: dict[str, DeviceModel] | None = None) -> ScanReport:
        observed_at = self.data.get("observed_at") or _utc_now_iso()
        exec_host = self.data.get("execution_host", "fixture-host")
        platform_name = self.data.get("platform", "linux")

        if platform_name != "linux":
            unsupported_probe = ProbeResult(
                probe="host_platform",
                tool="os_detector",
                status="unsupported",
                duration_ms=0.0,
                error=f"Discovery not supported on platform '{platform_name}'.",
                device_count=0,
            )
            return ScanReport(
                schema_version=1,
                platform=platform_name,
                execution_host=exec_host,
                observed_at=observed_at,
                overall_status="unsupported",
                probes=[unsupported_probe],
                devices=[],
            )

        probes: list[ProbeResult] = []
        devices: list[NormalizedDevice] = []

        raw_probes = self.data.get("probes", {})

        # USB probe replay
        if "usb" in raw_probes:
            p_data = raw_probes["usb"]
            status: ProbeStatus = p_data.get("status", "ok")
            duration = float(p_data.get("duration_ms", 1.0))
            raw_out = p_data.get("output")
            error = p_data.get("error")
            dev_list: list[NormalizedDevice] = []

            if status == "ok" and raw_out:
                dev_list, parse_err = LinuxProvider.parse_lsusb(raw_out)
                if parse_err:
                    status = "parse-error"
                    error = parse_err
                    dev_list = []

            probes.append(
                ProbeResult(
                    probe="usb",
                    tool="lsusb",
                    status=status,
                    duration_ms=duration,
                    error=error,
                    device_count=len(dev_list),
                )
            )
            devices.extend(dev_list)

        # PCI probe replay
        if "pci" in raw_probes:
            p_data = raw_probes["pci"]
            status = p_data.get("status", "ok")
            duration = float(p_data.get("duration_ms", 1.0))
            raw_out = p_data.get("output")
            error = p_data.get("error")
            dev_list = []

            if status == "ok" and raw_out:
                dev_list, parse_err = LinuxProvider.parse_lspci(raw_out)
                if parse_err:
                    status = "parse-error"
                    error = parse_err
                    dev_list = []

            probes.append(
                ProbeResult(
                    probe="pci",
                    tool="lspci",
                    status=status,
                    duration_ms=duration,
                    error=error,
                    device_count=len(dev_list),
                )
            )
            devices.extend(dev_list)

        # Block probe replay
        if "block" in raw_probes:
            p_data = raw_probes["block"]
            status = p_data.get("status", "ok")
            duration = float(p_data.get("duration_ms", 1.0))
            raw_out = p_data.get("output")
            error = p_data.get("error")
            dev_list = []

            if status == "ok" and raw_out:
                dev_list, parse_err = LinuxProvider.parse_lsblk(raw_out)
                if parse_err:
                    status = "parse-error"
                    error = parse_err
                    dev_list = []

            probes.append(
                ProbeResult(
                    probe="block",
                    tool="lsblk",
                    status=status,
                    duration_ms=duration,
                    error=error,
                    device_count=len(dev_list),
                )
            )
            devices.extend(dev_list)

        # Match models
        for dev in devices:
            dev.model_candidates = _match_catalog_models(dev, catalog)

        # Compute overall status
        ok_count = sum(1 for p in probes if p.status == "ok")
        if not probes:
            overall: ScanStatus = "failed"
        elif ok_count == len(probes):
            overall = "ok"
        elif ok_count > 0:
            overall = "partial"
        else:
            overall = "failed"

        # Explicit overall override if specified in fixture
        if "overall_status" in self.data:
            overall = self.data["overall_status"]

        return ScanReport(
            schema_version=1,
            platform=platform_name,
            execution_host=exec_host,
            observed_at=observed_at,
            overall_status=overall,
            probes=probes,
            devices=devices,
        )
