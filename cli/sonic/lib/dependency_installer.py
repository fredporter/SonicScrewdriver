"""Sonic Offline Dependency Installer and Package Registry.

Per uDOS Product Refactor Plan Section 11:
- Runtime dependencies install as verified versioned artifacts, not live sibling checkouts.
- Offline bundles supported with full SHA-256 integrity verification.
- Reuses compatible installed packages and detects version conflicts explicitly.
- Shared dependency tracking: records which products require each installed package.
- Safe uninstall: preserves packages still needed by another product and never removes user documents.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from sonic.lib.settings import state_root


class PackageError(Exception):
    """Base exception for Sonic package operations."""


class PackageIntegrityError(PackageError):
    """Raised when an artifact checksum does not match expected digest."""


class DependencyConflictError(PackageError):
    """Raised when an incompatible version requirement conflicts with installed state."""


class PackageSecurityError(PackageError):
    """Raised when security boundaries are violated (e.g. path traversal or touching user documents)."""


@dataclass
class PackageRecord:
    name: str
    version: str
    description: str = ""
    installed_at: str = ""
    archive_sha256: str = ""
    required_by: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    dependencies: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PackageRecord:
        return cls(
            name=data["name"],
            version=data["version"],
            description=data.get("description", ""),
            installed_at=data.get("installed_at", ""),
            archive_sha256=data.get("archive_sha256", ""),
            required_by=list(data.get("required_by", [])),
            files=list(data.get("files", [])),
            dependencies=dict(data.get("dependencies", {})),
        )


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_packages_root(custom_root: Optional[Path] = None) -> Path:
    if custom_root:
        return Path(custom_root).resolve()
    return (state_root() / "packages").resolve()


def get_manifest_path(packages_root: Path) -> Path:
    return packages_root / "installed_manifest.json"


def load_installed_manifest(packages_root: Path) -> Dict[str, PackageRecord]:
    m_path = get_manifest_path(packages_root)
    if not m_path.exists():
        return {}
    try:
        with open(m_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
            return {k: PackageRecord.from_dict(v) for k, v in raw.items()}
    except Exception:
        return {}


def save_installed_manifest(packages_root: Path, manifest: Dict[str, PackageRecord]) -> None:
    packages_root.mkdir(parents=True, exist_ok=True)
    m_path = get_manifest_path(packages_root)
    temp_path = packages_root / f".manifest-{os.getpid()}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump({k: v.to_dict() for k, v in manifest.items()}, f, indent=2)
    temp_path.replace(m_path)


def is_protected_user_path(path: Path) -> bool:
    """Ensure path is not inside protected user document stores."""
    resolved = path.resolve()
    home = Path.home().resolve()
    protected_roots = [
        home / "Vault",
        home / "Shared",
        home / "Public",
        home / ".ssh",
        home / ".gitconfig",
        home / ".codex",
    ]
    for prot in protected_roots:
        if resolved == prot or resolved.is_relative_to(prot):
            return True
    return False


def build_package(
    source_dir: Path,
    output_file: Path,
    name: str,
    version: str,
    dependencies: Optional[Dict[str, str]] = None,
    description: str = "",
) -> Path:
    """Build a standalone .spkg archive with SHA-256 checksums."""
    source_dir = Path(source_dir).resolve()
    output_file = Path(output_file).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    file_checksums: Dict[str, str] = {}
    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
        for f in files:
            if f.startswith(".") or f.endswith(".pyc"):
                continue
            abs_f = Path(root) / f
            rel_f = abs_f.relative_to(source_dir).as_posix()
            file_checksums[rel_f] = compute_sha256(abs_f)

    meta = {
        "format": "sonic-package/1",
        "name": name,
        "version": version,
        "description": description,
        "dependencies": dependencies or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "checksums": file_checksums,
    }

    with zipfile.ZipFile(output_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel_f in sorted(file_checksums.keys()):
            zf.write(source_dir / rel_f, arcname=f"payload/{rel_f}")
        zf.writestr("package.json", json.dumps(meta, indent=2).encode("utf-8"))

    return output_file


def check_version_compatibility(installed_version: str, required_version_spec: str) -> bool:
    """Simple semver check: allows matching versions or >= requirements."""
    if not required_version_spec or required_version_spec == "*":
        return True
    if required_version_spec.startswith(">="):
        min_v = required_version_spec[2:].strip()
        return installed_version >= min_v
    if required_version_spec.startswith("=="):
        exact_v = required_version_spec[2:].strip()
        return installed_version == exact_v
    return installed_version == required_version_spec


def install_package(
    archive_path: Path,
    consumer_id: str,
    packages_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Install an offline package artifact, verifying integrity and recording shared dependencies."""
    archive_path = Path(archive_path).resolve()
    if not archive_path.exists():
        raise PackageError(f"Package artifact does not exist: {archive_path}")

    root = get_packages_root(packages_root)
    archive_sha = compute_sha256(archive_path)

    with zipfile.ZipFile(archive_path, "r") as zf:
        try:
            meta_raw = zf.read("package.json")
            meta = json.loads(meta_raw.decode("utf-8"))
        except KeyError:
            raise PackageIntegrityError("Package archive is missing required package.json metadata")
        except Exception as e:
            raise PackageIntegrityError(f"Failed to read package metadata: {e}")

        pkg_name = meta["name"]
        pkg_version = meta["version"]
        checksums = meta.get("checksums", {})

        manifest = load_installed_manifest(root)

        # Check existing installation
        if pkg_name in manifest:
            existing = manifest[pkg_name]
            if existing.version != pkg_version:
                raise DependencyConflictError(
                    f"Version conflict for package '{pkg_name}': "
                    f"installed version is {existing.version} (required by {existing.required_by}), "
                    f"cannot overwrite with version {pkg_version}"
                )
            # Same version already installed -> register consumer
            if consumer_id not in existing.required_by:
                existing.required_by.append(consumer_id)
                save_installed_manifest(root, manifest)
            return {
                "status": "reused",
                "name": pkg_name,
                "version": pkg_version,
                "required_by": existing.required_by,
                "install_dir": str(root / pkg_name / pkg_version),
            }

        # Check declared dependencies
        for dep_name, dep_spec in meta.get("dependencies", {}).items():
            if dep_name not in manifest:
                raise DependencyConflictError(
                    f"Unmet dependency for '{pkg_name}': '{dep_name} {dep_spec}' is not installed"
                )
            installed_dep = manifest[dep_name]
            if not check_version_compatibility(installed_dep.version, dep_spec):
                raise DependencyConflictError(
                    f"Incompatible dependency for '{pkg_name}': '{dep_name}' installed={installed_dep.version}, required={dep_spec}"
                )

        # Verify checksums and extract
        pkg_dest_dir = root / pkg_name / pkg_version
        pkg_dest_dir.mkdir(parents=True, exist_ok=True)

        extracted_files: List[str] = []
        for rel_payload_path, expected_hash in checksums.items():
            arc_name = f"payload/{rel_payload_path}"
            try:
                file_bytes = zf.read(arc_name)
            except KeyError:
                raise PackageIntegrityError(f"Missing payload file in archive: {arc_name}")

            actual_hash = hashlib.sha256(file_bytes).hexdigest()
            if actual_hash != expected_hash:
                raise PackageIntegrityError(
                    f"SHA-256 integrity check failed for {rel_payload_path}: "
                    f"expected {expected_hash}, got {actual_hash}"
                )

            dest_file = (pkg_dest_dir / rel_payload_path).resolve()
            if not dest_file.is_relative_to(pkg_dest_dir):
                raise PackageSecurityError(f"Illegal path escape attempt in package: {rel_payload_path}")

            dest_file.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_file, "wb") as f:
                f.write(file_bytes)
            extracted_files.append(rel_payload_path)

        # Record in manifest
        record = PackageRecord(
            name=pkg_name,
            version=pkg_version,
            description=meta.get("description", ""),
            installed_at=datetime.now(timezone.utc).isoformat(),
            archive_sha256=archive_sha,
            required_by=[consumer_id],
            files=extracted_files,
            dependencies=meta.get("dependencies", {}),
        )
        manifest[pkg_name] = record
        save_installed_manifest(root, manifest)

        return {
            "status": "installed",
            "name": pkg_name,
            "version": pkg_version,
            "required_by": record.required_by,
            "install_dir": str(pkg_dest_dir),
            "file_count": len(extracted_files),
        }


def list_installed_packages(packages_root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """List all installed packages and their consumers."""
    root = get_packages_root(packages_root)
    manifest = load_installed_manifest(root)
    return [rec.to_dict() for rec in manifest.values()]


def verify_package(package_name: str, packages_root: Optional[Path] = None) -> Dict[str, Any]:
    """Verify integrity of installed package files against recorded state."""
    root = get_packages_root(packages_root)
    manifest = load_installed_manifest(root)
    if package_name not in manifest:
        raise PackageError(f"Package '{package_name}' is not installed")

    rec = manifest[package_name]
    pkg_dir = root / rec.name / rec.version
    if not pkg_dir.exists():
        return {
            "name": rec.name,
            "version": rec.version,
            "healthy": False,
            "error": "Package directory missing",
        }

    missing = []
    for rel_f in rec.files:
        f_path = pkg_dir / rel_f
        if not f_path.exists():
            missing.append(rel_f)

    return {
        "name": rec.name,
        "version": rec.version,
        "healthy": len(missing) == 0,
        "missing_files": missing,
        "required_by": rec.required_by,
    }


def uninstall_package(
    package_name: str,
    consumer_id: str,
    packages_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Uninstall a package for a given consumer.

    If other products still depend on the package, removal is halted and package is retained.
    Never removes user documents.
    """
    root = get_packages_root(packages_root)
    manifest = load_installed_manifest(root)
    if package_name not in manifest:
        raise PackageError(f"Package '{package_name}' is not installed")

    rec = manifest[package_name]
    if consumer_id in rec.required_by:
        rec.required_by.remove(consumer_id)

    # Check if another consumer still needs it
    if rec.required_by:
        save_installed_manifest(root, manifest)
        return {
            "status": "retained",
            "name": package_name,
            "version": rec.version,
            "reason": f"Package still required by other consumer(s): {rec.required_by}",
            "remaining_consumers": rec.required_by,
        }

    # No consumers left -> safely delete files
    pkg_dir = root / rec.name / rec.version
    if is_protected_user_path(pkg_dir):
        raise PackageSecurityError(f"Refusing to delete inside protected user path: {pkg_dir}")

    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)

    parent_name_dir = root / rec.name
    if parent_name_dir.exists() and not any(parent_name_dir.iterdir()):
        parent_name_dir.rmdir()

    del manifest[package_name]
    save_installed_manifest(root, manifest)

    return {
        "status": "uninstalled",
        "name": package_name,
        "version": rec.version,
        "removed_files": len(rec.files),
    }
