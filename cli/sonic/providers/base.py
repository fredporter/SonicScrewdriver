"""Abstract base contracts for read-only hardware discovery."""
from abc import ABC, abstractmethod
from typing import Literal

from pydantic import Field

from sonic.lib.catalog import DeviceModel, Record

ProbeStatus = Literal[
    "ok",
    "missing-tool",
    "timeout",
    "permission-denied",
    "parse-error",
    "unsupported",
    "failed",
]

ScanStatus = Literal["ok", "partial", "unsupported", "failed"]


class ProbeResult(Record):
    probe: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    tool_version: str | None = None
    status: ProbeStatus
    duration_ms: float = 0.0
    error: str | None = None
    device_count: int = 0


class NormalizedDevice(Record):
    bus: Literal["usb", "pci", "block", "other"]
    hardware_id: str = Field(min_length=1)
    vendor: str | None = None
    product: str | None = None
    subsystem: str | None = None
    revision: str | None = None
    device_node: str | None = None
    size_bytes: int | None = None
    model_candidates: list[str] = Field(default_factory=list)


class ScanReport(Record):
    schema_version: Literal[1] = 1
    platform: str = Field(min_length=1)
    execution_host: str = Field(min_length=1)
    observed_at: str = Field(min_length=1)
    overall_status: ScanStatus
    probes: list[ProbeResult] = Field(default_factory=list)
    devices: list[NormalizedDevice] = Field(default_factory=list)


class BaseProvider(ABC):
    @abstractmethod
    def scan(self, catalog: dict[str, DeviceModel] | None = None) -> ScanReport:
        """Execute a read-only inventory scan returning normalized findings."""
        pass
