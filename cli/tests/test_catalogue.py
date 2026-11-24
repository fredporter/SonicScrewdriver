"""Checks for the base distribution catalogue and the library snapshot."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from sonic.cli import cli
from sonic.lib.catalogue import (
    CatalogueError,
    build_snapshot,
    catalogue_summary,
    load_catalogue,
)
from sonic.lib.depot import DepotRecord, save_depot_manifest

SHA = "ba9323207bd2d2b4d5ac9d7c77f08f7c2405415d73e8fe0b8929e7366df6dccc"


def seed_payload() -> dict:
    return {
        "schema": "sonic.catalogue/1",
        "version": "0.1.0",
        "layer": 0,
        "titles": [
            {
                "id": "nanocoder",
                "title": "NanoCoder",
                "summary": "Local coding agent runtime",
                "provenance": "upstream",
                "editions": [
                    {
                        "id": "nanocoder-1.30.0",
                        "treatment": "adapted",
                        "status": "release",
                        "media_policy": "bundled",
                        "capsules": [
                            {
                                "id": "nanocoder",
                                "kind": "installer",
                                "version": "1.30.0",
                                "sha256": SHA,
                                "bytes": 7,
                            }
                        ],
                    }
                ],
            }
        ],
        "managed_lanes": [{"id": "ollama-models", "owner": "Ollama", "retained": False}],
    }


@pytest.fixture
def seed_file(tmp_path: Path) -> Path:
    path = tmp_path / "catalogue.json"
    path.write_text(json.dumps(seed_payload()), encoding="utf-8")
    return path


@pytest.fixture
def depot_with_artifact(tmp_path: Path) -> Path:
    depot = tmp_path / "depot"
    depot.mkdir()
    artifact = depot / "nanocoder.tgz"
    artifact.write_bytes(b"PAYLOAD")
    save_depot_manifest(
        depot,
        {
            "nanocoder": DepotRecord(
                id="nanocoder",
                kind="installer",
                version="1.30.0",
                file_name="nanocoder.tgz",
                relative_path="nanocoder.tgz",
                size_bytes=7,
                sha256=SHA,
            )
        },
    )
    return depot


def test_loads_and_summarises_the_base_catalogue(seed_file: Path):
    data = load_catalogue(seed_file)
    summary = catalogue_summary(data)

    assert summary["schema"] == "sonic.catalogue/1"
    assert summary["layer"] == 0
    assert summary["titles"] == 1
    assert summary["editions"] == 1
    assert summary["capsules"] == 1
    assert summary["statuses"] == {"release": 1}
    assert summary["managed_lanes"] == 1


def test_missing_catalogue_is_an_error(tmp_path: Path):
    with pytest.raises(CatalogueError):
        load_catalogue(tmp_path / "absent.json")


def test_unknown_schema_is_rejected(tmp_path: Path):
    path = tmp_path / "catalogue.json"
    path.write_text(json.dumps({"schema": "something-else/9", "titles": []}), encoding="utf-8")
    with pytest.raises(CatalogueError):
        load_catalogue(path)


def test_malformed_edition_is_rejected(tmp_path: Path):
    payload = seed_payload()
    payload["titles"][0]["editions"][0].pop("capsules")
    path = tmp_path / "catalogue.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CatalogueError):
        load_catalogue(path)


def test_snapshot_without_a_depot_claims_nothing(seed_file: Path):
    snapshot = build_snapshot(load_catalogue(seed_file), generated_at="2026-11-24T00:00:00Z")

    assert snapshot["schema"] == "ucode-library/1"
    assert snapshot["depot"]["root"] == "not configured"
    assert snapshot["depot"]["retainedBytes"] == 0
    capsule = snapshot["titles"][0]["editions"][0]["capsules"][0]
    assert capsule["verified"] is False
    assert capsule["bytes"] == 7


def test_snapshot_marks_a_retained_artifact_verified(seed_file: Path, depot_with_artifact: Path):
    snapshot = build_snapshot(load_catalogue(seed_file), depot_dir=depot_with_artifact)

    capsule = snapshot["titles"][0]["editions"][0]["capsules"][0]
    assert capsule["verified"] is True
    assert capsule["bytes"] == 7
    assert snapshot["depot"]["retainedBytes"] == 7
    assert snapshot["depot"]["root"].endswith("depot")


def test_snapshot_rejects_a_hash_mismatch(seed_file: Path, depot_with_artifact: Path):
    save_depot_manifest(
        depot_with_artifact,
        {
            "nanocoder": DepotRecord(
                id="nanocoder",
                kind="installer",
                version="1.30.0",
                file_name="nanocoder.tgz",
                relative_path="nanocoder.tgz",
                size_bytes=7,
                sha256="0" * 64,
            )
        },
    )
    snapshot = build_snapshot(load_catalogue(seed_file), depot_dir=depot_with_artifact)
    assert snapshot["titles"][0]["editions"][0]["capsules"][0]["verified"] is False


def test_snapshot_rejects_a_missing_file(seed_file: Path, depot_with_artifact: Path):
    (depot_with_artifact / "nanocoder.tgz").unlink()
    snapshot = build_snapshot(load_catalogue(seed_file), depot_dir=depot_with_artifact)
    assert snapshot["titles"][0]["editions"][0]["capsules"][0]["verified"] is False


def test_cli_status_and_snapshot(seed_file: Path):
    runner = CliRunner()

    status = runner.invoke(cli, ["catalogue", "status", "--catalogue", str(seed_file), "--json"])
    assert status.exit_code == 0, status.output
    assert json.loads(status.output)["titles"] == 1

    snapshot = runner.invoke(cli, ["catalogue", "snapshot", "--catalogue", str(seed_file)])
    assert snapshot.exit_code == 0, snapshot.output
    assert json.loads(snapshot.output)["schema"] == "ucode-library/1"


def test_cli_reports_a_missing_catalogue(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(cli, ["catalogue", "status", "--catalogue", str(tmp_path / "absent.json")])
    assert result.exit_code != 0
    assert "Catalogue error" in result.output
