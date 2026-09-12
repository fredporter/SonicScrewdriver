# Sonic-Screwdriver

Hardware revival, device knowledge and a standalone entry point into uDOS.

**Current status: revival baseline, 0.1.0.dev0.** The CLI exposes diagnostics, explicit state intake and offline library lookup.
The old USB, flashing, Mint, security, mesh and game command prototypes were
removed because they were unimplemented or outside the confirmed product scope.
No disk-writing or flashing capability is currently advertised.

The direction is Python/Linux, a Sonic-owned Ventoy-based boot experience,
Classic Modern Mint, Beacon offline portals, and guide/crypt/time-capsule devices.
Sonic installs and consumes uCore/uCode/uKnowledge capabilities as needed;
it does not duplicate their platform services.

## Start here

- [Gemini implementation handover](docs/GEMINI-HANDOVER.md)
- [Scaffold and implementation contracts](docs/IMPLEMENTATION-CONTRACTS.md)

- [Revival plan](docs/REVIVAL-PLAN-2026-09.md)
- [Sprint 1: reproducible standalone foundation](docs/SPRINT-01-2026-09.md)
- [Existing-code and upstream reuse decisions](docs/REUSE-AND-UPSTREAM-2026-09.md)
- [Historical reconciliation](docs/HISTORICAL-RECONCILIATION-2026-09.md)
- [Cleanup record](docs/CLEANUP-2026-09.json)

## Development

```sh
cd cli
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/sonic --help
.venv/bin/sonic diagnostics health
.venv/bin/python -m pytest tests -q
```

Mutable state lives under `UDOS_HOME` (default `~/Code/.udos`), with Sonic's
journal in `sonic/spool`. No automatic migration or deletion of old user state
is performed. Device YAML retains unverified historical claims for review;
mutating package data is not an approved runtime path.

The old release workflow is removed. Source checkout/package tests are not a
production release or hardware support claim. No Go toolchain is required.

### Redevelopment commands

`sonic config paths` prints resolved paths without creating state.
`sonic config import-legacy /absolute/old-state` previews byte-preserving intake;
add `--apply` to copy into `$UDOS_HOME/sonic/imports/legacy`. Originals are retained
and existing destinations are refused. Intake does not activate old configuration.
Use trusted local directories that are not changing during import.

`sonic library search archer --json` searches the offline model catalog.
`sonic library show tp-link-archer-c7` shows provenance and quarantined legacy
claims. These records do not establish physical-device or firmware compatibility.
