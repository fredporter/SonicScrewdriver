"""Base distribution catalogue (Layer 0 seed) and the local library snapshot.

The base catalogue is distributable data: metadata only, no payloads, no local
paths, no credentials. It is owned by global-knowledge and shipped with every
device. Retention, verification results and receipts are local state and are
added by the snapshot, which feeds consumers such as GridCore teletext 600-609.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sonic.lib.depot import get_default_depot_roots, load_depot_manifest

SCHEMA = "sonic.catalogue/1"
SNAPSHOT_SCHEMA = "ucode-library/1"


class CatalogueError(Exception):
    """Raised when the base catalogue is missing, unreadable or unsupported."""


def default_catalogue_path() -> Path:
    override = os.environ.get("SONIC_CATALOGUE_PATH")
    if override:
        return Path(override).expanduser()
    return Path.home() / "Public" / "global-knowledge" / "datasets" / "distribution_catalogue.json"


def load_catalogue(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load and validate the distributable base catalogue."""
    target = Path(path).expanduser() if path else default_catalogue_path()
    if not target.is_file():
        raise CatalogueError(f"Base catalogue not found: {target}")

    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogueError(f"Base catalogue is unreadable: {target}: {exc}") from exc

    if not isinstance(data, dict):
        raise CatalogueError(f"Base catalogue must be a JSON object: {target}")
    if data.get("schema") != SCHEMA:
        raise CatalogueError(f"Unsupported catalogue schema in {target}: {data.get('schema')!r}")

    titles = data.get("titles")
    if not isinstance(titles, list):
        raise CatalogueError(f"Base catalogue titles must be a list: {target}")
    for title in titles:
        if not isinstance(title, dict) or not title.get("id") or not isinstance(title.get("editions"), list):
            raise CatalogueError(f"Malformed title record in {target}")
        for edition in title["editions"]:
            if not isinstance(edition, dict) or not edition.get("id") or not isinstance(edition.get("capsules"), list):
                raise CatalogueError(f"Malformed edition record in {target}: {title.get('id')}")

    return data


def catalogue_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Count what the base catalogue declares, grouped by library status."""
    editions = 0
    capsules = 0
    statuses: Dict[str, int] = {}
    for title in data.get("titles", []):
        for edition in title.get("editions", []):
            editions += 1
            status = str(edition.get("status", "research"))
            statuses[status] = statuses.get(status, 0) + 1
            capsules += len(edition.get("capsules", []))

    return {
        "schema": data.get("schema"),
        "version": data.get("version"),
        "layer": data.get("layer"),
        "titles": len(data.get("titles", [])),
        "editions": editions,
        "capsules": capsules,
        "statuses": statuses,
        "managed_lanes": len(data.get("managed_lanes", [])),
    }


def _record_is_verified(record: Any, declared_sha: Optional[str], depot_dir: Optional[Path]) -> bool:
    if record is None or not record.sha256:
        return False
    if declared_sha and record.sha256.lower() != declared_sha.lower():
        return False
    if depot_dir is not None and record.relative_path:
        if not (Path(depot_dir).expanduser() / record.relative_path).is_file():
            return False
    return True


def build_snapshot(
    catalogue: Dict[str, Any],
    depot_dir: Optional[Path] = None,
    generated_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Merge the base catalogue with local depot state into a library snapshot.

    Without a depot the snapshot still describes every declared title, with
    nothing marked verified: an honest empty state beats invented availability.
    """
    manifest = load_depot_manifest(depot_dir) if depot_dir is not None else {}

    titles: List[Dict[str, Any]] = []
    retained_ids = set()
    retained_bytes = 0

    for title in catalogue.get("titles", []):
        editions: List[Dict[str, Any]] = []
        for edition in title.get("editions", []):
            capsules: List[Dict[str, Any]] = []
            for capsule in edition.get("capsules", []):
                capsule_id = str(capsule.get("id", ""))
                record = manifest.get(capsule_id)
                declared_sha = capsule.get("sha256")
                checked = _record_is_verified(record, declared_sha, depot_dir)

                size = int(record.size_bytes) if record is not None else int(capsule.get("bytes") or 0)
                sha = declared_sha or (record.sha256 if record is not None else None)
                if record is not None and capsule_id not in retained_ids:
                    retained_ids.add(capsule_id)
                    retained_bytes += int(record.size_bytes)

                capsules.append(
                    {
                        "id": capsule_id,
                        "kind": capsule.get("kind", "capsule"),
                        "version": str(capsule.get("version", "")),
                        "sha256": sha,
                        "bytes": size,
                        "verified": checked,
                    }
                )
            editions.append(
                {
                    "id": edition.get("id", ""),
                    "treatment": edition.get("treatment", "authentic"),
                    "status": edition.get("status", "research"),
                    "mediaPolicy": edition.get("media_policy", "bundled"),
                    "capsules": capsules,
                }
            )
        titles.append(
            {
                "id": title.get("id", ""),
                "title": title.get("title", title.get("id", "")),
                "summary": title.get("summary", ""),
                "provenance": title.get("provenance", "upstream"),
                "editions": editions,
            }
        )

    depot = {
        "root": str(Path(depot_dir).expanduser().resolve()) if depot_dir is not None else "not configured",
        "retainedBytes": retained_bytes,
        "reclaimableBytes": 0,
    }

    return {
        "schema": SNAPSHOT_SCHEMA,
        "generatedAt": generated_at or datetime.now(timezone.utc).isoformat(),
        "depot": depot,
        "titles": titles,
    }


def resolve_depot_root(explicit: Optional[Path] = None) -> Optional[Path]:
    """Resolve the depot root, preferring an explicit path."""
    if explicit is not None:
        return Path(explicit).expanduser()
    for candidate in get_default_depot_roots():
        if candidate.is_dir():
            return candidate
    return None
