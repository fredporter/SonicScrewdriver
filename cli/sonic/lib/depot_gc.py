"""Read-only Depot retention planning.

`sonic depot gc` answers one question: which *registered* artifacts could be
removed, and why. This module never unlinks, never writes to the depot and
never trusts a path from a manifest without checking containment. The apply
milestone is deliberately absent; it must quote the plan id printed here and
revalidate everything immediately before removing a file.

Sources of truth, in the order the ADR gives them:

1. the depot manifest, for identity, size and digest;
2. the Layer 0 distribution catalogue, for pins (the catalogue names what must
   stay available);
3. the Depot receipts, for references that still need the artifact.

Anything that cannot be enumerated (an unreadable manifest, receipt, pin file
or catalogue) is an *unknown reference*: the plan then proposes no removals at
all, because "I could not read it" is not evidence of "nothing needs it".
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from sonic.lib.catalogue import default_catalogue_path

SCHEMA = "sonic.depot-gc-plan/1"
MANIFEST_FILE = "depot_manifest.json"
PINS_FILE = "pins.json"
RECEIPTS_DIR = "receipts"

KEEP = "keep"
REMOVE = "remove"


class DepotGcError(Exception):
    """Raised when a dry run cannot be produced honestly."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _iter_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _iter_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_strings(item)


def _resolve_member(root: Path, relative: str) -> Tuple[Optional[Path], Optional[str]]:
    """Resolve a manifest path inside ``root`` without following symlinks out."""
    if not relative or not relative.strip():
        return None, "no path recorded"
    relative_path = Path(relative)
    if relative_path.is_absolute():
        return None, "absolute path recorded"
    if any(part == ".." for part in relative_path.parts):
        return None, "path escapes the depot root"
    candidate = root / relative_path
    if candidate.is_symlink():
        return None, "path is a symlink"
    try:
        resolved = candidate.resolve()
    except OSError as exc:  # pragma: no cover - platform dependent
        return None, f"path is unresolvable: {exc}"
    if resolved != root and root not in resolved.parents:
        return None, "path escapes the depot root"
    return candidate, None


def format_bytes(value: int) -> str:
    """Render a byte count without inventing precision."""
    units = ["B", "KB", "MB", "GB", "TB"]
    amount = float(max(value, 0))
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.0f} B" if unit == "B" else f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{value} B"  # pragma: no cover - unreachable


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while chunk := stream.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_time(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _parse_supersede(values: Iterable[str]) -> Tuple[Dict[str, Tuple[str, str]], List[str]]:
    mapping: Dict[str, Tuple[str, str]] = {}
    problems: List[str] = []
    for value in values:
        old, separator, new = value.partition("=")
        if not separator or not old.strip() or not new.strip():
            problems.append(f"--supersede must be OLD=NEW@VERSION: {value!r}")
            continue
        new_id, at, new_version = new.partition("@")
        if not at or not new_id.strip() or not new_version.strip():
            problems.append(f"--supersede successor must be NEW@VERSION: {value!r}")
            continue
        mapping[old.strip()] = (new_id.strip(), new_version.strip())
    return mapping, problems


def _blocked_reason(blockers: List[Dict[str, str]]) -> str:
    kinds = [blocker["kind"] for blocker in blockers]
    if "unknown_references" in kinds:
        return "unknown references — retained (a manifest, receipt, pin file or catalogue could not be read)"
    if "pinned" in kinds:
        return "pinned — retained"
    if "referenced" in kinds:
        return "referenced by a receipt — retained"
    if "integrity" in kinds:
        detail = next(blocker["detail"] for blocker in blockers if blocker["kind"] == "integrity")
        return f"missing integrity — retained ({detail})"
    return "retained"

def _find_reference_cycles(edges: Dict[str, str]) -> Dict[str, List[str]]:
    """Return every node that sits in a requirement cycle, with its cycle path."""
    cycles: Dict[str, List[str]] = {}
    state: Dict[str, int] = {}
    stack: List[str] = []

    def visit(node: str) -> None:
        state[node] = 1
        stack.append(node)
        successor = edges.get(node)
        if successor is not None and successor in edges:
            if state.get(successor) == 1:
                path = stack[stack.index(successor):] + [successor]
                for member in path[:-1]:
                    cycles.setdefault(member, path)
            elif state.get(successor, 0) == 0:
                visit(successor)
        stack.pop()
        state[node] = 2

    for node in sorted(edges):
        if state.get(node, 0) == 0:
            visit(node)
    return cycles


def _load_manifest(root: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    path = root / MANIFEST_FILE
    if not path.is_file():
        return [], [f"depot manifest not found: {path}"]
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [f"depot manifest is unreadable: {path}: {exc}"]

    if isinstance(raw, dict):
        items: List[Tuple[Optional[str], Any]] = list(raw.items())
    elif isinstance(raw, list):
        items = [(None, item) for item in raw]
    else:
        return [], [f"depot manifest must be an object or a list of records: {path}"]

    records: List[Dict[str, Any]] = []
    problems: List[str] = []
    for key, value in items:
        if not isinstance(value, dict):
            problems.append(f"manifest entry {key!r} is not an object")
            continue
        artifact_id = value.get("id") or key
        if not isinstance(artifact_id, str) or not artifact_id.strip():
            problems.append(f"manifest entry {key!r} has no id")
            continue
        if key is not None and value.get("id") and value["id"] != key:
            problems.append(
                f"manifest key {key!r} disagrees with its id {value['id']!r}; identity is ambiguous"
            )
            continue
        records.append(dict(value, id=artifact_id))
    return records, problems


def _load_receipts(root: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    receipts_dir = root / RECEIPTS_DIR
    if not receipts_dir.exists():
        return [], []
    if not receipts_dir.is_dir():
        return [], [f"receipts path is not a directory: {receipts_dir}"]

    receipts: List[Dict[str, Any]] = []
    problems: List[str] = []
    for path in sorted(receipts_dir.rglob("*.json")):
        if path.is_symlink():
            problems.append(f"receipt is a symlink: {path.relative_to(root).as_posix()}")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"receipt is unreadable: {path.relative_to(root).as_posix()}: {exc}")
            continue
        receipts.append(
            {
                "file": path.relative_to(root).as_posix(),
                "action": str(data.get("action", "")) if isinstance(data, dict) else "",
                "at": str(data.get("at", "")) if isinstance(data, dict) else "",
                "tokens": {token for token in _iter_strings(data) if token},
            }
        )
    return receipts, problems


def _load_pins_file(path: Path) -> Tuple[Dict[str, str], Optional[str]]:
    if not path.exists():
        return {}, None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, f"local pins are unreadable: {path}: {exc}"

    container: Any = raw.get("pins", raw) if isinstance(raw, dict) else raw
    pins: Dict[str, str] = {}
    if isinstance(container, dict):
        for key, value in container.items():
            if isinstance(value, dict):
                pins[str(key)] = str(value.get("reason") or value.get("note") or "pinned locally")
            elif isinstance(value, str) and value.strip():
                pins[str(key)] = value.strip()
            elif value is True:
                pins[str(key)] = "pinned locally"
    elif isinstance(container, list):
        for item in container:
            if isinstance(item, dict) and item.get("id"):
                pins[str(item["id"])] = str(item.get("reason") or "pinned locally")
            elif isinstance(item, str) and item.strip():
                pins[item.strip()] = "pinned locally"
    return pins, None


def _load_catalogue(path: Path) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str], str, Optional[str]]:
    """Return id pins, digest pins, file-name pins, status and any problem."""
    if not path.is_file():
        return {}, {}, {}, "not_found", f"base catalogue not found: {path}"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, {}, {}, "unreadable", f"base catalogue is unreadable: {path}: {exc}"

    ids: Dict[str, str] = {}
    digests: Dict[str, str] = {}
    names: Dict[str, str] = {}

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            declared_id = value.get("id")
            if isinstance(declared_id, str) and declared_id:
                ids[declared_id] = "declared in the Layer 0 catalogue"
                digest = value.get("sha256")
                if isinstance(digest, str) and digest:
                    digests[digest.lower()] = f"declared in the Layer 0 catalogue as {declared_id}"
                file_name = value.get("file_name")
                if isinstance(file_name, str) and file_name:
                    names[file_name] = f"declared in the Layer 0 catalogue as {declared_id}"
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(raw)
    return ids, digests, names, "loaded", None


def _receipt_references(
    receipts: Iterable[Dict[str, Any]],
    tokens: Iterable[str],
) -> List[Dict[str, str]]:
    wanted = {token for token in tokens if token}
    references: List[Dict[str, str]] = []
    for receipt in receipts:
        matched = bool(wanted & receipt["tokens"])
        if not matched:
            matched = any(
                token.endswith("/" + candidate)
                for token in receipt["tokens"]
                for candidate in wanted
            )
        if matched:
            references.append(
                {"source": f"receipt:{receipt['file']}", "action": receipt["action"], "at": receipt["at"]}
            )
    return references



def build_gc_plan(
    depot_dir: Path,
    *,
    retain_days: Optional[int] = None,
    supersede: Iterable[str] = (),
    verify: bool = False,
    catalogue_path: Optional[Path] = None,
    pins_path: Optional[Path] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Inventory the depot and propose removals without touching anything."""
    if retain_days is not None and retain_days < 0:
        raise DepotGcError("--retain-days must be zero or greater")

    root = Path(depot_dir).expanduser()
    if not root.is_absolute():
        raise DepotGcError(f"depot root must be an absolute path: {root}")
    if root.is_symlink():
        raise DepotGcError(f"depot root must not be a symlink: {root}")
    root = root.resolve()
    if not root.is_dir():
        raise DepotGcError(f"depot root is not a directory: {root}")

    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise DepotGcError("plan time must be timezone-aware")

    records, problems = _load_manifest(root)
    receipts, receipt_problems = _load_receipts(root)
    problems.extend(receipt_problems)

    local_pins, pins_problem = _load_pins_file(
        Path(pins_path).expanduser() if pins_path else root / PINS_FILE
    )
    if pins_problem:
        problems.append(pins_problem)

    catalogue_target = Path(catalogue_path).expanduser() if catalogue_path else default_catalogue_path()
    (
        catalogue_ids,
        catalogue_digests,
        catalogue_names,
        catalogue_status,
        catalogue_problem,
    ) = _load_catalogue(catalogue_target)
    if catalogue_problem:
        problems.append(catalogue_problem)

    supersede_map, supersede_problems = _parse_supersede(supersede)
    problems.extend(supersede_problems)

    artifacts: List[Dict[str, Any]] = []
    by_id: Dict[str, Dict[str, Any]] = {}
    for record in records:
        artifact_id = record["id"]
        version = str(record.get("version", "latest"))
        kind = str(record.get("kind", "unknown"))
        relative = str(record.get("relative_path") or record.get("path") or record.get("file_name") or "")
        file_name = str(record.get("file_name") or Path(relative).name)
        declared_sha = str(record.get("sha256") or "").lower()
        declared_bytes = int(record.get("size_bytes") or 0)

        path, path_problem = _resolve_member(root, relative)
        stat: Optional[os.stat_result] = None
        integrity = "unchecked"
        detail = path_problem or ""

        if path is not None:
            try:
                stat = path.stat()
            except OSError as exc:
                integrity, detail = "missing_file", str(exc)
            else:
                if not path.is_file():
                    integrity, detail = "not_a_file", "recorded path is not a regular file"
                elif not declared_sha:
                    integrity, detail = "missing_digest", "manifest records no SHA-256"
                elif declared_bytes and stat.st_size != declared_bytes:
                    integrity, detail = (
                        "size_mismatch",
                        f"recorded {declared_bytes} bytes, found {stat.st_size}",
                    )
                else:
                    integrity = "unverified"
        elif path_problem:
            integrity = "unsafe_path"

        pins: List[Dict[str, str]] = []
        if artifact_id in local_pins:
            pins.append({"source": "pins.json", "detail": local_pins[artifact_id]})
        if artifact_id in catalogue_ids:
            pins.append({"source": "catalogue", "detail": catalogue_ids[artifact_id]})
        elif declared_sha and declared_sha in catalogue_digests:
            pins.append({"source": "catalogue", "detail": catalogue_digests[declared_sha]})
        elif file_name in catalogue_names:
            pins.append({"source": "catalogue", "detail": catalogue_names[file_name]})

        tokens = [artifact_id, f"{artifact_id}@{version}", relative, file_name]
        if relative:
            tokens.append(Path(relative).name)
        if declared_sha:
            tokens.append(declared_sha)
        references = _receipt_references(receipts, tokens)

        artifacts.append(
            {
                "id": artifact_id,
                "kind": kind,
                "version": version,
                "relative_path": relative,
                "path": str(path) if path is not None else None,
                "bytes": stat.st_size if stat else declared_bytes,
                "declared_bytes": declared_bytes,
                "sha256": declared_sha,
                "added_at": str(record.get("added_at", "")),
                "target_profiles": list(record.get("target_profiles") or []),
                "integrity": {"status": integrity, "detail": detail},
                "pins": pins,
                "references": references,
                "hardlink": {
                    "device": stat.st_dev if stat else None,
                    "inode": stat.st_ino if stat else None,
                    "link_count": stat.st_nlink if stat else None,
                },
                "decision": KEEP,
                "reason": "retained — no retention policy matched",
                "blockers": [],
                "verified_at": None,
            }
        )
        by_id[artifact_id] = artifacts[-1]

    for old, (new_id, new_version) in supersede_map.items():
        if old not in by_id:
            problems.append(f"--supersede names an artifact that is not registered: {old!r}")
        new_record = by_id.get(new_id)
        if new_record is None:
            problems.append(f"--supersede successor is not registered: {new_id!r}")
        elif new_record["version"] != new_version:
            problems.append(
                f"--supersede successor {new_id} is version {new_record['version']}, not {new_version}"
            )


    # ---- refusals that do not depend on the policy -------------------------
    for artifact in artifacts:
        if problems:
            artifact["blockers"].append(
                {"kind": "unknown_references", "detail": "; ".join(problems)}
            )
        if artifact["pins"]:
            artifact["blockers"].append(
                {
                    "kind": "pinned",
                    "detail": "; ".join(f"{pin['source']}: {pin['detail']}" for pin in artifact["pins"]),
                }
            )
        if artifact["references"]:
            artifact["blockers"].append(
                {
                    "kind": "referenced",
                    "detail": "; ".join(reference["source"] for reference in artifact["references"]),
                }
            )
        if artifact["integrity"]["status"] not in {"unverified", "verified"}:
            artifact["blockers"].append(
                {
                    "kind": "integrity",
                    "detail": artifact["integrity"]["detail"] or artifact["integrity"]["status"],
                }
            )

    # ---- candidate selection ----------------------------------------------
    groups: Dict[Tuple[str, int], List[Dict[str, Any]]] = {}
    for artifact in artifacts:
        if artifact["integrity"]["status"] in {"unverified", "verified"} and artifact["sha256"]:
            groups.setdefault((artifact["sha256"], artifact["bytes"]), []).append(artifact)

    duplicate_of: Dict[str, str] = {}
    for members in groups.values():
        if len(members) < 2:
            continue
        keeper = sorted(
            members,
            key=lambda item: (
                0 if item["pins"] else 1,
                0 if item["references"] else 1,
                item["id"],
            ),
        )[0]
        for member in members:
            if member is not keeper:
                duplicate_of[member["id"]] = keeper["id"]

    candidates: List[Dict[str, Any]] = []
    for artifact in artifacts:
        if artifact["blockers"]:
            artifact["reason"] = _blocked_reason(artifact["blockers"])
            continue

        if artifact["id"] in supersede_map:
            new_id, new_version = supersede_map[artifact["id"]]
            artifact["reason"] = f"superseded by {new_id}@{new_version}"
            candidates.append(artifact)
            continue

        if artifact["id"] in duplicate_of:
            artifact["reason"] = f"duplicate of {duplicate_of[artifact['id']]}"
            candidates.append(artifact)
            continue

        if retain_days is not None:
            added = _parse_time(artifact["added_at"])
            if added is not None and moment - added > timedelta(days=retain_days):
                artifact["reason"] = f"expired (added {artifact['added_at']})"
                candidates.append(artifact)
                continue

        artifact["reason"] = "retained — no retention policy matched"


    # ---- retention closure -------------------------------------------------
    # A removal is only safe while the copy that keeps its content is retained by
    # the same plan. A verified keeper that is itself scheduled for removal would
    # take the payload with it, so the removal set is pruned to a fixed point, and
    # self-references and cycles are refused outright.
    requirements: Dict[str, str] = {}
    for artifact in candidates:
        artifact_id = artifact["id"]
        if artifact_id in duplicate_of:
            requirements[artifact_id] = duplicate_of[artifact_id]
        elif artifact_id in supersede_map:
            requirements[artifact_id] = supersede_map[artifact_id][0]

    pending: Dict[str, Dict[str, Any]] = {artifact["id"]: artifact for artifact in candidates}

    def keep(artifact: Dict[str, Any], kind: str, reason: str, detail: str = "") -> None:
        artifact["decision"] = KEEP
        artifact["reason"] = reason
        artifact["blockers"].append({"kind": kind, "detail": detail or reason})
        pending.pop(artifact["id"], None)

    for artifact_id in sorted(list(pending)):
        if requirements.get(artifact_id) == artifact_id:
            keep(
                pending[artifact_id],
                "self_reference",
                "superseded by itself — retained (no distinct successor)",
            )

    cycles = _find_reference_cycles(
        {
            artifact_id: requirement
            for artifact_id, requirement in requirements.items()
            if artifact_id in pending
        }
    )
    for artifact_id, path in sorted(cycles.items()):
        if artifact_id in pending:
            keep(
                pending[artifact_id],
                "reference_cycle",
                f"reference cycle — retained ({' → '.join(path)})",
            )

    changed = True
    while changed:
        changed = False
        # A candidate whose keeper or successor is also a candidate cannot go:
        # the copy that would preserve its content sits in the same removal set.
        for artifact_id in sorted(list(pending)):
            requirement = requirements.get(artifact_id)
            if requirement and requirement in pending:
                keep(
                    pending[artifact_id],
                    "unretained_reference",
                    f"required copy {requirement} is also scheduled for removal — retained",
                )
                changed = True
        # ...and the keeper stays too, so the plan cannot invert the pair and
        # remove the copy it just called the keeper.
        dependents: Dict[str, List[str]] = {}
        for artifact_id, requirement in requirements.items():
            if artifact_id not in pending:
                dependents.setdefault(requirement, []).append(artifact_id)
        for requirement in sorted(dependents):
            if requirement in pending:
                keep(
                    pending[requirement],
                    "keeper_required",
                    f"keeper/successor for {', '.join(sorted(dependents[requirement]))} — retained",
                )
                changed = True

    # ---- cryptographic confirmation ---------------------------------------
    def confirm(artifact: Dict[str, Any]) -> Optional[str]:
        if not artifact["path"] or artifact["integrity"]["status"] not in {"unverified", "verified"}:
            return artifact["integrity"]["detail"] or artifact["integrity"]["status"]
        try:
            actual = _hash_file(Path(artifact["path"]))
        except OSError as exc:
            return f"unreadable: {exc}"
        if actual != artifact["sha256"]:
            artifact["integrity"] = {
                "status": "checksum_mismatch",
                "detail": f"recorded {artifact['sha256']}, computed {actual}",
            }
            return artifact["integrity"]["detail"]
        artifact["integrity"] = {"status": "verified", "detail": "SHA-256 matched at plan time"}
        artifact["verified_at"] = moment.isoformat()
        return None

    final: List[Dict[str, Any]] = []
    for artifact_id in sorted(pending):
        artifact = pending[artifact_id]
        failure = confirm(artifact)
        if failure:
            keep(artifact, "integrity", f"missing integrity — retained ({failure})", failure)
            continue

        requirement = requirements.get(artifact_id)
        if requirement:
            keeper = by_id[requirement]
            failure = confirm(keeper)
            if failure:
                if artifact_id in duplicate_of:
                    keep(
                        artifact,
                        "sole_verified_copy",
                        f"duplicate of {requirement} — retained as the only verified copy "
                        f"({failure})",
                        failure,
                    )
                else:
                    keep(
                        artifact,
                        "unverified_successor",
                        f"superseded by {requirement} — retained until the successor verifies "
                        f"({failure})",
                        failure,
                    )
                continue
            if keeper["decision"] != KEEP:
                keep(
                    artifact,
                    "unretained_reference",
                    f"required copy {requirement} is not retained — kept",
                )
                continue

        artifact["decision"] = REMOVE
        final.append(artifact)

    if verify:
        for artifact in artifacts:
            if artifact["decision"] == REMOVE or artifact["verified_at"]:
                continue
            if artifact["integrity"]["status"] in {"unverified", "verified"}:
                failure = confirm(artifact)
                if failure:
                    artifact["blockers"].append({"kind": "integrity", "detail": failure})
                    if artifact["reason"] == "retained — no retention policy matched":
                        artifact["reason"] = f"missing integrity — retained ({failure})"


    # ---- totals ------------------------------------------------------------
    removal_ids = {artifact["id"] for artifact in final}
    inode_sizes: Dict[Tuple[int, int], int] = {}
    inode_artifacts: Dict[Tuple[int, int], List[str]] = {}
    for artifact in artifacts:
        device, inode = artifact["hardlink"]["device"], artifact["hardlink"]["inode"]
        if device is None or inode is None:
            continue
        key = (int(device), int(inode))
        inode_sizes.setdefault(key, artifact["bytes"])
        inode_artifacts.setdefault(key, []).append(artifact["id"])

    eligible_inodes = {
        key
        for key, ids in inode_artifacts.items()
        if any(artifact_id in removal_ids for artifact_id in ids)
    }
    eligible_bytes = sum(inode_sizes[key] for key in eligible_inodes)

    reclaimable = 0
    for key in eligible_inodes:
        representative = next(
            artifact
            for artifact in artifacts
            if artifact["hardlink"]["device"] == key[0] and artifact["hardlink"]["inode"] == key[1]
        )
        if (representative["hardlink"]["link_count"] or 1) <= 1:
            reclaimable += inode_sizes[key]

    usage = shutil.disk_usage(root)
    totals = {
        "artifact_count": len(artifacts),
        "artifact_bytes": sum(artifact["bytes"] for artifact in artifacts),
        "unique_inode_bytes": sum(inode_sizes.values()),
        "retained_count": len(artifacts) - len(final),
        "eligible_count": len(final),
        "eligible_artifact_bytes": eligible_bytes,
        "estimated_reclaimable_bytes": reclaimable,
    }

    policy = {
        "retain_days": retain_days,
        "supersede": {old: f"{new}@{version}" for old, (new, version) in sorted(supersede_map.items())},
        "verify_all": bool(verify),
    }

    body = {
        "schema": SCHEMA,
        "depot_root": str(root),
        "policy": policy,
        "artifacts": [
            {
                "id": artifact["id"],
                "kind": artifact["kind"],
                "version": artifact["version"],
                "relative_path": artifact["relative_path"],
                "bytes": artifact["bytes"],
                "sha256": artifact["sha256"],
                "device": artifact["hardlink"]["device"],
                "inode": artifact["hardlink"]["inode"],
                "link_count": artifact["hardlink"]["link_count"],
                "decision": artifact["decision"],
                "reason": artifact["reason"],
                "blockers": sorted(blocker["kind"] for blocker in artifact["blockers"]),
            }
            for artifact in sorted(artifacts, key=lambda item: item["id"])
        ],
        "totals": totals,
    }
    plan_id = "gc-" + hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()

    refusals: Dict[str, List[str]] = {}
    for artifact in artifacts:
        for blocker in artifact["blockers"]:
            refusals.setdefault(blocker["kind"], []).append(artifact["id"])

    return {
        "schema": SCHEMA,
        "plan_id": plan_id,
        "mode": "dry-run",
        "generated_at": moment.isoformat(),
        "depot_root": str(root),
        "policy": policy,
        "catalogue": {"path": str(catalogue_target), "status": catalogue_status},
        "pins": {"path": str(pins_path or root / PINS_FILE), "count": len(local_pins)},
        "receipts": {"count": len(receipts), "root": str(root / RECEIPTS_DIR)},
        "problems": problems,
        "scope": (
            "Registered artifacts only. Unregistered files, other application stores, "
            "Docker volumes and the Trash are outside this plan."
        ),
        "artifacts": sorted(artifacts, key=lambda item: item["id"]),
        "totals": totals,
        "volume": {
            "path": str(root),
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "after_used_bytes": None,
            "note": (
                "APFS shared blocks and clone groups make the after figure unpredictable; "
                "apply must measure the volume before and after and report the delta."
            ),
        },
        "refusals": refusals,
        "read_only": True,
    }
