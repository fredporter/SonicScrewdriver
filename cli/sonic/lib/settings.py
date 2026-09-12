"""Standalone state ownership and non-destructive legacy import."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import uuid
from datetime import datetime, timezone


def state_root() -> Path:
    value = os.environ.get("UDOS_HOME")
    if value is not None and not value.strip():
        raise ValueError("UDOS_HOME must not be empty")
    base = Path(value).expanduser() if value else Path.home() / "Code" / ".udos"
    if not base.is_absolute():
        raise ValueError("UDOS_HOME must be an absolute path")
    return base / "sonic"


def import_legacy(source: Path, apply: bool = False) -> dict:
    """Copy explicit legacy files into a separate import namespace; never overwrite.

    Symlinks and special files are rejected. Originals remain untouched.
    This is a byte-preserving intake, not an implicit schema migration.
    Atomic: stages into .staging-XXXX, writes receipt.json, then renames.
    """
    if source.is_symlink():
        raise ValueError("Legacy source must not be a symlink")
    source = source.resolve(strict=True)
    if not source.is_dir():
        raise ValueError("Legacy source must be a directory")
    target = state_root() / "imports" / "legacy"
    resolved_target = target.resolve()
    if source == resolved_target or source in resolved_target.parents or resolved_target in source.parents:
        raise ValueError("Legacy source and import destination must not overlap")
    if target.exists():
        raise ValueError(f"Import destination already exists: {target}")
    entries = []
    for path in sorted(source.rglob("*")):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError(f"Unsupported legacy entry: {path}")
        if path.is_dir():
            continue
        relative = path.relative_to(source)
        dest = target / relative
        if any(p.is_symlink() for p in [dest, *dest.parents]):
            raise ValueError(f"Import destination contains a symlink: {dest}")
        if dest.exists():
            raise ValueError(f"Import destination already exists: {dest}")
        entries.append({"path": relative.as_posix(), "bytes": path.stat().st_size,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    copied = []
    receipt_data = None
    if apply:
        staging_dir = target.parent / f".staging-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        try:
            staging_dir.mkdir(parents=True, exist_ok=True)
            for entry in entries:
                original = source / entry["path"]
                content = original.read_bytes()
                if original.is_symlink() or hashlib.sha256(content).hexdigest() != entry["sha256"]:
                    raise ValueError(f"Source changed during import: {original}")
                staged_dest = staging_dir / entry["path"]
                staged_dest.parent.mkdir(parents=True, exist_ok=True)
                with staged_dest.open("xb") as stream:
                    stream.write(content)
                staged_dest.chmod(0o600)
                copied.append(entry["path"])

            receipt_data = {
                "schema": "sonic.intake-receipt/1",
                "source": str(source),
                "destination": str(target),
                "imported_at": datetime.now(timezone.utc).isoformat(),
                "file_count": len(entries),
                "total_bytes": sum(e["bytes"] for e in entries),
                "files": entries,
            }
            receipt_file = staging_dir / "receipt.json"
            receipt_file.write_text(json.dumps(receipt_data, indent=2), encoding="utf-8")
            receipt_file.chmod(0o600)

            staging_dir.rename(target)
        except Exception:
            if staging_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)
            raise

    res = {
        "schema": "sonic.legacy-import/1",
        "applied": apply,
        "source": str(source),
        "destination": str(target),
        "files": entries,
        "copied": copied,
        "originals_preserved": True,
    }
    if receipt_data is not None:
        res["receipt"] = receipt_data
    return res
