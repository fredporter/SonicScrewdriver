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

Rule: **an artifact is provenance and a verification gate; the offline unit is the verified installed tree.** Ship that as a Package (`.spkg`, per-file SHA) or a capsule payload, and keep the artifact as the thing the gate checks.

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

