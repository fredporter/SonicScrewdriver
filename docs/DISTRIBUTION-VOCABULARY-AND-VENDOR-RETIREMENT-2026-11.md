# Distribution Vocabulary, Vendor Retirement and the Update Gate

**Status:** Proposed (supersedes the loose "pod" usage)
**Date:** 2026-11-24
**Owners:** SonicScrewdriver (transport, depot, capsules) · uCore (storage policy, installers) · uCode/GridCore (library UI and runtime capsules)

## 1. One vocabulary

The ecosystem already had the right words. Use them, and stop inventing new ones.

| Term | Owner | Meaning | Never call it |
| :--- | :--- | :--- | :--- |
| **Catalogue** | Sonic | Metadata registry: ids, versions, provenance, licence, SHA-256, status. No payloads. | "Vendor folder", "index of stuff" |
| **Artifact** | Sonic/Depot | A retained file under the depot root, verified against a recorded hash. | "blob", "download" |
| **Capsule** | Sonic + uCode | A hash-manifested bundle of a directory or payload (`.capsule`), immutable once sealed. Distribution capsule ≠ runtime capsule, so qualify when ambiguous. | "pod" |
| **Runtime Capsule** | uCode/GridCore | The launchable software unit behind `CAPSULE.LIST`/`CAPSULE.RUN` (NetHack, Repton…). | "Capsule Pod" |
| **Edition** | uCode | One exact build of a Title: treatment (`authentic`/`enhanced`/`adapted`), media policy, capsules. | "version" when you mean the media set |
| **Title** | uCode | A Software Library entry that owns Editions. | "app", "program" |
| **Package** (`.spkg`) | Sonic | Installable dependency payload for one or more consumers, with per-file SHA-256 and consumer tracking. | "installer" |
| **Depot** | Sonic | The retention boundary: the only place retained delivery artifacts live, with GC and receipts. | "cache", "store" |
| **Tomb** | Sonic | Sealed, read-only archive of a capsule or dissolved dispatch. | "trash", "backup" |
| **Activity store** | uCore | The SQLite feed projection at `$UDOS_HOME/pods/activity.db`. Path stays for compatibility; the term is *store*, not pod. | "pod" |
| **Device library** | Sonic | `sonic library` = device models only. | "library" unqualified |
| **Software Library** | uCode | The Title→Edition→Capsule catalogue defined in `docs/SOFTWARE_LIBRARY_CAPSULE_SPEC.md`. | "library" unqualified |

**Banned word: "pod".** It currently means three unrelated things (Activity store, runtime capsules in the uCode manual, and an unnamed portable bundle). Portable delivery sets are **capsules**; frozen sets are **tombs**; their home is the **Depot**.

Status vocabulary is the Software Library's: `research → configured → verified → enhanced → release`. Vendor's parallel ladder (RAW/SCANNED/STUDIED/TESTED/INTEGRATED/RECOMMENDED/ARCHIVED) is retired.

## 2. Retiring `~/Code/Vendor`

Vendor is not a store and not a repository. It is a directory of upstream clones plus a manifest, with a promotion ladder that duplicates the Software Library status and a "serves everything" behaviour that produced the depot bug. It must go.

| Vendor lane | What actually matters | Destination |
| :--- | :--- | :--- |
| `01-RAW/<repo>` | upstream URL + exact commit | Catalogue record (`provenance.source: upstream`, `resolved_ref`); clone deleted (reproducible) |
| `01-RAW/*.zip` (fonts, bedstead, bbclinux) | the bytes themselves | Depot artifact, if still needed by a consumer; otherwise delete |
| `02-STUDIED` / `03-INTEGRATED` | adopted code | the owning Git repository (already forked/imported) |
| `VENDOR_MANIFEST.yaml`, `00-INDEX/*.json` | licence, attribution, decision history | Catalogue export, retained once, hashed |
| `04-RECOMMENDED`, `99-ARCHIVE` | nothing live | drop |

Sequence (one reviewed change, not a sweep):

1. Freeze intake: no new clone into Vendor; new sources enter through the catalogue.
2. Export manifest + index JSON to a single catalogue snapshot and store it as a retained Depot artifact (hashed, receipts recorded).
3. For each RAW clone: confirm no local-only commits, record `upstream_url` + `resolved_ref`, delete.
4. For each STUDIED/INTEGRATED entry: confirm the adopted code exists in its owning repo; promote first if not.
5. Update the policy text that still names Vendor: workspace `AGENTS.md` ("shared caches … `Code/Vendor/01-RAW`", "Vendor is the upstream source catalogue"), `Vendor/README.md`, `vendor_hygiene_check.py`, and the `Vendor/01-RAW` root in `sonic.lib.depot.get_default_depot_roots()`.
6. Remove the directory. Provenance survives in the catalogue; payloads survive only where a consumer needs them.

Licence and attribution obligations are satisfied by the catalogue record (`upstream_url`, `license`, `resolved_ref`), not by keeping an unverified copy on disk.

**Executed 2026-11-24.** `~/Code/Vendor` (745,613,366 bytes across 44,972 files) moved to the macOS Trash. `VENDOR_MANIFEST.yaml` (`sha256 eb847cc7…0fd2`) and the decision history are captured in `Depot/receipts/vendor-retirement-2026-11-24.json`. Retained in the Depot instead of deleted: `fonts/` (13 MB), `fonts-retro/` (8.9 MB), `bedstead-3.261.zip` (1.6 MB) and `tools/bbclinux.zip` (22 MB). The uCode font manifest still names `~/Code/Vendor/fonts/retro` — a path that was already stale before this change — and should be repointed at the Depot in a separate reviewed edit.

## 3. Offline installs: what the artifact can and cannot do

Measured on 2026-11-24 for NanoCoder 1.30.0:

- the pinned tarball is 1,349,964 bytes, SHA-256 `ba9323…dccc`, identical to `vendor/lock.yaml`;
- a clean install resolves **351 packages**;
- with a cold npm cache, `npm install --offline` fails (`ENOTCACHED` on `strip-json-comments@5.1.0`) — the tarball alone is **not** an offline installer;
- with a warm cache the same offline install succeeds, and the installer proves the installed package is byte-identical to the archive before applying reviewed patches.

Rule: **an artifact is provenance and a verification gate; the offline unit is the verified tarball plus a pinned dependency bundle.** The installer now installs from the retained tarball path rather than the registry name, and accepts `--deps <bundle|dir>`; `--build-deps` produces the bundle from one clean online install.

Measured bundle: the resolved dependency cache is 199 MB and compresses to a 79,618,918-byte `tar.gz` (`sha256 d7c9223d…71ff`). Trust chain:

1. **The pin is authoritative.** `EXPECTED_DEPS_SHA256` and `EXPECTED_DEPS_BYTES` are reviewed constants in the installer — the same source that already pins the package tarball.
2. **The Layer 0 catalogue must agree.** The installer reads the `nanocoder-npm-cache` digest from `distribution_catalogue.json`; a disagreement aborts the install.
3. **A sidecar may only confirm.** `<bundle>.sha256` is still written and checked, but it is compared *against* the pin, so replacing the bundle and its sidecar together changes nothing.
4. **The dependency set is versioned.** `vendor/nanocoder-1.30.0-deps-lock.json` is committed, and `--build-deps` installs with `npm ci`; an existing bundle is not overwritten without `--rebuild-deps`, and a missing lock is an error rather than an invitation to re-resolve.

Proofs: a one-byte change to the bundle aborts before extraction; a forged bundle **plus a matching replacement sidecar** is rejected with `Dependency bundle does not match the pinned release digest`, exit 1, nothing extracted; a fresh `UDOS_HOME` with an empty npm cache completes the offline install (351 packages, both patches, version and byte-identity asserted).

Caveat worth knowing: npm cache keys include the registry URL, so the bundle must be built against the same registry used at install time. Building from `registry.npmjs.org` and installing with a different `npm_config_registry` fails with `ENOTCACHED` — that is a cache-key mismatch, not corruption. The bundle ships in the Depot as artifact `nanocoder-npm-cache` and is declared in the catalogue seed beside the tarball.

## 4. The update gate and manager

One gate, owned by Sonic, used by every consumer (uCore installers, uCode runtime capsules, knowledge editions).

```
discover → verify → stage → approve → activate → rollback
```

Invariants:

1. No activation without a verified successor artifact (hash match at the destination).
2. No silent downgrade; a lower version needs an explicit `--allow-downgrade` and a receipt.
3. The previous capsule/tree survives until the new one verifies, then is retired (not deleted) for one cycle.
4. Activation never fetches. Fetch and verify belong to `stage`.
5. A consumer still pinned to an older edition blocks removal, not upgrade.
6. Every transition writes an `update-receipts/<utc>.json`: id, from, to, sha, actor, reason, size delta.

Proposed surface (not yet implemented):

```sh
sonic update check [--json]              # pins vs installed consumers
sonic update stage <id>@<version>        # fetch, verify hash, place in depot
sonic update activate <id>@<version> --approve
sonic update rollback <id>
sonic update receipts [--json]
```

`sonic depot gc` and the gate share one rule: retention may delete an expired or superseded artifact, never the only verified copy and never anything a receipt or consumer still references.

## 5. GridCore: teletext library pages and SONIC terminal commands

Landed in `~/Code/uCode/packages/gridcore`:

- `src/teletext/library-catalogue.ts` — `LibrarySnapshot` (`ucode-library/1` + depot summary), `formatBytes`, `countByStatus`.
- `src/teletext/page-provider.ts` — page **600** (library index: depot root, retained/reclaimable, titles with status and page numbers) and **601–609** (title detail: provenance, editions, treatment/status/media policy, capsule availability, abbreviated SHA). Pages 100/199/888 advertise 600.
- `src/terminal/sonic-commands.ts` — `createSonicCommandHandler(bridge)`: `SONIC DEPOT STATUS`, `SONIC CAPSULE LIST`, `SONIC CAPSULE VERIFY <id>`, `SONIC HELP`. Identifier allowlist `^[a-z0-9][a-z0-9._-]{0,63}$`, no paths, no shell, and `[]` for non-SONIC input so it composes with another handler.

Producer contract still required: `sonic catalogue snapshot --json` emitting `LibrarySnapshot`, and a host bridge implementing `SonicBridge` (`depotStatus`, `listCapsules`, `verifyCapsule`). Until that exists the pages render an honest empty state and the terminal reports the bridge as unavailable; neither invents data.

GridCore notes are read-only. Curation (register, prune, approve an update) happens through the gate in a Terminal session, never from a teletext page.

## 6. Evidence

- `packages/gridcore`: 196 tests passing across 28 files, including `library-pages.test.ts` and `sonic-commands.test.ts`.
- `scripts/install_nanocoder.sh` (uCore): artifact-first install, byte-identity check, patch assertions, uninstall/replace; 18 backend tests passing including the pin-drift contract test.
- Sonic catalogue: `cli/sonic/lib/catalogue.py`, `cli/sonic/commands/catalogue.py`, `cli/tests/test_catalogue.py` (10 tests) — base seed loads from `~/Public/global-knowledge/datasets/distribution_catalogue.json`, snapshot merges Depot retention, missing file or hash mismatch never reports `verified`.
- Explicit depot roots: `depot list|register|verify --depot <root>` with a CLI test proving no duplicate copy is made when the artifact already lives in the depot.
- Depot contents after the first registration: `nanocollective-nanocoder-1.30.0.tgz` (hardlinked to the installer cache, one inode), 46 MB of retained assets, two receipts. `sonic depot verify nanocoder --depot ~/Code/Depot` → `verified`.
- Storage before/after: `.udos` 124 GiB → 52 GiB; Colima runtime 77 GiB → 4.4 GiB; host free 91 GiB → 164 GiB. Vendor hygiene baseline before retirement: 28 manifest entries, 20 RAW repos/ZIPs, `PASSED`.

## 7. Decisions recorded

- Decided: schema and CLI live in Sonic; the distributable base catalogue is a Layer 0 seed in `global-knowledge/datasets/`; the local instance (retention, verification, receipts) lives in the Depot and is never committed.
- Open: whether a portable capsule set needs its own extension (`.capsule-set`) or is a directory of capsules plus one manifest. Recommendation: directory + manifest, no new extension.
- Open: encryption at rest for removable media — host-managed volume (APFS/LUKS) recorded in the manifest; Sonic adds no crypto.

## 8. Next: retention GC (not yet implemented)

Prerequisite, now closed: `depot register` no longer has an implicit destination. It requires `--depot` or `SONIC_DEPOT_ROOT`, so nothing can be written to an unintended root before deletion logic exists.

`sonic depot gc` starts in **dry-run by default** and must report, per artifact:

- id, kind, version, path and byte size;
- the eligibility reason (`expired`, `superseded by <id>@<version>`, `duplicate of <id>`, `pinned — retained`);
- last verified time, and every consumer or receipt that still references it;
- the totals, kept deliberately separate:
  - **eligible artifact bytes** — the sum of the sizes of the artifacts the plan proposes to remove, which is what a human reads as "space";
  - **estimated space reclaimed** — `0` for an artifact whose data is still reachable through another hardlink (for example the Depot copy while the installer-cache link still exists), because unlinking one name frees no file data;
  - **measured space reclaimed** — on APFS, shared blocks and clone groups make arithmetic unreliable, so the reported figure comes from a before-and-after measurement of the volume, never from summing `st_size`.

`--apply` requires the plan identifier printed by the dry run, re-verifies each artifact immediately before unlinking, refuses when a candidate is the only verified copy, pinned, or referenced, and writes one receipt per removal. No blanket prune, no implicit root, no silent deletion.

### 8.1 Read-only dry run (implemented 2026-11-24)

`sonic depot gc` is dry-run only. It writes nothing, unlinks nothing and has no
`--apply` flag yet: passing one is a usage error, so a half-built apply cannot
be reached by habit.

```sh
cd ~/Code/SonicScrewdriver/cli
python3 -m sonic.cli depot gc --depot ~/Code/Depot
python3 -m sonic.cli depot gc --depot ~/Code/Depot --json
python3 -m sonic.cli depot gc --depot ~/Code/Depot --retain-days 90 --verify
python3 -m sonic.cli depot gc --depot ~/Code/Depot --supersede old-id=new-id@1.4.0
```

The plan document (`sonic.depot-gc-plan/1`) carries a stable `plan_id`: the
SHA-256 of the root, policy, per-artifact identity and decision, and the byte
totals. Identical inventory and policy produce an identical id; `generated_at`
and the volume figures are deliberately outside the digest so a re-run can be
compared with the reviewed plan.

Per artifact the plan reports id, kind, version, path, bytes, the recorded
digest, `last_verified_at` (from evidence, or the plan's own hash time), every
pin with its source, every receipt that still references the artifact, the
hardlink device/inode/link count, and one reason string. Reasons are
`expired`, `superseded by <id>@<version>`, `duplicate of <id>`,
`pinned — retained`, `referenced by a receipt — retained`,
`missing integrity — retained (<detail>)` and
`unknown references — retained (...)`.

Refusal rules, in order:

1. **Unknown references.** An unreadable manifest, receipt, `pins.json` or base
   catalogue, an ambiguous manifest key/id pair, or a malformed
   `--supersede` means the plan cannot prove what still needs the payload, so
   it proposes no removals at all. A missing catalogue counts here: the pins
   live in Layer 0, so "not found" is not "nothing is pinned".
2. **Pins.** Any artifact named by the Layer 0 catalogue (by id, digest or file
   name) or by the optional `<depot>/pins.json` is pinned.
3. **Receipts.** Any receipt under `<depot>/receipts/**.json` that mentions the
   artifact's id, `id@version`, relative path, file name, basename or digest
   blocks removal. Receipt schemas vary, so matching is by value, not by a
   fixed field list.
4. **Integrity and containment.** A manifest path must be relative, free of
   `..`, not a symlink and inside the resolved depot root. Missing files,
   non-regular files, missing digests and size mismatches are refused; every
   candidate and every copy that would keep its content is hashed at plan time,
   so a tampered candidate is reported, not removed.
5. **Sole verified copy.** A duplicate is only eligible while the copy that
   would remain hashes clean. If it does not, the candidate is retained as the
   only verified copy. A superseded artifact waits until its successor
   verifies.

Byte accounting keeps the three figures apart, as §8 requires:

- `artifact_bytes` — the sum of the artifacts' recorded sizes;
- `unique_inode_bytes` — the same sum with hardlinks counted once per inode;
- `eligible_artifact_bytes` — the unique-inode bytes of the artifacts the plan
  proposes to remove;
- `estimated_reclaimable_bytes` — zero for any eligible inode whose link count
  is still above one;
- `volume.used_bytes` — measured before the plan; `after_used_bytes` stays
  `null`, because APFS shared blocks and clone groups make the delta
  unpredictable until apply measures it.

Unregistered files, other application stores, Docker volumes and the Trash are
outside the inventory: the plan reads the manifest and nothing else.

Evidence: `cli/tests/test_depot_gc.py` (16 tests, disposable depots) covers the
explicit-root refusal, flat and nested manifest paths, path containment,
missing files, size mismatches, tampering, catalogue and local pins, receipt
references in nested receipt directories, unreadable inputs, duplicates,
hardlinks, expiry, supersession, plan-id stability and immutability of the
depot across a verified run. The live depot plan reports both NanoCoder
artifacts as `pinned — retained` with `link_count = 2`, eligible bytes `0` and
estimated reclaimable `0`, which is the honest answer.

Remaining before apply: quote the reviewed plan id, revalidate bytes, digests,
pins, references and containment immediately before each unlink, tolerate
concurrent changes, write one receipt per removal, and measure the volume
before and after to report the real delta.
