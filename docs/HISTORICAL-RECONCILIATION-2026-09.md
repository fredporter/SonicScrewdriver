# Sonic historical reconciliation

Reviewed 10 September 2026. This is the disposition register for the [revival plan](REVIVAL-PLAN-2026-09.md). Older completion labels and command examples are historical evidence, not current product contracts.

## Audit scope and limits

Inspected the current Sonic tree, ignored Python source, local Git history and `origin/legacy/v1-go`; Sonic plans and archives; relevant uCore/uCode distribution and learning documents; archived DevStudio specs including hidden `.compost`; archived uServer Sonic/CmMint prototypes; and the installer lineage from archived uCode3 into current HomeNest. Followed historical references to source where available. Indexed source snapshots in [the provenance inventory](HISTORICAL-SOURCE-INVENTORY-2026-09.json).

Sonic HEAD: `92fff66`; local legacy ref: `ed4a7debf7e010bcd3237776f1c4aeffe6765489` (8 June 2026). Local remote-tracking refs were inspected without fetching. This is a local estate audit, not verification of remote release availability, external URLs, every historical commit, or physical hardware behavior. No installer, recovery, flashing or legacy daemon was executed. The subsequent current Python baseline tests and package checks are reported in the cleanup summary. The earlier 18-test result applies only to the current local Sonic CLI baseline; HomeNest tests were inspected, not run here.

Disposition meanings: **adopt** preserves a concept; **adapt** preserves it under current contracts; **defer** retains an explicit later milestone; **superseded** replaces an old specification; **retire** removes a direction permanently from the revival backlog. Retired directions require a new explicit product decision to reopen. After this audit the user authorized removal: superseded Sonic files are removed from the active checkout, with hashes in CLEANUP-2026-09.json, tracked history in Git, and a temporary pre-cleanup source snapshot. External archives and other product repositories were not deleted.

## Newly recovered details worth keeping

1. **Sonic Beacon already had a detailed design.** DevStudio's `UDN-SONIC-V2-001.md`, §14.3, describes an offline router portal with file sharing, local chat, games and vault synchronization. Adopt Beacon as a named portal role; begin with read-only publishing and explicit local access. Chat, uploads and sync need separate storage/access/conflict contracts. The router/model compatibility examples are unverified and must not seed a trusted flashing recipe.
2. **A real Go implementation preceded the current scaffold.** Git history contains Linux disk discovery/partitioning, ISO downloads/writes, driver metadata, firmware-tool adapters, backup records, library manifests and tests. `5495a1b` removed the Go tree after the v2 rewrite. Recover behavior and test cases selectively; do not restore the whole Go runtime. The Python package was excluded by an ignore rule introduced for the old binary, making the apparent rewrite especially misleading in clean checkouts.
3. **Older flashing covered more transports.** `pkg/reflash/reflash.go` includes UF2, DFU, ESP, AVR, STM32, JTAG and SD pathways. These are adapter candidates, not proven support: `Verify()` merely sleeps and returns true. Qualify one provider at a time after the USB journey, with actual post-write verification.
4. **Backup was modeled as a first-class artifact.** Legacy `pkg/recovery/recovery.go` defines firmware/config/state/full/partition/bootloader/filesystem records with hashes, tags and import/export. Adopt the record model. Rewrite capture/restore per provider: the old implementation reads whole paths into memory and even models config as a prefix of device bytes. It is not a universal firmware backup method.
5. **Driver tracking and catalog overlays had a second Python prototype.** Archived uServer `sonic-screwdriver/` has YAML driver commands and catalog import/custom-record paths. It has useful semantics but inconsistent list-versus-map catalog handling, manual USB steps and an obsolete HTTP wrapper. Retain import requirements and fixtures, not a second service.
6. **Mint customization can work in two delivery modes.** May's CmMint plan explicitly preferred a stock Mint installer plus first-run customization; June's Sonic tree switched toward remastered ISOs. Resolve this with one idempotent profile: apply to installed Mint or apply during image creation. Verify the post-install profile first, then use the same inputs for the flagship preconfigured live image. Back up existing settings and support profile removal without reinstalling the OS.
7. **More CmMint scripts survive than the current Sonic tree suggests.** Archived uServer has browser/icon configuration, Mint settings backup/restore, Obsidian backup scripts and first-run setup. They depend on old paths, absent extension assets and uConnect development servers; package restoration is explicitly incomplete. Recover settings categories, backup receipts and rollback scenarios. Do not execute or import those scripts wholesale.
8. **A newer hidden charter supports CLI independence.** DevStudio `.compost/.../classic-modern-mvp/docs/sonic-tui-charter.md` says core work must run without opening a browser, including over SSH. It claims a Python/Textual track and later Go/Bubble Tea direction; matching implementation was not found in this audit. Adopt terminal independence and next-action errors; retain the existing Python stack and optional uihub surface. Its Ubuntu/ThinUI default is a separate host profile, not a replacement for the user's Mint direction. The adjacent apply script is explicitly a placeholder.
9. **Staging and rollback are not entirely greenfield.** Archived uCode3's `uhome_server/sonic/*` files are largely compatibility wrappers around `installer/*`. The implementation and tests survive in current `HomeNest/src/uhome_server/installer` and `HomeNest/tests`. Compare bundle verification, preflight, stage receipts, target promotion and rollback with Sonic's intended contracts before implementing duplicates. HomeNest keeps its product installer and media behavior; any shared extraction requires characterization tests and an explicit owner.
10. **Companion mode is part of the current ecosystem plan.** uCore's `DISTRIBUTION_AND_SONIC_PATHWAY.md` includes installing, inspecting, updating, backing up and repairing uCore itself. Add this as a profile after the standalone device path, consuming uCore's signed component manifest. A browser PWA alone does not install its backend/runtime.
11. **Capsules overlap an existing uCode runtime term.** `uCode/scripts/probe_capsule_runtime.py` exercises a catalogue capsule over `ucode-session/1`. Sonic's physical vault capsule should contain or reference that runtime payload through an adapter; it must not redefine the existing program/session protocol. No running-session behavior was tested in this audit.

## Source and concept disposition

Paths below are relative to Sonic unless another repository is named. The inventory records full local paths and content hashes. Superseded document bodies remain in recorded history; the revival plan, reuse report and Sprint 1 brief define the confirmed forward scope.

| Source / historical claim | Evidence and decision | Destination / gate |
| --- | --- | --- |
| `README.md`, `ROADMAP.md`: v2 complete | **Superseded** completion narrative; CLI operations and C boot paths remain partial | Revival baseline and truthful capability matrix |
| `docs/SONICSCREWDRIVER_DEV_PLAN.md`, `.tasker.dev-flow.yaml`: July integration complete | **Superseded** execution authority. Tracker summary says 9/9 complete while nine detailed tasks remain `todo`; older 14-task archive is only partially enumerated | Recreate accepted tasks in uFlow from current evidence, not counts |
| `docs/USB-CREATION.md`: universal triple-partition instructions | **Adapt** user journey; **retire** fixed universal layout and unverified Mac boot claims | Per-provider layouts, Mac writer gate, separate multiboot/live/install profiles |
| `docs/sonic-linux/README.md`: minimal Mint and five required Sonic services | **Adapt** minimal profiles; **retire** required Sonic core/home/network/vault daemons and fixed historic resource/version promises | base-linux module; measure actual resource budgets |
| `docs/classic-modern-mint/SETUP-GUIDE.md`: developer workstation, email feeds, MCP and replacement apps | **Adapt** optional settings profile; **retire** mandated developer/browser/editor stack and email pipeline inside Sonic | Mint role profile; host/workflow integrations stay optional |
| `docs/archived/classic-modern-mint-README.md`: theme pipeline, vendor workspaces, claimed 47 tests | **Adapt** reversible theming and provenance; **retire** Sonic vendor-copy/patch/sandbox authority. Inline expected output is not a test result | Profile builder; source management remains external development work |
| `docs/archived/classic-modern-mint-usxd-ui-plan.md`: static web + Bubble Tea + OBF | **Adapt** shared information model and keyboard navigation; **supersede** duplicate UI stack | GridCore/terminal renderers and uihub adapter |
| `docs/USXD-OBF-STYLE-GUIDE.md` and legacy `spec-sheet.md` | **Adapt** quiet visual intent and fallback assets; **retire** new Sonic OBF compiler/opaque style format. OBF is described inconsistently across docs | Existing uCode/GridCore and uCore tokens; licensed asset pack |
| `docs/USX-NPM-STRUCTURE.md`, `usx-sonic-tokens.md`, `usx-migration-guide.md` | **Adapt** semantic status/accessibility; **supersede** copied package ownership, versions and standalone Vue scaffold instructions | Import current host contracts, no duplicate frontend project |
| `docs/dev-tools-parity.md`, `sonic-skill-catalog.md`, MCP manifest/bridge | **Adapt** tool inventory and event concepts; catalog/manifest/decorator do not prove a working MCP server or enforced policy | Generate tool surface from real capabilities; share plan/apply authorization; redact events |
| `docs/bootloader-status-taxonomy.md`, C bootloader and YAML menus | **Retire** custom firmware-loader implementation after user direction; retain lifecycle/display ideas as provider reference | Independent build/boot qualification; not a release prerequisite |
| `mint/*.sh`, theme overlay | **Adapt** extraction/overlay/repack intent; privileged scripts not qualified | Disposable builder, verified inputs, cleanup traps, settings rollback |
| `recovery/README.md`, `recovery/scripts/*` | **Adapt** diagnostics and recovery roles. Disk script includes actual fsck/wipefs calls and swallows errors; unlike CLI stubs it can modify media | Read-only triage first; image-before-repair option, explicit repair plans and credential-recovery policy |
| `interface/dashboard.html`, uCore Sonic surface | **Supersede** demo events/statistics; retain only useful presentation examples | One live uihub surface |
| Legacy Go `disk`, `iso`, `usb`, tests | **Adapt** parsers/layout/test cases. Whole-disk ISO write after custom partitioning can replace that layout; empty checksum is accepted in downloader | Separate raw-image write from partition assembly; mandatory verified artifacts |
| Legacy Go `driver`, `reflash`, `recovery`, `knowledge` | **Adapt** driver/transport/backup concepts; **retire** assumed verification and home-directory stores | Sonic providers; uKnowledge content; new storage contract |
| Legacy Go `library`, `catalogue`, `.she` packager | **Adapt** requirements/manifest concepts; archive runtime. `.she` code creates tar/gzip, while later spec proposes a fixed header/signature/payload format | Canonical bundle schema plus explicit legacy importer only if real bundles require it |
| Legacy Go `vault` and `sonic-udos-uhome.md` | **Retire** Sonic as central API gateway/master secret store; code wraps old uServer secrets | uCore identity/credentials; capsule crypto is a separate artifact function |
| Legacy `container`, `remote`, CHASIS game library | **Retire** general container platform, VNC manager and game storefront as Sonic responsibilities | uCode game/runtime integration; host-owned remote administration |
| DevStudio `SONIC_SPEC.md`, `UDN-SONIC-V2-001.md` | **Adapt** Beacon, recovery, offline docs, capability-based reuse; **supersede** bootloader-first rewrite and giant feature checklist | Current role/provider model |
| Archived uServer Python CLI and server | **Adapt** driver/library import semantics; **retire** port-30005 server, hard-coded paths and duplicate command namespace | Sonic application services/uCore adapter |
| Archived uServer `cmmint/` docs, scripts, configurations | **Adapt** post-install profile and settings backup; **retire** migration to a new cmmint repo, mandatory Obsidian/Zen and legacy cron/dev-server autostart | Classic Modern Mint inside Sonic profile structure; user-selectable app bundles |
| Hidden Classic Modern MVP host profile, tokens, CSS, ThinUI notes | **Adapt** low-resource/quiet host appearance and native-desktop fallback; **defer** alternate Ubuntu profile | Existing rendering/host owners; no competing ThinUI implementation in Sonic |
| Archived uCode3 `UDN-SONIC-001.md`, standalone release guide | **Adapt** offline/LAN channel, signed payload and staging concepts; **retire** separate Sonic-Home-Express product/runtime | One Sonic distribution contract |
| Archived and current Sonic-Home installer guides | **Superseded** release URL/version/support claims until independently verified | Current HomeNest manifests and current support evidence |
| Current HomeNest installer and tests | **Retain with owner**, compare generic contracts; archived mirrors stay archived | Contract comparison before any extraction; no media-stack migration |
| uCode learning-pathway layout/manifest/dry-run lesson | **Adopt** inspectable planning; **supersede** literal examples as current commands. Named layout/script paths were not found in this search | New CLI docs generated against shipped commands |
| uCore distribution/spec-inventory plans | **Retain** ownership/discovery and coordinated release gates | This reconciliation is design evidence; hardware and release sign-off remain open |
| uCode capsule runtime probe | **Retain with owner** | Sonic physical capsule references supported uCode program/session contracts |

## Permanently retired directions

These are closed backlog directions, not merely unscheduled milestones:

- Sonic as the ecosystem API gateway, secret authority, AI/swarm coordinator or always-on platform core.
- A separate Sonic-Home/Sonic-Express family of daemons and products, mandatory Docker runtime, general vendor workspace manager or competing frontend application.
- Recreating Home Assistant/Matter automation, moving HomeNest media ownership into Sonic, or restoring legacy uConnect/uServer runtime dependencies. The current uCore pathway explicitly keeps those boundaries separate.
- CHASIS premium storefront/trial bundles, cryptocurrency wallet integration and priced/manufactured USB promises as requirements of this revival. Physical distribution can be proposed later through a fresh product decision.
- Claims that ordinary storage can become a FIDO authenticator or self-networking mesh node through generic enrollment. Support must be declared against actual hardware capabilities and verified providers.
- A compulsory custom C bootloader, one partition layout for every platform, invented test output as acceptance evidence, and silent-success wrappers.
- Proprietary/uncleared branding assets or a mandatory browser/editor choice as the basis of the free-software desktop. The visual direction survives independently of those dependencies.

## Explicit later candidates

Keep a bounded incubation list: PXE/iPXE network installation; USB gadget/virtual-CD mode on capable hardware; direct-attach UF2/DFU/JTAG providers; separately qualified BIOS/ARM/Mac boot targets; peer/offline pack synchronization; optional local uploads/chat; alternate Ubuntu Classic Modern profile; and broader router/phone roles. Each needs an owner, device requirements and a real acceptance test before promotion. Do not recreate them as empty modules now.

## Consolidated additions to the backlog

| ID | Work and owner | Acceptance |
| --- | --- | --- |
| SONIC-016 | Sonic + HomeNest: compare existing bundle/stage/receipt/promotion contracts before implementing SONIC-007 | Written mapping, reuse/extraction decision and characterization tests; no duplicated lifecycle authority |
| SONIC-017 | Sonic Mint profile: recover settings backup/restore semantics; one profile for post-install and image build | Apply twice safely, verify settings, remove profile and restore prior settings on disposable Mint |
| SONIC-018 | Sonic + uKnowledge: schema migration fixtures for old catalog list/map variants, driver records, backup metadata and legacy bundles | Deterministic import, invalid-record report, private-data separation; no execution on import |
| SONIC-019 | Sonic recovery: inventory read-only diagnostics vs mutations and define backup/repair flows | Failure and cleanup tests; disk identity protection; no false success; documented restore limits |
| SONIC-020 | Sonic + uCore: signed companion install/inspect/repair profile | Clean-host install and repair through uCore-owned lifecycle manifest; no second service supervisor |
| SONIC-021 | Sonic + uCode: reconcile physical vault capsule with existing program capsule/session | Offline content reader plus one qualified program payload; clear schema names and ownership |
| SONIC-022 | Sonic + host/workflow owners: Beacon role and optional exchange features | Read-only offline portal first; upload/chat/sync each separately approved, quota-bound and removable |

## Readiness assessment

The local historical reconciliation is sufficient to review scope and prioritize source recovery. It is not a hardware sign-off. Before an implementation sprint, reconcile the selected host/target matrix and disk-write policy with uCore's distribution discovery gate; identify the base-linux owner and upstream release prerequisites. No approval or deployment was inferred from old “complete” labels.

The best immediate investment remains source recovery and truthful packaging, followed by the Mac-to-USB-to-Mint workflow. The audit adds reusable contracts and stronger acceptance tests without restoring the old platform sprawl.

## Confirmed disposition after review

The user accepted Beacon, Python/Linux, uDOS delegation and removal of deprecated artifacts. The Go runtime, standalone Sonic platform services, old custom bootloader and failed Mint implementation are closed. Ventoy is the preferred Sonic-owned derivative; Mint is rebuilt from retained design theory. ISO generation and capsule/vault behavior consume qualified upstream and ecosystem implementations as documented in REUSE-AND-UPSTREAM-2026-09.md.
