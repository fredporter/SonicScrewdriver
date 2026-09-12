"""Validated model catalog. Model identity never authorizes device writes."""
from datetime import datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

ID = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Provenance(Record):
    source: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    verification: Literal["unverified"] = "unverified"


class Capacity(Record):
    value: int = Field(gt=0)
    unit: Literal["bytes"]


class DeviceModel(Record):
    id: str = Field(pattern=ID)
    vendor: str = Field(min_length=1)
    model: str = Field(min_length=1)
    type: Literal["pc", "laptop", "router", "esp32", "phone", "other"]
    hardware_revision: str | None = None
    provenance: Provenance
    ram: Capacity | None = None
    storage: Capacity | None = None
    legacy_claims: dict = Field(default_factory=dict)
    flash_eligible: Literal[False] = False


class EvidenceRecord(Record):
    kind: Literal["probe", "log", "manual", "fixture"]
    detail: str = Field(min_length=1)
    observed_at: str = Field(min_length=1)

    @field_validator("observed_at")
    @classmethod
    def validate_iso_tz(cls, v: str) -> str:
        try:
            dt = datetime.fromisoformat(v)
            if dt.tzinfo is None:
                raise ValueError("Timestamp must be timezone-aware")
        except Exception as exc:
            raise ValueError(f"Invalid timezone-aware ISO timestamp: {v}") from exc
        return v


class DeviceInstance(Record):
    id: str = Field(pattern=ID)
    model_candidates: list[str] = Field(default_factory=list)
    hardware_ids: list[str] = Field(default_factory=list)
    observed_at: str = Field(min_length=1)
    provenance: Provenance
    evidence: list[EvidenceRecord] = Field(default_factory=list)

    @field_validator("observed_at")
    @classmethod
    def validate_iso_tz(cls, v: str) -> str:
        try:
            dt = datetime.fromisoformat(v)
            if dt.tzinfo is None:
                raise ValueError("Timestamp must be timezone-aware")
        except Exception as exc:
            raise ValueError(f"Invalid timezone-aware ISO timestamp: {v}") from exc
        return v

    @field_validator("hardware_ids")
    @classmethod
    def validate_hardware_ids(cls, v: list[str]) -> list[str]:
        if len(v) != len(set(v)):
            raise ValueError("Hardware IDs must be unique")
        for hid in v:
            if not hid or not hid.strip():
                raise ValueError("Hardware ID must be non-empty")
        return v


class DriverRecord(Record):
    id: str = Field(pattern=ID)
    operating_system: str = Field(min_length=1)
    hardware_ids: list[str] = Field(min_length=1)
    provenance: Provenance
    review_status: Literal["unverified", "quarantined", "candidate", "verified"] = "unverified"

    @field_validator("hardware_ids")
    @classmethod
    def validate_hardware_ids(cls, v: list[str]) -> list[str]:
        if len(v) != len(set(v)):
            raise ValueError("Hardware IDs must be unique")
        for hid in v:
            if not hid or not hid.strip():
                raise ValueError("Hardware ID must be non-empty")
        return v


class Catalog(Record):
    schema_version: Literal[1]
    devices: list[DeviceModel]


def load_catalog(directory: Path | None = None) -> dict[str, DeviceModel]:
    directory = directory or Path(__file__).parent.parent / "data" / "devices"
    records = {}
    for path in sorted(directory.glob("*.yaml")):
        catalog = Catalog.model_validate(yaml.safe_load(path.read_text()))
        for item in catalog.devices:
            if item.id in records:
                raise ValueError(f"Duplicate device ID: {item.id}")
            records[item.id] = item
    return records
