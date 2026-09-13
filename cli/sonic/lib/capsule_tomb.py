"""Universal Capsule & Tomb Packaging and Sealing Engine for Sonic Screwdriver.

Implements authoritative lifecycle container standards from:
- global-knowledge/standards/CONTAINER-STANDARDS.md

Provides:
- .capsule packaging: bundles source directories/binders into signed, offline distribution packages.
- .tomb sealing: freezes editions, binders, or expired dispatches into immutable witness archives.
- Container integrity verification for .capsule and .tomb archives.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class ContainerError(Exception):
    """Base exception for container operations."""


class ContainerIntegrityError(ContainerError):
    """Raised when container file manifests or checksums do not match."""


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_bytes_sha256(data: bytes) -> str:
    """Compute SHA-256 hash of raw bytes."""
    return hashlib.sha256(data).hexdigest()


EXCLUDED_CONTAINER_PATTERNS = {
    ".DS_Store",
    "__pycache__",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
}


def pack_capsule(
    source_dir: Path,
    output_file: Optional[Path] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    version: str = "1.0.0",
    capsule_id: Optional[str] = None,
) -> Path:
    """Package a binder or source directory into a signed .capsule bundle."""
    source_dir = Path(source_dir).resolve()
    if not source_dir.is_dir():
        raise ContainerError(f"Source directory does not exist or is not a directory: {source_dir}")

    cid = capsule_id or source_dir.name
    out_path = output_file or source_dir.parent / f"{cid}.capsule"
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Collect files and calculate SHA-256 digests
    file_manifest: Dict[str, str] = {}
    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_CONTAINER_PATTERNS]
        for f in files:
            if f in EXCLUDED_CONTAINER_PATTERNS or f.endswith(".pyc"):
                continue
            full_path = Path(root) / f
            rel_path = full_path.relative_to(source_dir).as_posix()
            file_manifest[rel_path] = compute_file_sha256(full_path)

    manifest_data = {
        "schema_version": "udos-capsule/1",
        "capsule_id": cid,
        "title": title or cid,
        "author": author or "Sovereign User",
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "integrity": {
            "algorithm": "sha256",
            "file_count": len(file_manifest),
            "files": file_manifest,
        },
    }

    manifest_bytes = json.dumps(manifest_data, indent=2, sort_keys=True).encode("utf-8")
    manifest_sha256 = compute_bytes_sha256(manifest_bytes)

    # Write to zip archive
    temp_zip = out_path.with_suffix(".tmp.zip")
    try:
        with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # Write manifest
            zf.writestr("capsule.manifest.json", manifest_bytes)
            # Write payload files
            for rel_path in sorted(file_manifest.keys()):
                source_file = source_dir / rel_path
                zf.write(source_file, rel_path)

        if out_path.exists():
            out_path.unlink()
        temp_zip.rename(out_path)
    finally:
        if temp_zip.exists():
            temp_zip.unlink()

    return out_path


def seal_tomb(
    source_path: Path,
    output_file: Optional[Path] = None,
    reason: str = "archived_historical_witness",
    notes: str = "",
    tomb_id: Optional[str] = None,
) -> Path:
    """Seal a binder, edition, or dissolved dispatch into an immutable .tomb archive."""
    source_path = Path(source_path).resolve()
    if not source_path.exists():
        raise ContainerError(f"Source path does not exist: {source_path}")

    tid = tomb_id or f"tomb-{source_path.stem}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    out_path = output_file or source_path.parent / f"{tid}.tomb"
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    file_manifest: Dict[str, str] = {}
    if source_path.is_dir():
        for root, dirs, files in os.walk(source_path):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_CONTAINER_PATTERNS]
            for f in files:
                if f in EXCLUDED_CONTAINER_PATTERNS or f.endswith(".pyc"):
                    continue
                full_path = Path(root) / f
                rel_path = full_path.relative_to(source_path).as_posix()
                file_manifest[rel_path] = compute_file_sha256(full_path)
    else:
        file_manifest[source_path.name] = compute_file_sha256(source_path)

    tombstone_data = {
        "schema_version": "udos-tomb/1",
        "tomb_id": tid,
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "notes": notes,
        "immutable": True,
        "integrity": {
            "algorithm": "sha256",
            "file_count": len(file_manifest),
            "files": file_manifest,
        },
    }

    tombstone_bytes = json.dumps(tombstone_data, indent=2, sort_keys=True).encode("utf-8")

    temp_zip = out_path.with_suffix(".tmp.zip")
    try:
        with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("tombstone.json", tombstone_bytes)
            if source_path.is_dir():
                for rel_path in sorted(file_manifest.keys()):
                    source_file = source_path / rel_path
                    zf.write(source_file, rel_path)
            else:
                zf.write(source_path, source_path.name)

        if out_path.exists():
            out_path.unlink()
        temp_zip.rename(out_path)
        # Lock file permissions to read-only (0o444)
        out_path.chmod(0o444)
    finally:
        if temp_zip.exists():
            temp_zip.unlink()

    return out_path


def verify_container(archive_path: Path) -> Dict[str, Any]:
    """Verify integrity of a .capsule or .tomb archive against its internal manifest."""
    archive_path = Path(archive_path).resolve()
    if not archive_path.is_file():
        raise ContainerError(f"Container archive not found: {archive_path}")

    if not zipfile.is_zipfile(archive_path):
        raise ContainerError(f"File is not a valid zip container: {archive_path}")

    with zipfile.ZipFile(archive_path, "r") as zf:
        namelist = set(zf.namelist())
        is_capsule = "capsule.manifest.json" in namelist
        is_tomb = "tombstone.json" in namelist

        if not (is_capsule or is_tomb):
            raise ContainerError("Archive is neither a recognized .capsule nor .tomb container (missing manifest)")

        manifest_name = "capsule.manifest.json" if is_capsule else "tombstone.json"
        manifest_raw = zf.read(manifest_name).decode("utf-8")
        manifest = json.loads(manifest_raw)

        expected_files: Dict[str, str] = manifest.get("integrity", {}).get("files", {})
        verified_count = 0
        corrupt_files: List[str] = []

        for rel_path, expected_sha in expected_files.items():
            if rel_path not in namelist:
                corrupt_files.append(f"Missing file: {rel_path}")
                continue
            data = zf.read(rel_path)
            actual_sha = hashlib.sha256(data).hexdigest()
            if actual_sha != expected_sha:
                corrupt_files.append(f"Checksum mismatch for {rel_path}: expected {expected_sha}, got {actual_sha}")
            else:
                verified_count += 1

        is_valid = len(corrupt_files) == 0 and verified_count == len(expected_files)

        return {
            "archive": str(archive_path),
            "container_type": "capsule" if is_capsule else "tomb",
            "schema_version": manifest.get("schema_version"),
            "container_id": manifest.get("capsule_id") or manifest.get("tomb_id"),
            "valid": is_valid,
            "verified_files": verified_count,
            "total_files": len(expected_files),
            "corrupt_files": corrupt_files,
            "manifest": manifest,
        }
