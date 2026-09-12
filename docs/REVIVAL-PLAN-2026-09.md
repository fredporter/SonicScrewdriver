# SonicScrewdriver revival plan

Implementation baseline · consolidated 12 September 2026

## Confirmed decisions and current baseline

Confirmed by the user on 10 September 2026: Python/Linux is the baseline; no Go rewrite. Sonic is a standalone hardware tool and entry point into uDOS, installing and leveraging uCore/uCode rather than recreating their gateway, secrets or automation capabilities. Beacon is an accepted role. Classic Modern Mint retains its design theory, but its failed scripts are removed and rebuilt as a reversible profile. A Sonic-owned Ventoy derivative is the preferred boot-menu direction, with upstream study and a bounded fork/build gate.

The authorized cleanup removed 56 obsolete files, including old specifications, unsafe/unsupported command shells, C bootloader stubs, failed Mint scripts, recovery scripts, demo UI, stale MCP manifest and the ignored Go binary. The current CLI exposes diagnostics, explicit legacy-state intake and offline library lookup. Unused scanner/database prototypes were removed at handover. The 21 catalog models retain unverified historical claims; no physical-device or flash compatibility is established.

Start implementation with [the Gemini handover](GEMINI-HANDOVER.md) and [implementation contracts](IMPLEMENTATION-CONTRACTS.md). Forward work is defined by this plan, [the historical reconciliation](HISTORICAL-RECONCILIATION-2026-09.md), [reuse/upstream decisions](REUSE-AND-UPSTREAM-2026-09.md), and [Sprint 1](SPRINT-01-2026-09.md). [Cleanup hashes](CLEANUP-2026-09.json) and [source provenance](HISTORICAL-SOURCE-INVENTORY-2026-09.json) preserve the audit trail. Older references below describe the pre-cleanup assessment and are recoverable from Git history or the recorded temporary snapshot.

## Product direction

Sonic becomes a standalone, offline-capable device manager, installer and distribution channel. **uCode revives software; Sonic-Screwdriver revives and repurposes hardware.** Its Python engine powers a scriptable CLI, terminal menus, and an optional uihub surface, including operation from macOS through uDOS. A dedicated Global Devices vault holds technical knowledge and links it to versioned, executable installation and recovery recipes. A base-linux module installs the same released toolkit into a minimal Linux environment. Classic Modern Mint is the flagship desktop revival profile.

“Universal” means a consistent interface and extensible device/provider contracts. It does not mean every device can be flashed: support is declared per hardware revision, operation, host platform and tested recipe.

This plan is based on local source inspection and the user's concrete product scenarios. Selected upstream protocol/tool references are linked below; this is not a comprehensive upstream survey. No hardware writes, ISO builds or boot tests were performed. The subsequent authorized cleanup and diagnostics baseline changes are recorded above; this plan does not claim installation or hardware verification.

## Core scenarios and product acceptance

| Scenario | Required experience | Acceptance evidence |
| --- | --- | --- |
| Prepare media from a Mac | Open Sonic in uihub/uDOS, identify a removable drive, choose images and tools, review the plan, create and verify media | Complete on a declared supported Mac host; boot the resulting media on the declared reference PC |
| Multiboot toolkit | Ventoy-style menu lists installation, live desktop, diagnostics and recovery images; users can manage image entries without rebuilding everything | Two qualified images boot from one USB; replacing one entry preserves the other and user data |
| Standalone bootable USB | Boot into a usable Sonic environment with CLI/menu, device reference and selected tools without an installed host OS or internet | Cold boot with network disconnected; inventory, local reference and selected recovery tools work |
| Revive an old PC | Inspect hardware, explain compatibility, test the live environment, then install Classic Modern Mint or a lighter qualified profile | Successful installation and reboot, plus recorded graphics, network, storage, audio and input checks |
| Identify drivers | Map detected hardware IDs to the chosen OS/kernel, built-in drivers, required firmware or unsupported components | Distinguish detected hardware from an actually working driver; generate an offline dependency pack where available |
| Reference any device | Find manuals, driver references, technical specifications and repair information even when no installer exists | A library-only record is useful and searchable without claiming device control |
| Repurpose hardware | Match an old PC, router or phone to realistic roles, explain requirements and apply a qualified recipe | One local portal host and one constrained display/client role demonstrated; unsupported roles have reasons |
| Grow shared knowledge | Import reviewed central editions, retain local notes, propose corrections and publish verified findings | Offline access, provenance, edition rollback and a contribution round trip without publishing private instance data |

## Bootable media and Classic Modern Mint

Treat three outputs separately: a **multiboot installer/toolkit USB**, a **live or persistent standalone Sonic USB**, and an **OS installed onto a computer's internal disk**. A menu containing ISO files is not itself a persistent installed desktop. Persistence and portable full installations need their own layouts, update rules and boot tests.

Use a boot-provider contract so an established multiboot implementation can supply early boot while Sonic owns image selection, verification, metadata and the user workflow. The confirmed direction is a Sonic-owned Ventoy-based version or updated fork, with a narrow patch set rather than a new bootloader written from scratch. Its official installation guide documents Windows and Linux tooling, so native macOS media preparation remains a separate engineering gate rather than an assumed upstream feature. Evaluate a qualified prebuilt disk image with a Mac writer versus a managed Linux execution environment with explicit USB access; choose and test one path before advertising Mac creation support. [Ventoy installation guide](https://www.ventoy.net/en/doc_start.html)

Separate the pre-OS boot menu from the GridCore environment that runs after boot. Bundle versioned GridCore fonts, glyph assets, display diagnostics, terminal palettes and rendering tools with their licenses. Generate compatible early-boot theme assets as needed; do not assume the browser canvas can execute in firmware. Keep a plain text fallback if graphics initialization fails.

Classic Modern Mint should be a reproducible, calm, minimal desktop inspired by the simplicity and visual language of classic Mac OS: consistent typography, restrained palette, clear desktop/menu conventions and little visual clutter. Use freely redistributable assets. Its manifest pins the upstream image, package selection, desktop settings, theme assets, GridCore tools, Sonic and optional uDOS/uCode integration. Separate cosmetic preferences from hardware requirements. Live sessions should offer “Try”, “Inspect this PC” and “Install”, with a clear storage review before installation.

base-linux supplies the minimal runtime and module contract; Classic Modern Mint supplies the flagship desktop experience. Qualify its hardware requirements experimentally and offer a lighter profile for machines that do not meet them. Running the management UI on a Mac does not imply that every Mac can boot these Linux images.

## Repurposing and a uDOS-connected device network

Add a **role profile** above installation recipes: portal host, portal client, photo frame, timer, file node, network access point, sensor gateway or other narrowly defined purpose. A role declares minimum capabilities, supported deployment modes, protocols, resource/power expectations, maintenance requirements and evidence. Matching returns viable roles with reasons and blockers, not a blanket “compatible” score.

Prefer the least invasive viable deployment: configure existing software, install a free application, run a local browser client, replace the OS, or flash firmware only when required and supported. An old phone might serve as an offline timer or photo frame on its existing OS; it need not run Linux or a full uDOS agent. Check browser/runtime capabilities, kiosk behavior, storage, sleep/wake, offline operation and sustained-power suitability. Unsupported, reference-only, parts-donor and responsible retirement are valid outcomes.

For PCs and routers, distinguish the roles of portal application host, display client, access point and gateway. An old router may provide connectivity while a PC serves the portal. Firmware support must match the exact hardware revision; use upstream device records as provenance inputs, not model-name guesses. [OpenWrt hardware database](https://toh.openwrt.org/?view=hardware)

Define a small, versioned **uDOS device descriptor** with instance identity, capabilities, roles, protocol endpoints, execution location, software/recipe versions, health and update policy. Support full Linux nodes, lightweight agents, browser-only clients and devices represented through gateways. No universal agent or processor architecture is required.

Proposed open-protocol baseline: HTTP(S) for portal content and capability APIs; MQTT for optional telemetry/events; explicit pairing and local discovery; SSH for authorized administration where supported. MQTT is an open OASIS IoT messaging standard, not a requirement for every device. Select maintained free-software implementations and pin versions during implementation. Protocol adapters should allow existing devices to participate without reflashing. [MQTT specification](https://mqtt.org/mqtt-specification/)

Model portal **reachability** and **access policy** independently:

- Reachability: local host, LAN or deliberately published internet endpoint.
- Access: anonymous/public content, password-protected or identity-restricted.

A LAN portal can still require a password; public content never implies public device administration. Start local-first, with explicit enrollment, revocation and per-role permissions. Do not automatically open router ports or publish services. uCore owns portal/service hosting and access integration; uFlow owns coordinated workflows; Sonic provisions, inventories, verifies and removes device roles. Network services belong to the selected node owner, with declared memory/storage budgets and uninstall procedures.

The first network demonstration should connect a revived PC portal host, an existing or qualified router, and an older browser-capable device showing a local photo frame or timer. Prove boot recovery, offline behavior and role removal. Grow to internet publishing, gateways and sensor fleets through additional qualified recipes.

## Capsules, crypts and tombs

A revived device can be a **physical vessel for a vault edition**: a pocket guide, an encrypted archive, a place-based time capsule, a game artifact or an offline survival manual. The experience takes inspiration from the Hitchhiker's Guide and Doctor Who: discover an object, learn what it holds, unlock it if necessary, and explore its knowledge through a distinctive terminal or teletext interface.

Use **capsule** as the underlying portable content contract. **Crypt** denotes an encrypted capsule profile; **tomb** denotes a sealed archival/presentation profile. These names express purpose and experience, not separate storage engines. A tomb can be public or encrypted. A capsule can live on a USB drive, an old phone, a small computer or storage served by a local gateway; it need not be bootable or continuously networked.

| Profile | Example | Required behavior |
| --- | --- | --- |
| Guide | Old phone containing an offline field library | Start, search and display locally, with all fonts and navigation assets bundled |
| Crypt | Retired laptop or removable drive containing private vault documents | Discover only permitted metadata; unlock through a supported encryption provider; keep keys outside published images |
| Tomb / time capsule | Device placed at an authorized location holding a dated collection | Show creation date, provenance and opening instructions; preserve an immutable edition and a separately retained recovery copy |
| Game capsule | Physical object containing a puzzle, story or old program | Launch a pinned compatible runtime, optionally uCode; isolate saved progress from sealed content |
| Survival library | Offline manuals on a bootable USB or local Wi-Fi node | Expose critical reading without an account, remote service or mandatory unlock; show source, edition and review dates |

The shared interaction is **locate → inspect → unlock if needed → verify → read/display/play → reseal or eject**. Locating can mean attached-storage scan, an explicitly discoverable local service, a QR/printed capsule identifier, or an owner's private placement register. Location is optional metadata, private by default. An unpowered device cannot advertise itself: physical labels and retained records provide the discovery path. A QR link should identify the capsule or a local access method without requiring an internet resolver.

Define a versioned capsule manifest containing: capsule ID, format version, title, edition date, content digests, provenance, required reader/runtime, supported display modes, search index, entry page, optional role/placement metadata, access policy, recovery instructions and resource requirements. Public discovery metadata is separate from protected metadata and payload. References to restricted documents follow their redistribution permissions. Export selected vault content rather than copying the user's entire vault or credentials.

Keep three layers separable: the **content edition**, the **reader/game runtime**, and the **device deployment recipe**. uKnowledge owns vault export, indexing and provenance; Sonic packages and provisions the selected edition and reader onto qualified hardware; uCode executes supported program content. Reading a basic capsule must still work without an installed uCore server. Provide common document formats, a self-contained reader and a plain-text entry document explaining how to recover content with another machine.

Use established encryption implementations behind an adapter, with format/tool-version metadata and tested offline recovery. Do not create a custom cipher. A game puzzle or “open after this date” screen is a presentation condition, not a cryptographic access guarantee. A device clock alone cannot enforce a secure future opening date. Crypt profiles require a separately retained recovery method; public survival profiles can expose an unencrypted essential collection alongside an optional private compartment. Lock/eject clears the reader session and temporary plaintext according to the host's capabilities; do not promise forensic erasure on every old device.

For unattended placement, the recipe records intended power mode, battery/storage condition, enclosure requirements, service interval and a retrieval/removal procedure. Report tested retention expectations rather than promising indefinite storage. Preserve a second verified copy, allow periodic digest checks and media refresh, and offer an unpowered storage-only profile when an always-on node is unsuitable. Immutable content, mutable game saves and device logs have separate storage/quotas; removing the runtime must not silently delete the archive.

Proposed commands extend the same plan/apply workflow:

```sh
sonic capsule pack <vault-selection> --profile guide --output guide.capsule
sonic capsule inspect <capsule>
sonic capsule verify <capsule>
sonic capsule locate --local
sonic capsule unlock <capsule>
sonic capsule open <capsule>
sonic plan deploy <capsule> --target <instance-id> --output plan.json
sonic apply plan.json
```

Add **700 Capsules** to the uihub/GridCore page map: nearby/attached capsules, public cover pages, access state, table of contents, search and read/play actions. Avoid exposing protected titles or search results before unlock. Use the same logical pages in the standalone reader, with a text fallback and no dependency on remotely hosted fonts.

The first capsule milestone deploys a public guide and a separate encrypted sample archive onto qualified reused hardware. With the network disconnected, demonstrate cold start, discovery, search, display, correct/incorrect unlock handling, tamper detection, power-cycle recovery and extraction on a second machine. Add a small uCode game only after its runtime is qualified. This is a core reuse scenario, not a prerequisite for completing the initial USB installer.

## What exists, and what is misleading

| Area | Evidence in this checkout | Consequence |
| --- | --- | --- |
| Source recovery | `.gitignore:84` contains unanchored `sonic`; `git check-ignore` confirms it excludes `cli/sonic/cli.py` and the device YAML. `git ls-files` contains tests/setup but no Python package. | Preserve and review the local package first. A fresh checkout cannot reproduce this working tree. |
| CLI | Click/Rich command groups, envelope/spool helpers, scanner/database/partition libraries exist locally. `commands/usb.py` and `commands/device.py` leave operations as TODOs while emitting success. | Salvage structure; replace false success with explicit unsupported results before wiring operations. |
| Tests | `python3 -m pytest cli/tests -q` passed 18 tests in the current environment. Command tests principally exercise help; other tests cover CLI/telemetry. | Useful baseline, not evidence of installation, firmware writes or clean-package correctness. |
| Packaging | `cli/setup.py` declares 2.1.0; `version` says 0.1.0-dev. Release workflow sets up Go and invokes root `make build`, but the tracked tree has no root Makefile or Go source. An ignored root `sonic` binary exists locally. | Rebuild distribution around reviewed Python source and a single version authority; do not distribute the legacy binary as the new release. |
| Device library | Three YAML families: PCs, routers, ESP32. Database writes into installed package data; IDs feed filenames directly. ESP32 memory values disagree with inline comments. Scanner helpers are partial and `scan_all(timeout)` does not enforce the timeout. | Curate records, separate read-only catalog from overrides, validate IDs and normalize discovery before claiming compatibility. |
| Bootloader | C renderer/menu/detection code and build recipes exist; chainloading contains stubs. `qemu-test` prints suggested commands rather than executing a boot test. | Treat as experimental. Custom bootloader completion must not block the first CLI release. |
| Mint | ISO customization scripts exist, including privileged mounts/chroot, passwordless sudo configuration, and signing-key import with `|| true`. | Audit and test in disposable Linux builders before reuse. Classic Modern Mint becomes the flagship desktop profile after qualification. |
| uihub | uCore routes `/sonic` to `SonicScrewdriverSurface.vue`, with hard-coded counts and July sample events. | Replace the demo surface with live capabilities, inventory and operation data. |
| GridCore | uCore has `TerminalRecipeView.vue`, canvas/buffer adapters and `@udos/gridcore` types; the recipe view renders a fixed C64-style example. | Reuse rendering primitives, but implement real menu input/state; this example is not an installer session transport. |
| Ecosystem | uCore owns hosting/extensions; uFlow owns workflows. uKnowledge owns knowledge, provenance and vault contracts; udos-vaults describes vault topology integration. | Integrate through these owners. Standalone Sonic must not require any of them to run. |
| Storage | Sonic spool currently uses `~/.local/share/udos`; workspace policy requires mutable ecosystem state under `UDOS_HOME`. | Centralize configuration and provide an explicit migration path. |

No existing `base-linux` manifest or implementation was found by the inspected workspace searches. Its interface below is a proposal pending identification of the intended Linux build owner.

## Architecture and ownership

```text
sonic CLI / terminal menus       uihub /sonic + GridCore
             |                         |
             |                 uCore Sonic adapter
             +------------+------------+
                          |
                Sonic application services
      inventory · catalog · artifacts · plans · operations
                          |
              platform/device provider adapters
           discovery · install · flash · verify · recover
                          |
              devices attached to the execution host

Global Devices edition -> catalog + recipes -> resolved operation plan
uKnowledge indexes vault content; uFlow can orchestrate Sonic operations
base-linux consumes the same Sonic release and selected offline packs
```

Keep Python/Click initially. Separate commands and presentation from application services, typed contracts, storage and adapters. Rich output goes to the terminal; machine output is schema-versioned JSON/JSONL with stable exit codes and no ANSI. Optional hardware dependencies load only when their provider is selected.

Sonic owns device semantics and individual operation journals. uFlow optionally owns multi-step ecosystem workflows; Sonic does not become a second task scheduler. uCore owns authentication, API hosting and browser access. Avoid a mandatory Sonic daemon: CLI operations run locally, while uCore launches or hosts the same service layer behind its existing lifecycle contracts.

## CLI and operation contract

Proposed command vocabulary (not commands currently implemented):

```sh
sonic doctor --json
sonic device scan --json
sonic device show <instance-id>
sonic library search <query>
sonic library show <model-id>
sonic vault sync --edition <edition>
sonic artifact fetch <artifact-id>
sonic plan install <profile> --target <instance-id> --output plan.json
sonic plan flash <recipe-id> --target <instance-id> --output plan.json
sonic apply plan.json
sonic operation show <operation-id> --json
sonic operation logs <operation-id> --follow
sonic menu
```

Planning resolves exact hardware identity/revision, execution host, provider/tool versions, firmware hashes, partition layout or flash offsets, dependencies, expected effects, recovery prerequisites and verification steps. Plans contain no credentials. Apply rechecks identity and preconditions immediately before writes and refuses stale plans, ambiguous targets and changed artifacts. Headless execution requires explicit authorization bound to the plan and target; a general `--force` cannot bypass compatibility checks.

Use operation states such as planned, awaiting-confirmation, running, verifying, succeeded, failed, cancelled and recovery-required. Persist step receipts and stream events with operation ID, sequence, timestamps, progress and errors. Success requires postconditions. Cancellation is available only at safe boundaries; interrupted destructive steps are never blindly replayed. Record whether rollback, backup restore or manual recovery is actually supported.

Providers declare supported operations and privileges. Keep browsing/discovery unprivileged where possible; isolate privileged writes behind bounded arguments, target checks, locks and timeouts. Protect the running system disk, its parent devices and mounted dependencies. A browser connects to the selected execution host: a remotely hosted uihub cannot implicitly access USB devices attached to the browser computer.

## Device library and Global Devices vault

Separate the following records:

1. **Device model:** vendor, model, board revisions, architecture, identifiers, interfaces, memory components with explicit units, power/pinout, boot modes, technical references and provenance.
2. **Device instance:** local serial/connection identity, detected revision, installed firmware, owner labels, backups and operation history. Private by default; never included in public catalog contributions.
3. **Artifact:** immutable digest, size, version, origin, signature/trust metadata, license/redistribution rights, architecture, compatible revisions and retrieval mirrors.
4. **Recipe:** versioned input schema, provider, pinned artifacts/scripts, prerequisites, exact targets, write steps, checks, expected results, recovery procedure and test evidence.

Add a **driver binding** record linking hardware IDs/revisions to OS/kernel versions, built-in modules, firmware artifacts, installation methods and working-device test evidence. Add a **role profile** linking desired uses to capability requirements and qualified recipes. Manuals and specifications remain independently useful when no binding or recipe exists.

Support status should distinguish documented, detected, experimental, tested and verified for a specific operation. Record test date, tool/recipe versions and board revision. A USB VID/PID match alone never authorizes flashing. Include manuals, schematics, datasheets, pinouts, bootloader unlock requirements, flash maps, known faults, repair notes and repurposing recipes. Keep firmware binaries outside Git in content-addressed storage; reference restricted material without mirroring it when redistribution is unavailable.

Proposed layout, resolved through settings rather than hard-coded home paths:

| Location | Owner and purpose | Lifecycle/budget |
| --- | --- | --- |
| `SonicScrewdriver/catalog/` | Sonic schemas, small seed records and reviewed recipes | Versioned source; normal repository review/removal |
| `~/Public/global-devices` | Installed read-only Global Devices edition | Explicit install/update/remove; edition size shown before download |
| `~/Vault/devices` | User notes and contribution drafts | User-owned; uninstall preserves documents |
| `$UDOS_HOME/sonic` | Inventory, operation receipts, locks, overrides, artifact cache and backups | Explicit quotas/retention; cache GC; backups require separate deletion intent |

Reuse uKnowledge’s existing filesystem-first library for optional standalone document packs; it does not require a running uCore server. Keep Sonic model matching separate from document search, and use the same uKnowledge contract when hosted. Match its Public-vault model: users propose contribution packages; maintainers validate and publish editions. Downloading a vault or indexing a script never executes it. Reviewed recipe execution is a separate action.

Start with versioned catalog snapshots and deterministic local search. Add signing, digest verification, update trust roots, revocation and rollback policy before automated updates. Default to on-demand artifact fetch; offline packs contain only selected device families and verified dependencies. Display required download and expanded sizes and available disk space before import.

## Distribution and base-linux module

Ship one Python wheel/source distribution from clean CI, with tested inclusion of seed data. Offer stable and preview channels through versioned release metadata; add native Linux packaging after the core package is reliable. Distinguish installing/updating Sonic itself from installing an OS or firmware onto a target. Updates stage and verify the replacement before activation and never interrupt active writes.

The proposed base-linux module is a declarative consumer: pinned Sonic version, distro/architecture compatibility, system packages, optional provider extras, udev/permission rules, selected catalog edition, offline artifacts, CLI/menu entrypoint, health check and uninstall procedure. It should work without uCore, a desktop, an account or a network once its pack is installed. It is not a new distribution or a runtime state owner.

First target: one selected minimal Linux base and x86_64 UEFI image profile. Qualify Classic Modern Mint as the flagship desktop profile of the same recipe system, alongside the minimal standalone toolkit. Use a proven boot path already available in the selected base; do not revive the removed custom C stub. BIOS, ARM boards, Secure Boot and Apple Silicon require explicit independent validation lanes rather than inherited compatibility claims.

## uihub and teletext experience

Evolve the existing `/sonic` route into a dedicated device workspace:

- **100 Home:** connected devices, supported actions, active operation and execution host.
- **200 Library:** keyboard-searchable manufacturer/category/model pages; stable model IDs behind page numbers.
- **300 Device:** specifications, revision, interfaces, pinout references, firmware and evidence.
- **400 Install / flash:** select target and recipe, resolve plan, inspect changes, confirm, follow progress, verify.
- **500 Recovery:** backups, logs, recovery procedures and repurpose options.
- **600 Vault / channel:** installed edition, offline packs, update status and contributions.

Reuse uCode GridCore’s existing reader model/state/rendering/interaction and terminal primitives, supplying Sonic content and semantic actions rather than a new reader engine. CLI terminal menus render the same information model through a terminal renderer; they need not share pixel rendering code. Support 40-column compact and 80-column expanded layouts, arrows/Enter/Escape, numbered pages, search and clear status labels. Provide an accessible DOM/text companion, focus handling and readable plain output.

Proposed uCore adapter API: capabilities, device inventory/detail, library search/detail, plan creation, operation creation/status and event streaming under `/api/sonic`. Both menu and web clients call the same application services. A raw shell/PTY can be an explicit expert tool later; it is not the installer API. Reconnect must reconstruct state from persisted operation records instead of launching another write.

## Delivery sequence and acceptance gates

| Stage | Deliverables | Gate |
| --- | --- | --- |
| 0 — Recover truthful baseline | Preserve ignored sources; narrow ignore rules; reconcile versions; audit local binary provenance; replace false success; correct README; repair Python release workflow | Fresh checkout installs a built wheel, includes catalog data and passes tests without editable-source leakage; unsupported commands return nonzero |
| 1 — Useful standalone reader | Settings/storage, normalized discovery, model/instance schemas, curated seeds, library search/show, JSON output, doctor | Works offline on chosen Linux host; missing tools and unknown devices give accurate results; catalog edits never touch package installation |
| 2 — First real operation | Plan/apply engine, target locks, artifact checks, removable-media provider, verification and receipts; qualify the Mac execution path | Fixture tests and sacrificial USB write/readback; system disk, changed target and tampered image refused; Mac host support demonstrated |
| 3 — Installer and base-linux | Multiboot menu, standalone Sonic image, Classic Modern Mint profile, GridCore asset pack, module manifest and offline drivers/reference | Two menu images boot; standalone tools work offline; reference PC installs Mint and passes device checks; uninstall preserves user data |
| 4 — Integrated surface | Optional uCore extension, real inventory/events, GridCore menus, teletext library and accessible fallback | CLI and uihub resolve equivalent plans; reconnect and cancellation are tested; host identity remains visible |
| 5 — Published channel and vault | Signed editions/releases, staged updates, contributions, role profiles and a local portal network demonstration | Tamper/stale metadata tests; contribution round trip; PC portal plus older client works offline; role removal verified |
| 6 — Additional device providers | Qualified ESP32 and router flashing recipes, gateway/telemetry adapters, expanded device and driver records | Exact-board hardware evidence; compatibility refusal tests; explicit enrollment/revocation; no blanket phone/router support claims |
| Capsule milestone — after standalone media and vault contracts | Portable capsule manifest/export, guide/crypt/tomb profiles, offline reader, GridCore pages and deployment recipe | Disconnected reading and unlock, tamper detection, power-cycle recovery and recovery on a second machine; immutable content survives runtime removal |

Stages 2 and 3 depend on Stage 1; Stage 4 can begin with read-only Stage 1 APIs and add writes only after Stage 2. Stage 5 completes production distribution. Do not attach a calendar until recovery and reference hardware selection establish effort. Track these milestones through uFlow, treating the old `.tasker.dev-flow.yaml` as historical input.

## First implementation backlog

1. `SONIC-001`: recover ignored Python/data files with a reviewed inventory; preserve local content before cleanup.
2. `SONIC-002`: replace TODO success paths with typed unsupported results; add behavior tests.
3. `SONIC-003`: consolidate package version/build metadata, optional dependencies, package data and clean-wheel CI.
4. `SONIC-004`: implement `UDOS_HOME` configuration and migration; run uCore's `scripts/check_home_path_policy.py` for path changes.
5. `SONIC-005`: define model/instance/artifact/recipe/operation schemas and migrate the three seed families with provenance review.
6. `SONIC-006`: wire real read-only scan/lookup, enforce timeouts and structured errors; test parser fixtures and duplicate/ambiguous identities.
7. `SONIC-007`: implement plan/apply with a fake provider and failure-injection tests before enabling hardware writes.
8. `SONIC-008`: qualify the Mac media-creation host and one sacrificial Linux installer target; publish their exact support matrix.
9. `SONIC-009`: add uCore extension and replace the mock `/sonic` data with live read-only services.
10. `SONIC-010`: build shared menu state and GridCore device pages; add installer steps after operation qualification.

11. `SONIC-011`: build Classic Modern Mint profile and multiboot/standalone USB manifests with bundled GridCore assets.
12. `SONIC-012`: add driver bindings, role matching and a PC/router/older-client local portal demonstration.
13. `SONIC-013`: define capsule/export contracts with uKnowledge and deliver a standalone offline guide on reused hardware.
14. `SONIC-014`: qualify an encryption adapter and recovery workflow; add crypt/tomb profiles, local discovery and capsule pages.
15. `SONIC-015`: qualify a capsule game runtime with uCode, separate saves from sealed content, and document physical placement/maintenance profiles.

Release completion means a new user can install Sonic from its channel, browse an offline device edition, identify a supported attached target, inspect and apply a pinned plan, verify the result, recover from documented failures, and perform the same workflow through uihub. Base-linux must ship that capability without uCore. The flagship demonstration begins on a Mac, creates a toolkit USB, revives a reference PC with Classic Modern Mint, then connects it to an older client for a useful local role. Broader firmware coverage and network roles require separate evidence gates. The retired custom bootloader, CHASIS storefront and commercial USB commitments are not part of the backlog. Games use qualified uCode payloads.

Decisions to settle during Stage 0: the intended base-linux owner/base distribution; available reference hardware; channel publishing ownership and signing custody; and whether Global Devices is a separately installed vault edition or a named edition within an existing global corpus. The proposed boundaries support either vault packaging choice.

## Recovered backlog and dependency order

The historical audit adds SONIC-016 through SONIC-022, defined in the reconciliation register: installer-contract reuse, reversible Mint settings, legacy schema import, explicit recovery flows, uCore companion provisioning, uCode capsule alignment and Beacon exchange features. These are backlog definitions, not parallel services to implement.

Sprint 1 is limited to reproducible packaging, settings, validated records, read-only Linux discovery/library commands and reuse/build spikes. The next execution sprint must use HomeNest/uCore contract findings. Mint's profile is first proven post-install, then reused inside a preconfigured live image. Beacon starts read-only and local; uploads/chat/sync are separately qualified. Native Mac disk writing and production distributions remain separate release gates.

## Successor sprint: HomeNest

The next product revival is [HomeNest](../../HomeNest/docs/REVIVAL-PLAN-2026-09.md):
standalone Linux Steam gaming and media. HA/Matter has a separate
[adapter repository](../../udos-home-assistant/README.md). Sonic provisions and
installs each independently. Characterize HomeNest's existing installer code
before any shared extraction; do not maintain copied installer implementations.
HomeNest's first release must also work through manual artifact installation.
