# Gemini implementation handover — SonicScrewdriver

Prepared 12 September 2026. User has authorized redevelopment and cleanup.
Pre-work is complete as a handoff; Sprint 1 implementation and hardware
qualification are not complete. Begin with the read-only foundation, not disk
writing. This file is a repository handover, not a message sent to a service.

## Mission and decisions

Deliver a standalone Python/Linux CLI-first hardware revival toolkit and
installer/distribution channel. uCode revives software; Sonic revives hardware.
Retain Beacon, offline device reference, guide/crypt/tomb capsules, a Sonic-owned
Ventoy derivative, base-linux and Classic Modern Mint theory. No Go rewrite.
No generic gateway/secrets/automation platform. Reuse the ecosystem owners in
[implementation contracts](IMPLEMENTATION-CONTRACTS.md).

The user approved Steam gaming plus media for HomeNest, a separate product
following Sonic. HA/Matter has its own integration repository/card/API/commands.
Do not merge either into Sonic or turn HomeNest back into uCode3.

## Read in this order

1. Workspace `../AGENTS.md` (relative to repository root) and any newer local instructions.
2. This handover and [implementation contracts](IMPLEMENTATION-CONTRACTS.md).
3. [Revival plan](REVIVAL-PLAN-2026-09.md): full product and acceptance scope.
4. [Sprint 1](SPRINT-01-2026-09.md): historical progress and outstanding gates.
5. [Reuse/upstream decisions](REUSE-AND-UPSTREAM-2026-09.md).
6. [Historical reconciliation](HISTORICAL-RECONCILIATION-2026-09.md) only when resolving provenance/backlog questions.

## Current executable baseline

Python >=3.11, package `sonic-screwdriver`, command `sonic`, version `0.1.0.dev0`.
Build metadata in `cli/setup.py` and `cli/pyproject.toml`; CI builds a wheel and
runs copied tests outside the checkout on Ubuntu. CI has not been observed
running during this handover; local source tests are not Linux hardware evidence.

- `diagnostics health`, `diagnostics summary`: local journal/CLI diagnostics only.
- `config paths`: read-only state path output.
- `config import-legacy SOURCE`: preview; `--apply` copies into isolated intake.
- `library search QUERY --json`, `library show MODEL_ID`: offline model lookup.
- 21 model seeds: legacy claims quarantined, provenance hashes, flash eligibility false.
- No scanner command, real installation, flash provider, ISO, active uihub adapter,
  production release/channel, Beacon service or crypt implementation exists.

The prior scanner and its unused database facade were removed because no active
command consumed them and they lacked provider qualification. Recovery text and
hashes are in [handover cleanup record](CLEANUP-HANDOVER-2026-09.json). Do not
restore them wholesale. Earlier 56-file cleanup is separately recorded in
[CLEANUP-2026-09.json](CLEANUP-2026-09.json), with historical provenance inventory.

## First implementation sequence

1. Establish installed-wheel baseline on Linux; verify imports point outside
   source, seeds load, CLI works offline, and all tests pass.
2. Harden instance/driver schemas and implement a real read-only Linux provider
   plus scanner/doctor command using the contracts. Add sanitized parser and
   failure fixtures. Return accurate partial/unsupported outcomes.
3. Replace config import's non-atomic intake with an explicit staged migration
   only when an actual legacy schema activation is needed. Preserve originals;
   implement receipts/recovery before promising resumable migration.
4. Record HomeNest/uCore contract reuse mapping and uKnowledge/GridCore content
   mapping before introducing shared execution or UI infrastructure.
5. Complete the pinned Ventoy Linux build/VM boot spike; document blockers and
   chosen downstream patch boundary. Never mutate Vendor RAW sources.
6. Only then start fake-provider plan/apply tests, followed by qualified removable
   media operations. HomeNest's independent sprint follows the Sonic handoff.

Sprint completion is the clean-Linux offline inventory/library journey plus
reuse/build decisions, not completion of every product stage. See the revival
plan for later operation, base-linux/Mint, uihub, vault and capsule milestones.

## Known gaps and traps

- Legacy model specs can be wrong by orders of magnitude. No verified capacities,
  firmware eligibility or compatibility may be inferred from `legacy_claims`.
- Instance timestamps/driver IDs currently have minimal validation only.
- Intake rejects existing destinations and preserves sources but is not atomic;
  failure can leave partial copies. Symlink checks are not a hostile concurrent
  filesystem defense. Use trusted, quiescent directories until hardened.
- Journal reads load the entire file; add bounded retention/read behavior and
  concurrent append policy before treating it as an operation/event backbone.
- Diagnostics health writes events; it is not a read-only hardware doctor.
- Library data currently ships with the package; no edition signature/update
  implementation exists. No free-form script execution from catalog records.
- No reference hardware or Linux VM is provisioned by this pre-work. Choose a
  disposable x86-64 UEFI test environment first; record actual distro/kernel,
  firmware/GPU/storage and tool versions. Keep BIOS/ARM/Secure Boot/Mac writes
  as separate qualification lanes.
- Signing custody/channel publication and exact base-linux packaging must be
  resolved before release, not guessed into credential or host configuration.

## Verification and checkout handling

From repo root:

```sh
PYTHONPATH=cli python3 -m pytest -p no:cacheprovider cli/tests -q
cd cli
python3 -m build
```

Install the wheel into a disposable environment, copy tests outside the source
checkout and rerun them there. Run uCore `scripts/check_home_path_policy.py` for
path changes and Vendor `00-INDEX/vendor_hygiene_check.py` after upstream intake.
Use the existing CI for Linux validation; do not claim remote runs without logs.

This repository contains accumulated uncommitted authorized cleanup and new
source. Inspect `git status`, do not reset it. Many new `cli/sonic` files were
historically ignored and are now untracked: include them in any reviewed commit.
No commit, push or external publication is performed by this handover. Temporary
files under /private/tmp are not durable provenance or release artifacts.

## Gemini start prompt

Implement the next Sonic read-only foundation milestone described above. Inspect
current instructions/status, preserve the approved cleanup, verify the installed
package baseline, harden the instance/driver contracts, then implement and test
Linux inventory with truthful missing-tool, timeout, parse and ambiguity results.
Keep writes and external services disabled. Update this handover with exact
changes, test commands/results, limitations and the next unmet acceptance gate.

## Final pre-work verification — 12 September 2026

- Source suite: 31 passed, using `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=cli python3 -m pytest -p no:cacheprovider cli/tests -q`.
- Git whitespace check, JSON inventory parsing and new documentation links pass.
- uCore home-path policy passes.
- Fresh artifact build was not run: the current Python environment lacks `build`,
  and the earlier temporary build environment no longer exists. Install declared
  build tooling in a disposable environment and rerun installed-wheel tests as
  the first implementation gate. Earlier wheel results do not validate this cleanup.
- No Linux hardware, VM boot, physical writes or live integration tested.

The pre-work/handover is complete; the implementation gates above remain open.

## Gemini Implementation Milestone 1 — Read-Only Discovery Foundation (12 September 2026)

- Hardened `catalog.py` contracts:
  - `DeviceInstance` and `DriverRecord` validate timezone-aware ISO-8601 observation times, ID grammar, uniqueness of hardware IDs, and reject empty IDs.
  - Added `EvidenceRecord` and `review_status` ensuring unverified catalog seeds and observed instances never authorize physical device writes.
- Implemented read-only discovery provider interface `sonic.providers.base`:
  - `BaseProvider`, `ProbeResult`, `NormalizedDevice`, `ScanReport`, `ProbeStatus`, `ScanStatus`.
- Implemented `LinuxProvider` (`sonic.providers.linux`):
  - Fixed argument vectors (no shell, no sudo, no writes, per-probe 5s timeout):
    - `lsusb`
    - `lspci -nnmm`
    - `lsblk -J -b -o NAME,SIZE,TYPE,MOUNTPOINT,MODEL,SERIAL,TRAN`
  - Sanitizes block device serials (protected private instance data).
  - Truthful non-Linux platform reporting: macOS/Darwin returns explicit `unsupported` status with non-zero exit; never silent fallback to heuristics.
- Implemented `FixtureProvider` (`sonic.providers.fixture`) and checked-in deterministic fixtures in `cli/tests/fixtures/`:
  - `clean_linux_pc.json`, `missing_tools.json`, `parse_error.json`, `timeout.json`, `ambiguous_models.json`, `zero_devices.json`.
- Implemented CLI commands in `sonic.commands.scan`:
  - `sonic scan [--json] [--fixture PATH]`
  - `sonic doctor [--json] [--fixture PATH]`
  - Exit code 0 on complete `ok`, exit code 1 on partial/unsupported/failed, exit code 2 on invalid invocation. Clean JSON output without ANSI codes.
- Test suite expanded to 41 passing tests (`cli/tests/test_scan.py` added 10 comprehensive tests covering all failure/unsupported/fixture cases).
- uCore home-path policy verified clean.
- Next unmet gate: Staged migration with receipts/recovery before physical removable media operations.

