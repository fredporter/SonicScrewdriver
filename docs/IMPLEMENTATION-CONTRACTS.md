# Sonic implementation contracts

Status: design baseline, 12 September 2026. These contracts describe next work;
only the command groups listed in the handover exist. Do not create placeholder
commands that report success or infer supported operations from catalog labels.

## Scaffold and ownership

| Location | Owner / purpose | Lifecycle and removal |
|---|---|---|
| `cli/sonic/commands/` | Sonic CLI adapters; Click input/output only | Shipped with wheel; remove command registration with retired feature |
| `cli/sonic/lib/catalog.py` | Validated model catalog and initial data types | Read-only package records; upgrade with package |
| `cli/sonic/lib/settings.py` | Sonic state resolution and explicit legacy intake | No automatic migration; preserve originals |
| `cli/sonic/lib/spool.py` | Local event journal | Under UDOS_HOME; retention/rotation is implementation work |
| `cli/sonic/data/devices/` | 21 unverified model seeds | No writes here at runtime; historical claims remain quarantined |
| Proposed `cli/sonic/providers/` | Read-only inventory and later qualified operation adapters | Add concrete providers only; timeout and capability contract mandatory |
| Proposed `cli/tests/fixtures/` | Sanitized parser and fault fixtures | Checked-in deterministic inputs; no private device serials |
| Proposed `contracts/` | Exported validated schemas for external consumers | Generate from authoritative models; test for drift rather than maintain two definitions |
| `$UDOS_HOME/sonic` | Sonic-owned journal, intake, later cache/operation state | No new home-directory root; bound cache/journal growth; uninstall retains user data by default |

Do not pre-create empty services, UI projects, containers or an IDE/Gemini
configuration tree. The current scaffold is the installable Python package,
its tests and these contracts. New providers should be introduced with behavior.
User manuals/spec documents remain in Vault/Shared/Public or the uKnowledge
edition; Sonic holds references and device-specific bindings, not a second
knowledge engine. Initial library queries only search bundled model labels.

## Read-only discovery (first Gemini implementation)

Public command proposal: `sonic scan --json`, optional `sonic doctor --json`.
Use Linux USB/PCI/block-device inventory with explicit fixed argument vectors,
no shell, no sudo, no writes and a finite timeout per probe. Verify tool flags
against the installed Linux tool versions before locking fixtures. macOS must
return an explicit unsupported provider result until separately implemented.
Never silently substitute old ioreg/ifconfig heuristics.

Result proposal: schema version, execution host/platform, observation timestamp,
probe results and normalized devices. Each probe has tool/version when known,
status (`ok`, `missing-tool`, `timeout`, `permission-denied`, `parse-error`,
`unsupported`, `failed`), structured error and elapsed time. Overall status is
`ok`, `partial` or `unsupported`/`failed`. Empty successful output is distinct
from a failed probe. Plain output and JSON describe the same result; JSON has
no ANSI or diagnostic prose. Document exit codes: 0 complete, 1 partial/failure,
2 invalid usage; unsupported execution must be nonzero.

Hardware IDs carry bus, vendor/product and subsystem/revision where observed.
Keep observations separate from catalog model candidates. USB bridges and
shared IDs may match multiple models; report all with evidence, never pick the
first. Serial numbers are private instance data, excluded from shared editions
and default diagnostic output. Zero model matches is a useful scan result.
Presence of a device/driver is not evidence that the driver functions correctly.

Acceptance: offline fixture replay; malformed/truncated output; no devices;
missing tools; timeout; nonzero exit; permissions; mixed probe outcomes;
ambiguous IDs; JSON parsing; no state writes; macOS unsupported case; installed
wheel outside source checkout. Follow with real read-only Linux host evidence.

## Data contract hardening

`catalog.py` strict models are the starting point. Instance and driver types
are provisional: validate timezone-aware observation times, ID grammar,
nonempty unique hardware IDs and model references. Unknown values stay null;
capacities use explicit bytes, positive integers, no guessed MB/GB conversion.
A cited source/revision is not itself verification. Add evidence types and
review status before any record can influence a supported-operation decision.
Keep library model, physical instance, driver binding, recipe and artifact
separate. Retain all legacy claims without promoting them to verified fields.

## Operations and distribution (after read-only acceptance)

Before adding an engine compare HomeNest `src/uhome_server/installer/` bundle,
preflight, plan, staging, promotion and health contracts with uCore distribution
lifecycle. Record exact paths/revisions, adopted behavior and deliberate gaps.
Sonic owns generic device/media application; HomeNest owns application payloads.
Do not copy the same installer into both repositories.

Plan contract: immutable plan ID/hash, target fingerprint, execution host,
recipe/artifact identities and digests, prerequisites, permissions, changes,
verification/recovery steps and expiry. Apply revalidates target and artifacts,
locks the target, requires explicit confirmation of destructive intent, records
progress/receipt, and fails closed on identity changes. Idempotency/reconnect
must never start a second write. Test fake providers and interruption first;
physical writes require a qualified sacrificial target and verification.

base-linux is a declarative consumer of the same released package, selected
catalog and optional provider dependencies. It adds no state/service owner.
Ventoy-derived boot support needs license/component inventory, pinned Linux
build and VM boot evidence before a downstream patch/fork is accepted. Vendor
RAW stays pristine; forks belong in an owning product repository. Mac control
via uihub is distinct from Mac raw-media execution support.

## Cross-product boundaries

uCore: optional identity/secrets/module lifecycle and host integration.
uCode/GridCore: terminal rendering/fonts/teletext reader and program capsules.
uFlow: durable cross-product workflows. uKnowledge: document/vault indexing.
HomeNest: standalone Steam/media payload. `udos-home-assistant`: separate home
control integration and card; upstream HA/Matter handles home protocols.
Sonic supplies device knowledge, qualification, provisioning and distributions.
No new API gateway, secrets server, scheduler, reader engine or Matter stack.
