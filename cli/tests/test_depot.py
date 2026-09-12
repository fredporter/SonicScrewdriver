"""Unit tests for Sonic Local Depot and Offline Artifact Cache."""

from pathlib import Path
import pytest

from sonic.lib.depot import (
    DepotError,
    DepotIntegrityError,
    list_artifacts,
    register_artifact,
    verify_artifact,
)


@pytest.fixture
def sample_iso_file(tmp_path: Path) -> Path:
    f = tmp_path / "linuxmint-22-cinnamon-64bit.iso"
    f.write_bytes(b"MOCK_LINUX_MINT_22_ISO_CONTENT_DATA")
    return f


def test_register_and_list_artifact(sample_iso_file: Path, tmp_path: Path):
    depot_dir = tmp_path / "test_depot"
    rec = register_artifact(
        file_path=sample_iso_file,
        artifact_id="mint-22-cinnamon",
        kind="iso",
        version="22.0",
        target_profiles=["cinnamon-full"],
        description="Linux Mint 22 Cinnamon 64-bit ISO",
        depot_dir=depot_dir,
    )

    assert rec.id == "mint-22-cinnamon"
    assert rec.kind == "iso"
    assert rec.version == "22.0"
    assert "cinnamon-full" in rec.target_profiles

    # Check listing
    items = list_artifacts(depot_dir=depot_dir)
    assert len(items) == 1
    assert items[0]["id"] == "mint-22-cinnamon"
    assert (depot_dir / "linuxmint-22-cinnamon-64bit.iso").exists()


def test_register_with_checksum_validation(sample_iso_file: Path, tmp_path: Path):
    depot_dir = tmp_path / "test_depot"

    # Incorrect checksum should raise DepotIntegrityError
    with pytest.raises(DepotIntegrityError):
        register_artifact(
            file_path=sample_iso_file,
            artifact_id="mint-22-corrupt",
            kind="iso",
            expected_sha256="deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
            depot_dir=depot_dir,
        )


def test_verify_depot_artifact(sample_iso_file: Path, tmp_path: Path):
    depot_dir = tmp_path / "test_depot"
    register_artifact(
        file_path=sample_iso_file,
        artifact_id="mint-22-cinnamon",
        kind="iso",
        depot_dir=depot_dir,
    )

    ver = verify_artifact("mint-22-cinnamon", depot_dir=depot_dir)
    assert ver["healthy"] is True
    assert ver["status"] == "verified"

    # Tamper with file
    cached_file = depot_dir / sample_iso_file.name
    cached_file.write_bytes(b"TAMPERED_BYTES")

    ver_tampered = verify_artifact("mint-22-cinnamon", depot_dir=depot_dir)
    assert ver_tampered["healthy"] is False
    assert ver_tampered["status"] == "checksum_mismatch"
