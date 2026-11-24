"""Read-only Depot GC dry-run tests.

Every case runs against a disposable depot: nothing here reads or writes the
live ``~/Code/Depot``.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sonic.lib.depot_gc import DepotGcError, build_gc_plan

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
PAYLOAD = b"payload"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_catalogue(path: Path, capsules=()) -> Path:
    payload = {
        "schema": "sonic.catalogue/1",
        "version": "0.0.1",
        "layer": 0,
        "titles": [{"id": "title", "editions": [{"id": "edition", "capsules": list(capsules)}]}],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def make_depot(tmp_path: Path, name: str = "depot") -> Path:
    depot = tmp_path / name
    depot.mkdir()
    return depot


def add_artifact(
    depot: Path,
    artifact_id: str,
    *,
    content: bytes = PAYLOAD,
    relative: str = "",
    kind: str = "package",
    version: str = "1.0.0",
    added_at: str = "",
    sha256: str = "",
    size_bytes: int | None = None,
    make_file: bool = True,
):
    relative = relative or f"{artifact_id}.tgz"
    path = depot / relative
    if make_file:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return {
        "id": artifact_id,
        "kind": kind,
        "version": version,
        "file_name": Path(relative).name,
        "relative_path": relative,
        "size_bytes": len(content) if size_bytes is None else size_bytes,
        "sha256": sha256 or _sha(content),
        "added_at": added_at or NOW.isoformat(),
    }


def write_manifest(depot: Path, records) -> Path:
    manifest = {record["id"]: record for record in records}
    path = depot / "depot_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def _plan(depot: Path, catalogue: Path, **kwargs):
    return build_gc_plan(depot, catalogue_path=catalogue, now=NOW, **kwargs)


def _artifact(plan, artifact_id):
    return next(item for item in plan["artifacts"] if item["id"] == artifact_id)


def _blocker_kinds(artifact):
    return [blocker["kind"] for blocker in artifact["blockers"]]


def test_gc_requires_an_explicit_depot(runner, tmp_path: Path):
    from sonic.cli import cli

    result = runner.invoke(cli, ["depot", "gc"], env={"SONIC_DEPOT_ROOT": ""})
    assert result.exit_code != 0
    assert "explicit depot root is required" in result.output


def test_gc_inventory_reports_identity_and_keeps_unpinned(tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(depot, [add_artifact(depot, "pkg")])

    plan = _plan(depot, catalogue)

    assert plan["schema"] == "sonic.depot-gc-plan/1"
    assert plan["mode"] == "dry-run"
    assert plan["read_only"] is True
    artifact = _artifact(plan, "pkg")
    assert artifact["bytes"] == len(PAYLOAD)
    assert artifact["relative_path"] == "pkg.tgz"
    assert artifact["integrity"]["status"] == "unverified"
    assert artifact["decision"] == "keep"
    assert artifact["reason"] == "retained — no retention policy matched"
    assert artifact["verified_at"] is None
    assert artifact["hardlink"]["link_count"] == 1
    assert plan["totals"]["artifact_count"] == 1
    assert plan["totals"]["eligible_count"] == 0


def test_gc_handles_flat_and_nested_manifest_paths(tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(
        depot,
        [
            add_artifact(depot, "flat-pkg", relative="flat-pkg.tgz"),
            add_artifact(depot, "nested-font", relative="artifacts/asset/fonts/classic/c64.bdf", content=b"font"),
        ],
    )

    plan = _plan(depot, catalogue)

    flat = _artifact(plan, "flat-pkg")
    nested = _artifact(plan, "nested-font")
    assert flat["path"] == str(depot / "flat-pkg.tgz")
    assert nested["path"] == str(depot / "artifacts/asset/fonts/classic/c64.bdf")
    assert nested["integrity"]["status"] == "unverified"
    assert plan["totals"]["artifact_bytes"] == len(PAYLOAD) + len(b"font")


def test_gc_refuses_paths_outside_the_depot(tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    (tmp_path / "outside.tgz").write_bytes(PAYLOAD)
    write_manifest(depot, [add_artifact(depot, "escape", relative="../outside.tgz", make_file=False)])

    plan = _plan(depot, catalogue)

    artifact = _artifact(plan, "escape")
    assert artifact["integrity"]["status"] == "unsafe_path"
    assert artifact["path"] is None
    assert "integrity" in _blocker_kinds(artifact)
    assert artifact["decision"] == "keep"
    assert plan["totals"]["eligible_count"] == 0


def test_gc_refuses_missing_files_and_size_mismatches(tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    missing = add_artifact(depot, "missing", make_file=False)
    short = add_artifact(depot, "short", content=b"too short", size_bytes=len(PAYLOAD))
    write_manifest(depot, [missing, short])

    plan = _plan(depot, catalogue)

    assert _artifact(plan, "missing")["integrity"]["status"] == "missing_file"
    assert _artifact(plan, "short")["integrity"]["status"] == "size_mismatch"
    assert plan["totals"]["eligible_count"] == 0


def test_gc_pins_from_the_catalogue_and_a_local_pins_file(tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(
        tmp_path / "catalogue.json",
        capsules=[
            {
                "id": "from-catalogue",
                "kind": "package",
                "version": "1.0.0",
                "file_name": "from-catalogue.tgz",
                "sha256": _sha(PAYLOAD),
                "bytes": len(PAYLOAD),
            }
        ],
    )
    (depot / "pins.json").write_text(
        json.dumps({"pins": {"from-pins": "retained for the January image"}}), encoding="utf-8"
    )
    write_manifest(depot, [add_artifact(depot, "from-catalogue"), add_artifact(depot, "from-pins")])

    plan = _plan(depot, catalogue)

    catalogue_pin = _artifact(plan, "from-catalogue")
    local_pin = _artifact(plan, "from-pins")
    assert catalogue_pin["reason"] == "pinned — retained"
    assert catalogue_pin["pins"][0]["source"] == "catalogue"
    assert local_pin["reason"] == "pinned — retained"
    assert local_pin["pins"][0]["source"] == "pins.json"
    assert plan["pins"]["count"] == 1


def test_gc_receipt_reference_retains_an_artifact(tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(depot, [add_artifact(depot, "pkg")])
    receipts = depot / "receipts" / "2026"
    receipts.mkdir(parents=True)
    (receipts / "removal.json").write_text(
        json.dumps(
            {
                "schema": "sonic.depot-receipt/1",
                "action": "depot_registered",
                "at": "2026-11-24T00:00:00Z",
                "artifact": "pkg",
            }
        ),
        encoding="utf-8",
    )

    plan = _plan(depot, catalogue)

    artifact = _artifact(plan, "pkg")
    assert artifact["reason"] == "referenced by a receipt — retained"
    assert artifact["references"][0]["source"] == "receipt:receipts/2026/removal.json"
    assert plan["receipts"]["count"] == 1



def test_gc_duplicate_is_eligible_and_bytes_are_counted_once(tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(depot, [add_artifact(depot, "pkg-a"), add_artifact(depot, "pkg-b")])

    plan = _plan(depot, catalogue)

    keeper = _artifact(plan, "pkg-a")
    duplicate = _artifact(plan, "pkg-b")
    assert keeper["decision"] == "keep"
    assert duplicate["decision"] == "remove"
    assert duplicate["reason"] == "duplicate of pkg-a"
    assert duplicate["verified_at"] == NOW.isoformat()
    assert plan["totals"]["eligible_count"] == 1
    assert plan["totals"]["eligible_artifact_bytes"] == len(PAYLOAD)
    assert plan["totals"]["estimated_reclaimable_bytes"] == len(PAYLOAD)
    assert plan["totals"]["unique_inode_bytes"] == 2 * len(PAYLOAD)


def test_gc_hardlinked_duplicate_is_eligible_but_frees_nothing(tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    first = add_artifact(depot, "pkg-a")
    second = add_artifact(depot, "pkg-b", make_file=False)
    os.link(depot / "pkg-a.tgz", depot / "pkg-b.tgz")
    write_manifest(depot, [first, second])

    plan = _plan(depot, catalogue)

    duplicate = _artifact(plan, "pkg-b")
    assert duplicate["decision"] == "remove"
    assert duplicate["hardlink"]["link_count"] == 2
    assert plan["totals"]["artifact_bytes"] == 2 * len(PAYLOAD)
    assert plan["totals"]["unique_inode_bytes"] == len(PAYLOAD)
    assert plan["totals"]["eligible_artifact_bytes"] == len(PAYLOAD)
    assert plan["totals"]["estimated_reclaimable_bytes"] == 0


def test_gc_expiry_without_a_keeper_is_retained(tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    old = (NOW - timedelta(days=40)).isoformat()
    write_manifest(depot, [add_artifact(depot, "old-pkg", added_at=old)])

    expired = _plan(depot, catalogue, retain_days=30)
    retained = _plan(depot, catalogue, retain_days=60)

    artifact = _artifact(expired, "old-pkg")
    assert expired["totals"]["eligible_count"] == 0
    assert artifact["decision"] == "keep"
    assert artifact["reason"] == (
        "expired — retained (no verified keeper or successor would remain after the plan)"
    )
    assert expired["refusals"]["sole_verified_copy"] == ["old-pkg"]
    assert _artifact(retained, "old-pkg")["reason"] == "retained — no retention policy matched"
    assert retained["plan_id"] != expired["plan_id"]


def test_gc_supersede_requires_a_verified_successor(tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(
        depot,
        [
            add_artifact(depot, "old-pkg", version="1.0.0"),
            add_artifact(depot, "new-pkg", version="2.0.0", content=b"successor"),
        ],
    )

    plan = _plan(depot, catalogue, supersede=["old-pkg=new-pkg@2.0.0"])
    assert _artifact(plan, "old-pkg")["decision"] == "remove"
    assert _artifact(plan, "old-pkg")["reason"] == "superseded by new-pkg@2.0.0"
    assert _artifact(plan, "new-pkg")["decision"] == "keep"

    wrong = _plan(depot, catalogue, supersede=["old-pkg=new-pkg@9.9.9"])
    assert wrong["totals"]["eligible_count"] == 0
    assert any("not 9.9.9" in problem for problem in wrong["problems"])
    assert _artifact(wrong, "old-pkg")["reason"].startswith("unknown references")


def test_gc_tampered_candidate_is_retained(tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    declared = _sha(PAYLOAD)
    keep = add_artifact(depot, "pkg-a", content=PAYLOAD)
    tampered = add_artifact(depot, "pkg-b", content=b"payloaD", sha256=declared)
    write_manifest(depot, [keep, tampered])

    plan = _plan(depot, catalogue)

    artifact = _artifact(plan, "pkg-b")
    assert artifact["decision"] == "keep"
    assert artifact["reason"].startswith("missing integrity — retained")
    assert artifact["integrity"]["status"] == "checksum_mismatch"
    assert plan["totals"]["eligible_count"] == 0



def test_gc_unreadable_inputs_refuse_every_removal(tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(depot, [add_artifact(depot, "pkg-a"), add_artifact(depot, "pkg-b")])
    receipts = depot / "receipts"
    receipts.mkdir()
    (receipts / "broken.json").write_text("{ not json", encoding="utf-8")

    plan = _plan(depot, catalogue)

    assert plan["totals"]["eligible_count"] == 0
    assert any("receipt is unreadable" in problem for problem in plan["problems"])
    assert plan["refusals"]["unknown_references"] == ["pkg-a", "pkg-b"]
    assert all(item["decision"] == "keep" for item in plan["artifacts"])

    missing_catalogue = build_gc_plan(depot, catalogue_path=tmp_path / "absent.json", now=NOW)
    assert missing_catalogue["catalogue"]["status"] == "not_found"
    assert missing_catalogue["totals"]["eligible_count"] == 0


def test_gc_plan_id_is_stable_and_policy_sensitive(tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(depot, [add_artifact(depot, "pkg-a"), add_artifact(depot, "pkg-b")])

    first = _plan(depot, catalogue)
    second = _plan(depot, catalogue)
    other = _plan(depot, catalogue, retain_days=365)

    assert first["plan_id"] == second["plan_id"]
    assert first["plan_id"].startswith("gc-")
    assert first["plan_id"] != other["plan_id"]


def test_gc_dry_run_never_changes_the_depot(tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(depot, [add_artifact(depot, "pkg-a"), add_artifact(depot, "pkg-b")])
    (depot / "receipts").mkdir()

    def snapshot():
        state = {}
        for path in sorted(depot.rglob("*")):
            stat = path.stat()
            state[path.relative_to(depot).as_posix()] = (stat.st_size, stat.st_mtime_ns, stat.st_ino)
        return state

    before = snapshot()
    plan = _plan(depot, catalogue, verify=True)
    after = snapshot()

    assert plan["totals"]["eligible_count"] == 1
    assert before == after
    assert not (depot / "pins.json").exists()


def test_gc_cli_prints_a_plan_and_has_no_apply(runner, tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(depot, [add_artifact(depot, "pkg-a")])

    from sonic.cli import cli

    result = runner.invoke(
        cli, ["depot", "gc", "--depot", str(depot), "--catalogue", str(catalogue)]
    )
    assert result.exit_code == 0, result.output
    assert "Depot GC dry run" in result.output
    assert "Nothing was removed" in result.output
    assert "read-only" in result.output

    as_json = runner.invoke(
        cli, ["depot", "gc", "--depot", str(depot), "--catalogue", str(catalogue), "--json"]
    )
    assert as_json.exit_code == 0, as_json.output
    plan = json.loads(as_json.output)
    assert plan["read_only"] is True
    assert plan["artifacts"][0]["id"] == "pkg-a"

    apply_attempt = runner.invoke(
        cli, ["depot", "gc", "--depot", str(depot), "--catalogue", str(catalogue), "--apply"]
    )
    assert apply_attempt.exit_code != 0
    assert "reviewed plan id" in apply_attempt.output


def test_gc_expired_duplicate_goes_only_because_its_keeper_remains(tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    old = (NOW - timedelta(days=40)).isoformat()
    write_manifest(
        depot,
        [add_artifact(depot, "pkg-a", added_at=old), add_artifact(depot, "pkg-b", added_at=old)],
    )

    plan = _plan(depot, catalogue, retain_days=30)

    keeper = _artifact(plan, "pkg-a")
    duplicate = _artifact(plan, "pkg-b")
    assert keeper["decision"] == "keep"
    assert keeper["reason"] == (
        "expired — retained (no verified keeper or successor would remain after the plan)"
    )
    assert duplicate["decision"] == "remove"
    assert duplicate["reason"] == "duplicate of pkg-a"
    assert duplicate["requirement"] == "pkg-a"
    assert plan["totals"]["eligible_count"] == 1
    assert plan["totals"]["estimated_reclaimable_bytes"] == len(PAYLOAD)


def test_gc_refuses_self_supersession(tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(depot, [add_artifact(depot, "pkg")])

    plan = _plan(depot, catalogue, supersede=["pkg=pkg@1.0.0"])

    artifact = _artifact(plan, "pkg")
    assert artifact["decision"] == "keep"
    assert artifact["reason"] == "superseded by itself — retained (no distinct successor)"
    assert plan["refusals"]["self_reference"] == ["pkg"]
    assert plan["totals"]["eligible_count"] == 0


def test_gc_refuses_successor_cycles(tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(
        depot,
        [
            add_artifact(depot, "pkg-a", content=b"alpha"),
            add_artifact(depot, "pkg-b", content=b"bravo"),
        ],
    )

    plan = _plan(
        depot,
        catalogue,
        supersede=["pkg-a=pkg-b@1.0.0", "pkg-b=pkg-a@1.0.0"],
    )

    first = _artifact(plan, "pkg-a")
    second = _artifact(plan, "pkg-b")
    assert plan["totals"]["eligible_count"] == 0
    assert first["decision"] == "keep" and second["decision"] == "keep"
    assert first["reason"] == "reference cycle — retained (pkg-a → pkg-b → pkg-a)"
    assert second["reason"] == "reference cycle — retained (pkg-a → pkg-b → pkg-a)"
    assert sorted(plan["refusals"]["reference_cycle"]) == ["pkg-a", "pkg-b"]


def test_gc_chain_never_removes_its_own_successor(tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(
        depot,
        [
            add_artifact(depot, "pkg-a", content=b"alpha"),
            add_artifact(depot, "pkg-b", version="2.0.0", content=b"bravo"),
            add_artifact(depot, "pkg-c", version="3.0.0", content=b"charlie"),
        ],
    )

    plan = _plan(
        depot,
        catalogue,
        supersede=["pkg-a=pkg-b@2.0.0", "pkg-b=pkg-c@3.0.0"],
    )

    assert plan["totals"]["eligible_count"] == 0
    assert _artifact(plan, "pkg-c")["decision"] == "keep"
    assert _artifact(plan, "pkg-a")["reason"] == (
        "required copy pkg-b is also scheduled for removal — retained"
    )
    assert _artifact(plan, "pkg-b")["reason"] == "keeper/successor for pkg-a — retained"


def test_gc_expired_successor_still_allows_the_superseded_removal(tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    old = (NOW - timedelta(days=40)).isoformat()
    write_manifest(
        depot,
        [
            add_artifact(depot, "pkg-a", added_at=old),
            add_artifact(depot, "pkg-b", version="2.0.0", content=b"successor", added_at=old),
        ],
    )

    plan = _plan(depot, catalogue, retain_days=30, supersede=["pkg-a=pkg-b@2.0.0"])

    successor = _artifact(plan, "pkg-b")
    superseded = _artifact(plan, "pkg-a")
    assert successor["decision"] == "keep"
    assert successor["reason"] == (
        "expired — retained (no verified keeper or successor would remain after the plan)"
    )
    assert superseded["decision"] == "remove"
    assert superseded["reason"] == "superseded by pkg-b@2.0.0"
    assert superseded["requirement"] == "pkg-b"
    assert plan["totals"]["eligible_count"] == 1


def test_default_depot_roots_exclude_the_retired_vendor_lane(monkeypatch, tmp_path: Path):
    from sonic.lib import depot as depot_module

    monkeypatch.delenv("SONIC_DEPOT_ROOT", raising=False)
    monkeypatch.setenv("UDOS_HOME", str(tmp_path / "udos"))

    roots = depot_module.get_default_depot_roots()

    assert roots
    assert all("Vendor" not in str(root) for root in roots)
    assert roots[-1] == (tmp_path / "udos" / "sonic" / "depot").resolve()


def test_cli_depot_list_without_an_explicit_root_uses_discovery(runner, monkeypatch, tmp_path: Path):
    from sonic.cli import cli

    monkeypatch.delenv("SONIC_DEPOT_ROOT", raising=False)
    monkeypatch.setenv("UDOS_HOME", str(tmp_path / "udos"))

    result = runner.invoke(cli, ["depot", "list"])

    assert result.exit_code == 0, result.output
    assert "Active Depot Roots" in result.output
    assert "No artifacts registered" in result.output


def _apply(runner, depot: Path, catalogue: Path, plan_id: str):
    from sonic.cli import cli

    return runner.invoke(
        cli,
        [
            "depot",
            "gc",
            "--depot",
            str(depot),
            "--catalogue",
            str(catalogue),
            "--apply",
            "--plan-id",
            plan_id,
        ],
    )


def test_gc_apply_removes_the_duplicate_and_writes_one_receipt(runner, tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(depot, [add_artifact(depot, "pkg-a"), add_artifact(depot, "pkg-b")])
    plan = build_gc_plan(depot, catalogue_path=catalogue, now=NOW)
    assert plan["totals"]["eligible_count"] == 1

    result = _apply(runner, depot, catalogue, plan["plan_id"])

    assert result.exit_code == 0, result.output
    assert not (depot / "pkg-b.tgz").exists()
    assert (depot / "pkg-a.tgz").exists()
    receipts = sorted((depot / "receipts").glob("*.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
    assert receipt["schema"] == "sonic.depot-gc-receipt/1"
    assert receipt["action"] == "artifact_removed"
    assert receipt["plan_id"] == plan["plan_id"]
    assert receipt["artifact"]["id"] == "pkg-b"
    assert receipt["artifact"]["sha256"] == _sha(PAYLOAD)
    assert receipt["reason"] == "duplicate of pkg-a"
    assert receipt["requirement"] == "pkg-a"
    assert receipt["volume"]["used_before_bytes"] > 0
    assert "recovery" in receipt

    after = build_gc_plan(depot, catalogue_path=catalogue, now=NOW)
    assert after["totals"]["eligible_count"] == 0
    assert after["plan_id"] != plan["plan_id"]


def test_gc_apply_refuses_a_plan_id_that_does_not_match(runner, tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(depot, [add_artifact(depot, "pkg-a"), add_artifact(depot, "pkg-b")])

    result = _apply(runner, depot, catalogue, "gc-" + "0" * 64)

    assert result.exit_code != 0
    assert "does not match plan" in result.output
    assert (depot / "pkg-b.tgz").exists()
    assert not (depot / "receipts").exists()


def test_gc_apply_refuses_a_candidate_that_drifted(runner, tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(depot, [add_artifact(depot, "pkg-a"), add_artifact(depot, "pkg-b")])
    plan = build_gc_plan(depot, catalogue_path=catalogue, now=NOW)

    (depot / "pkg-b.tgz").write_bytes(b"tampered")

    result = _apply(runner, depot, catalogue, plan["plan_id"])

    assert result.exit_code != 0
    assert "does not match plan" in result.output
    assert (depot / "pkg-b.tgz").exists()
    assert not (depot / "receipts").exists()


def test_gc_apply_refuses_when_the_keeper_drifted(runner, tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(depot, [add_artifact(depot, "pkg-a"), add_artifact(depot, "pkg-b")])
    plan = build_gc_plan(depot, catalogue_path=catalogue, now=NOW)

    (depot / "pkg-a.tgz").write_bytes(b"tampered")

    result = _apply(runner, depot, catalogue, plan["plan_id"])

    assert result.exit_code != 0
    assert "does not match plan" in result.output
    assert (depot / "pkg-b.tgz").exists()
    assert not (depot / "receipts").exists()



def test_gc_apply_stops_when_an_artifact_drifts_mid_run(runner, tmp_path: Path, monkeypatch):
    from sonic.lib import depot_gc as gc_module

    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(
        depot,
        [
            add_artifact(depot, "pkg-a1", content=b"aaa-payload"),
            add_artifact(depot, "pkg-a2", content=b"aaa-payload"),
            add_artifact(depot, "pkg-z1", content=b"zzz-payload"),
            add_artifact(depot, "pkg-z2", content=b"zzz-payload"),
        ],
    )
    plan = build_gc_plan(depot, catalogue_path=catalogue, now=NOW)
    assert plan["totals"]["eligible_count"] == 2

    real_unlink = gc_module.os.unlink
    calls = []

    def drifting_unlink(path):
        if Path(path).suffix == ".tgz":
            calls.append(Path(path).name)
            if len(calls) == 1:
                (depot / "pkg-z2.tgz").write_bytes(b"zzz-payloaX")
        real_unlink(path)

    monkeypatch.setattr(gc_module.os, "unlink", drifting_unlink)

    result = _apply(runner, depot, catalogue, plan["plan_id"])

    assert result.exit_code == 1
    assert "Stopped at pkg-z2" in result.output
    assert calls == ["pkg-a2.tgz"]
    assert not (depot / "pkg-a2.tgz").exists()
    assert (depot / "pkg-z2.tgz").exists()
    assert (depot / "pkg-z1.tgz").exists()
    assert len(list((depot / "receipts").glob("*.json"))) == 1


def test_gc_apply_reports_no_removals_when_the_plan_has_none(runner, tmp_path: Path):
    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(depot, [add_artifact(depot, "pkg-a")])
    plan = build_gc_plan(depot, catalogue_path=catalogue, now=NOW)
    assert plan["totals"]["eligible_count"] == 0

    result = _apply(runner, depot, catalogue, plan["plan_id"])

    assert result.exit_code == 0, result.output
    assert "contains no removals" in result.output
    assert (depot / "pkg-a.tgz").exists()
    assert not (depot / "receipts").exists()


def test_gc_apply_revalidates_each_keeper_before_its_unlink(runner, tmp_path: Path, monkeypatch):
    from sonic.lib import depot_gc as gc_module

    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(
        depot,
        [
            add_artifact(depot, "pkg-a1", content=b"aaa-payload"),
            add_artifact(depot, "pkg-a2", content=b"aaa-payload"),
            add_artifact(depot, "pkg-z1", content=b"zzz-payload"),
            add_artifact(depot, "pkg-z2", content=b"zzz-payload"),
        ],
    )
    plan = build_gc_plan(depot, catalogue_path=catalogue, now=NOW)
    assert plan["totals"]["eligible_count"] == 2
    assert _artifact(plan, "pkg-z2")["requirement"] == "pkg-z1"

    real_unlink = gc_module.os.unlink

    def drifting_unlink(path):
        if Path(path).suffix == ".tgz" and Path(path).name == "pkg-a2.tgz":
            # The keeper for the *next* candidate changes after the first removal.
            (depot / "pkg-z1.tgz").write_bytes(b"zzz-payloaX")
        real_unlink(path)

    monkeypatch.setattr(gc_module.os, "unlink", drifting_unlink)

    result = _apply(runner, depot, catalogue, plan["plan_id"])

    assert result.exit_code == 1
    assert "keeper or successor pkg-z1 drifted" in result.output
    assert not (depot / "pkg-a2.tgz").exists()
    assert (depot / "pkg-z2.tgz").exists()
    assert (depot / "pkg-z1.tgz").read_bytes() == b"zzz-payloaX"
    assert len(list((depot / "receipts").glob("*.json"))) == 1


def test_gc_apply_keeps_a_pending_receipt_when_finalisation_fails(
    runner, tmp_path: Path, monkeypatch
):
    from sonic.lib import depot_gc as gc_module

    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(depot, [add_artifact(depot, "pkg-a"), add_artifact(depot, "pkg-b")])
    plan = build_gc_plan(depot, catalogue_path=catalogue, now=NOW)

    real_write = gc_module._write_receipt

    def failing_write(directory, name, payload):
        if payload.get("state") == "committed":
            raise OSError(28, "No space left on device")
        return real_write(directory, name, payload)

    monkeypatch.setattr(gc_module, "_write_receipt", failing_write)

    result = _apply(runner, depot, catalogue, plan["plan_id"])

    assert result.exit_code == 1
    assert "receipt finalisation failed" in result.output
    assert not (depot / "pkg-b.tgz").exists()
    assert not list((depot / "receipts").glob("*.json"))
    staged = list((depot / "receipts" / "pending").glob("*.json"))
    assert len(staged) == 1
    record = json.loads(staged[0].read_text(encoding="utf-8"))
    assert record["state"] == "pending"
    assert record["artifact"]["id"] == "pkg-b"
    assert record["artifact"]["sha256"] == _sha(PAYLOAD)
    assert record["removed_at"] is None
    assert record["volume"] is None
    assert "Staged before unlink" in record["note"]

    after = build_gc_plan(depot, catalogue_path=catalogue, now=NOW)
    assert after["receipts"]["pending"] == 1
    assert after["totals"]["eligible_count"] == 0


def test_gc_apply_keeps_a_pending_receipt_when_the_unlink_is_interrupted(
    runner, tmp_path: Path, monkeypatch
):
    from sonic.lib import depot_gc as gc_module

    depot = make_depot(tmp_path)
    catalogue = write_catalogue(tmp_path / "catalogue.json")
    write_manifest(depot, [add_artifact(depot, "pkg-a"), add_artifact(depot, "pkg-b")])
    plan = build_gc_plan(depot, catalogue_path=catalogue, now=NOW)

    real_unlink = gc_module.os.unlink

    def interrupted_unlink(path):
        if Path(path).suffix == ".tgz":
            raise OSError(4, "Interrupted system call")
        real_unlink(path)

    monkeypatch.setattr(gc_module.os, "unlink", interrupted_unlink)

    result = _apply(runner, depot, catalogue, plan["plan_id"])

    assert result.exit_code == 1
    assert "unlink failed" in result.output
    assert (depot / "pkg-b.tgz").exists()
    assert not list((depot / "receipts").glob("*.json"))
    staged = list((depot / "receipts" / "pending").glob("*.json"))
    assert len(staged) == 1
    record = json.loads(staged[0].read_text(encoding="utf-8"))
    assert record["state"] == "pending"
    assert record["artifact"]["id"] == "pkg-b"
    assert record["removed_at"] is None

    after = build_gc_plan(depot, catalogue_path=catalogue, now=NOW)
    assert after["receipts"]["pending"] == 1
    assert _artifact(after, "pkg-b")["decision"] == "keep"
    assert after["totals"]["eligible_count"] == 0
