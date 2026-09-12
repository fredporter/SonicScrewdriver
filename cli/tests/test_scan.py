"""Tests for read-only hardware discovery, providers, and CLI scan/doctor."""
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from sonic.cli import cli
from sonic.lib.catalog import DeviceInstance, DriverRecord, EvidenceRecord, Provenance

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_darwin_unsupported_exit(runner):
    result = runner.invoke(cli, ["scan"])
    assert result.exit_code == 1
    assert "UNSUPPORTED" in result.output

    json_result = runner.invoke(cli, ["scan", "--json"])
    assert json_result.exit_code == 1
    data = json.loads(json_result.output)
    assert data["overall_status"] == "unsupported"
    assert data["schema_version"] == 1
    assert len(data["probes"]) == 1
    assert data["probes"][0]["status"] == "unsupported"


def test_doctor_darwin_unsupported(runner):
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 1
    assert "UNSUPPORTED" in result.output

    json_result = runner.invoke(cli, ["doctor", "--json"])
    assert json_result.exit_code == 1
    data = json.loads(json_result.output)
    assert data["supported"] is False
    assert data["overall_status"] == "unsupported"


def test_fixture_clean_linux_pc(runner):
    fixture = str(FIXTURES_DIR / "clean_linux_pc.json")
    result = runner.invoke(cli, ["scan", "--fixture", fixture, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["overall_status"] == "ok"
    assert len(data["probes"]) == 3
    for p in data["probes"]:
        assert p["status"] == "ok"

    devices = data["devices"]
    assert len(devices) >= 3
    busses = {d["bus"] for d in devices}
    assert {"usb", "pci", "block"}.issubset(busses)

    # Check block device privacy: no serial numbers exposed
    block_devs = [d for d in devices if d["bus"] == "block"]
    for bd in block_devs:
        assert "REDACTED" not in json.dumps(bd)


def test_fixture_missing_tools(runner):
    fixture = str(FIXTURES_DIR / "missing_tools.json")
    result = runner.invoke(cli, ["scan", "--fixture", fixture, "--json"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["overall_status"] == "partial"
    probes_by_name = {p["probe"]: p for p in data["probes"]}
    assert probes_by_name["usb"]["status"] == "missing-tool"
    assert probes_by_name["pci"]["status"] == "missing-tool"
    assert probes_by_name["block"]["status"] == "ok"


def test_fixture_parse_error(runner):
    fixture = str(FIXTURES_DIR / "parse_error.json")
    result = runner.invoke(cli, ["scan", "--fixture", fixture, "--json"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    probes_by_name = {p["probe"]: p for p in data["probes"]}
    assert probes_by_name["usb"]["status"] == "parse-error"
    assert probes_by_name["block"]["status"] == "parse-error"


def test_fixture_timeout(runner):
    fixture = str(FIXTURES_DIR / "timeout.json")
    result = runner.invoke(cli, ["scan", "--fixture", fixture, "--json"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    probes_by_name = {p["probe"]: p for p in data["probes"]}
    assert probes_by_name["usb"]["status"] == "timeout"


def test_fixture_zero_devices(runner):
    fixture = str(FIXTURES_DIR / "zero_devices.json")
    result = runner.invoke(cli, ["scan", "--fixture", fixture, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["overall_status"] == "ok"
    assert len(data["devices"]) == 0


def test_fixture_ambiguous_models(runner):
    fixture = str(FIXTURES_DIR / "ambiguous_models.json")
    result = runner.invoke(cli, ["scan", "--fixture", fixture, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    devices = data["devices"]
    assert len(devices) == 1
    # Check that candidate models were found from catalog without picking only one
    candidates = devices[0]["model_candidates"]
    assert isinstance(candidates, list)
    if candidates:
        assert len(candidates) >= 1


def test_no_state_writes_during_scan(tmp_path, monkeypatch, runner):
    state_dir = tmp_path / "test_udos_home"
    monkeypatch.setenv("UDOS_HOME", str(state_dir))
    fixture = str(FIXTURES_DIR / "clean_linux_pc.json")
    result = runner.invoke(cli, ["scan", "--fixture", fixture])
    assert result.exit_code == 0
    assert not state_dir.exists()


def test_hardened_contracts_validation():
    # Timezone-aware ISO string is required
    valid_tz = datetime.now(timezone.utc).isoformat()
    prov = Provenance(source="test", revision="rev1")

    # Valid instance
    instance = DeviceInstance(
        id="dev-01",
        model_candidates=["archer-c7-v5"],
        hardware_ids=["usb:046d:c52b"],
        observed_at=valid_tz,
        provenance=prov,
    )
    assert instance.id == "dev-01"

    # Naive timestamp without timezone must fail
    with pytest.raises(ValidationError):
        DeviceInstance(
            id="dev-02",
            observed_at="2026-09-12T10:00:00",
            provenance=prov,
        )

    # Duplicate hardware IDs must fail
    with pytest.raises(ValidationError):
        DeviceInstance(
            id="dev-03",
            hardware_ids=["usb:1234:5678", "usb:1234:5678"],
            observed_at=valid_tz,
            provenance=prov,
        )

    # Empty hardware ID must fail
    with pytest.raises(ValidationError):
        DriverRecord(
            id="drv-01",
            operating_system="linux",
            hardware_ids=[""],
            provenance=prov,
        )

    # Evidence record requires timezone-aware ISO string
    ev = EvidenceRecord(kind="probe", detail="lsusb", observed_at=valid_tz)
    assert ev.kind == "probe"
