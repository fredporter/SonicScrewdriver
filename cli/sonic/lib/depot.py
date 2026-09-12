"""Sonic Local Depot and Offline Artifact Cache.

Per user directive & uDOS Refactor Plan:
- Build and maintain an offline library of latest installers, ISOs, patches, and firmware.
- Decentralized server: download once, verify SHA-256, and serve locally across LAN.
- Maps to local storage sources (including ~/Code/Vendor/01-RAW and UDOS_HOME/depot).
- Eliminates cloud reliance, bandwidth waste, and external download delays during device revival.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sonic.lib.settings import state_root


class DepotError(Exception):
    """Base exception for Sonic Depot operations."""


class DepotIntegrityError(DepotError):
    """Raised when an artifact checksum does not match expected digest."""


@dataclass
class DepotRecord:
    id: str
    kind: str  # "iso", "package", "installer", "firmware", "tool"
    version: str
    file_name: str
    relative_path: str
    size_bytes: int
    sha256: str
    upstream_url: str = ""
    added_at: str = ""
    target_profiles: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DepotRecord:
        return cls(
            id=data["id"],
            kind=data.get("kind", "iso"),
            version=data.get("version", "latest"),
            file_name=data.get("file_name", ""),
            relative_path=data.get("relative_path", ""),
            size_bytes=int(data.get("size_bytes", 0)),
            sha256=data.get("sha256", ""),
            upstream_url=data.get("upstream_url", ""),
            added_at=data.get("added_at", ""),
            target_profiles=list(data.get("target_profiles", [])),
            description=data.get("description", ""),
        )


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_default_depot_roots() -> List[Path]:
    """Discover candidate local storage depots in order of priority."""
    roots: List[Path] = []

    # Explicit environment variable
    env_root = os.environ.get("SONIC_DEPOT_ROOT")
    if env_root and Path(env_root).is_dir():
        roots.append(Path(env_root).resolve())

    # Vendor folder in Code directory (~/Code/Vendor/01-RAW)
    vendor_raw = Path.home() / "Code" / "Vendor" / "01-RAW"
    if vendor_raw.is_dir():
        roots.append(vendor_raw.resolve())

    # UDOS state depot (~/Code/.udos/sonic/depot)
    udos_depot = (state_root() / "depot").resolve()
    roots.append(udos_depot)

    return roots


def get_depot_manifest_path(depot_dir: Path) -> Path:
    return depot_dir / "depot_manifest.json"


def load_depot_manifest(depot_dir: Optional[Path] = None) -> Dict[str, DepotRecord]:
    """Load records from depot manifest across known roots."""
    targets = [depot_dir] if depot_dir else get_default_depot_roots()
    combined: Dict[str, DepotRecord] = {}

    for root in targets:
        if not root or not root.exists():
            continue
        m_path = get_depot_manifest_path(root)
        if m_path.exists():
            try:
                with open(m_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    for k, v in raw.items():
                        if k not in combined:
                            rec = DepotRecord.from_dict(v)
                            combined[k] = rec
            except Exception:
                pass

    return combined


def save_depot_manifest(depot_dir: Path, records: Dict[str, DepotRecord]) -> None:
    depot_dir.mkdir(parents=True, exist_ok=True)
    m_path = get_depot_manifest_path(depot_dir)
    tmp_path = depot_dir / f".manifest-{os.getpid()}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump({k: v.to_dict() for k, v in records.items()}, f, indent=2)
    tmp_path.replace(m_path)


def register_artifact(
    file_path: Path,
    artifact_id: str,
    kind: str = "iso",
    version: str = "latest",
    expected_sha256: Optional[str] = None,
    upstream_url: str = "",
    target_profiles: Optional[List[str]] = None,
    description: str = "",
    depot_dir: Optional[Path] = None,
) -> DepotRecord:
    """Register and verify a local ISO, installer, or patch into the offline depot."""
    file_path = Path(file_path).resolve()
    if not file_path.exists():
        raise DepotError(f"Artifact file not found: {file_path}")

    actual_sha = compute_sha256(file_path)
    if expected_sha256 and actual_sha.lower() != expected_sha256.lower():
        raise DepotIntegrityError(
            f"Checksum mismatch for {file_path.name}: expected {expected_sha256}, calculated {actual_sha}"
        )

    target_depot = depot_dir or (state_root() / "depot").resolve()
    target_depot.mkdir(parents=True, exist_ok=True)

    rel_path = file_path.name
    dest_path = target_depot / file_path.name

    # If file is not already in depot, copy or link it
    if file_path.parent != target_depot:
        import shutil
        if not dest_path.exists():
            # For large ISOs, copy atomically
            shutil.copy2(file_path, dest_path)

    record = DepotRecord(
        id=artifact_id,
        kind=kind,
        version=version,
        file_name=file_path.name,
        relative_path=rel_path,
        size_bytes=dest_path.stat().st_size,
        sha256=actual_sha,
        upstream_url=upstream_url,
        added_at=datetime.now(timezone.utc).isoformat(),
        target_profiles=target_profiles or [],
        description=description,
    )

    records = load_depot_manifest(target_depot)
    records[artifact_id] = record
    save_depot_manifest(target_depot, records)

    return record


def list_artifacts(kind: Optional[str] = None, depot_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """List all available artifacts in the offline depot."""
    manifest = load_depot_manifest(depot_dir)
    results = []
    for rec in manifest.values():
        if kind and rec.kind != kind:
            continue
        results.append(rec.to_dict())
    return results


def verify_artifact(artifact_id: str, depot_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Check physical presence and SHA-256 integrity of an artifact in the depot."""
    manifest = load_depot_manifest(depot_dir)
    if artifact_id not in manifest:
        raise DepotError(f"Artifact '{artifact_id}' not registered in depot manifest")

    rec = manifest[artifact_id]
    roots = [depot_dir] if depot_dir else get_default_depot_roots()

    found_path: Optional[Path] = None
    for r in roots:
        cand = r / rec.relative_path
        if cand.exists():
            found_path = cand
            break

    if not found_path:
        return {
            "id": rec.id,
            "status": "missing_file",
            "file_name": rec.file_name,
            "healthy": False,
        }

    actual_hash = compute_sha256(found_path)
    matches = actual_hash == rec.sha256

    return {
        "id": rec.id,
        "status": "verified" if matches else "checksum_mismatch",
        "healthy": matches,
        "file_path": str(found_path),
        "expected_sha256": rec.sha256,
        "actual_sha256": actual_hash,
        "size_bytes": found_path.stat().st_size,
    }
