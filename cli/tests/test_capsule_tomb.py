"""Tests for .capsule packaging, .tomb sealing, and container integrity verification."""
from pathlib import Path
import pytest
from click.testing import CliRunner

from sonic.cli import cli
from sonic.lib.capsule_tomb import (
    pack_capsule,
    seal_tomb,
    verify_container,
)


@pytest.fixture
def sample_binder(tmp_path: Path) -> Path:
    binder_dir = tmp_path / "sample-binder"
    binder_dir.mkdir()
    (binder_dir / "draft.md").write_text("# Sample Project Draft\n\nInitial notes and specifications.")
    (binder_dir / "manifest.json").write_text('{"title": "Sample Project", "author": "Alice"}')
    originals_dir = binder_dir / "originals"
    originals_dir.mkdir()
    (originals_dir / "sketch.svg").write_text('<svg><circle r="10"/></svg>')
    return binder_dir


def test_pack_capsule_and_verify(sample_binder: Path, tmp_path: Path):
    out_capsule = tmp_path / "sample.capsule"
    archive_path = pack_capsule(
        source_dir=sample_binder,
        output_file=out_capsule,
        title="Sample Distribution Capsule",
        author="Alice",
    )
    assert archive_path.exists()
    assert archive_path == out_capsule

    # Verify container
    report = verify_container(archive_path)
    assert report["valid"] is True
    assert report["container_type"] == "capsule"
    assert report["schema_version"] == "udos-capsule/1"
    assert report["verified_files"] == 3
    assert len(report["corrupt_files"]) == 0


def test_seal_tomb_and_verify(sample_binder: Path, tmp_path: Path):
    out_tomb = tmp_path / "sample.tomb"
    archive_path = seal_tomb(
        source_path=sample_binder,
        output_file=out_tomb,
        reason="frozen_edition",
        notes="Approved edition 1 snapshot",
    )
    assert archive_path.exists()
    assert archive_path == out_tomb

    # Verify container
    report = verify_container(archive_path)
    assert report["valid"] is True
    assert report["container_type"] == "tomb"
    assert report["schema_version"] == "udos-tomb/1"
    assert report["manifest"]["reason"] == "frozen_edition"
    assert report["manifest"]["notes"] == "Approved edition 1 snapshot"
    assert report["manifest"]["immutable"] is True
    assert report["verified_files"] == 3


def test_cli_package_pack_and_verify(sample_binder: Path, tmp_path: Path):
    runner = CliRunner()
    out_capsule = tmp_path / "cli_test.capsule"

    res_pack = runner.invoke(cli, [
        "package", "pack",
        str(sample_binder),
        "--out", str(out_capsule),
        "--title", "CLI Pack Test",
    ])
    assert res_pack.exit_code == 0
    assert "Successfully packaged capsule" in res_pack.output
    assert out_capsule.exists()

    res_verify = runner.invoke(cli, [
        "package", "verify",
        str(out_capsule),
    ])
    assert res_verify.exit_code == 0
    assert "integrity OK" in res_verify.output


def test_cli_package_seal_and_verify(sample_binder: Path, tmp_path: Path):
    runner = CliRunner()
    out_tomb = tmp_path / "cli_test.tomb"

    res_seal = runner.invoke(cli, [
        "package", "seal",
        str(sample_binder),
        "--out", str(out_tomb),
        "--reason", "dissolved_to_ether",
        "--notes", "Ephemeral dispatch dissolved",
    ])
    assert res_seal.exit_code == 0
    assert "Successfully sealed immutable tomb" in res_seal.output
    assert "dissolved_to_ether" in res_seal.output
    assert out_tomb.exists()

    res_verify = runner.invoke(cli, [
        "package", "verify",
        str(out_tomb),
    ])
    assert res_verify.exit_code == 0
    assert "integrity OK" in res_verify.output
