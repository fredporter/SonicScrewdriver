# Reuse boundaries and upstream intake

10 September 2026. Source-level assessment, not runtime qualification of other repositories.

## What Sonic must not duplicate

| Capability | Existing source / owner | Sonic decision |
| --- | --- | --- |
| Teletext document model, state, render and input | `uCode/packages/gridcore/src/teletext/reader-{model,state,renderer,interaction}.ts`, corresponding tests | Supply device/capsule content and semantic actions. Do not create a second reader/navigation engine. |
| Terminal, character grid, fonts, Python bridge | `uCode/packages/gridcore/src/{terminal,characters,fonts,bridge}`; `uCode/runtimes/basic/bridge/gridcore_adapter.py` | Consume versioned rendering/runtime contracts. Plain CLI remains usable without a browser or JS runtime; advanced display packs add the required renderer. |
| Program capsules and sessions | `uCode/scripts/probe_capsule_runtime.py`, `ucode-session/1` | Physical vault capsules reference a qualified program payload and session protocol; no new interpreter. |
| Filesystem document reading/search | `uKnowledge/uknowledge/library.py`, `config.py` | This module explicitly has no uCore/AppFlowy/model dependency. Reuse it as a library or package subset for standalone documents. Sonic still owns hardware-model matching, not a competing document index. |
| Knowledge routes and permissions | `uKnowledge/uknowledge/routes.py`; uCore extension registration | Use the existing host API when installed. Contribution/export/signing promises still need endpoint-by-endpoint verification; do not assume all planned routes work. |
| Host module lifecycle | `uCore/backend/app/services/distribution_system/{distribution_system,package_manager,models}.py` | Existing install/update/remove/repair and plate integration are the host authority. Sonic's bootstrap installs a verified host release, then delegates component lifecycle. |
| Secrets, identity, API access | `uCore/backend/app/secret/store.py`, `services/identity.py`, extension/API services | Remove Sonic's independent server/security-management direction. Standalone capsule encryption uses a local artifact provider, not a replacement ecosystem secrets service. |
| Events and health | uCore Feed/health services; Sonic lightweight journal | Emit through adapters when hosted; bounded standalone journal otherwise. Do not create another dashboard/health daemon. |
| Durable orchestration | uFlow, with uCore workflow bridge | Sonic runs individual bounded operations. uFlow composes them once installed. |
| Installer preflight, stage, receipt, verify and rollback | `HomeNest/src/uhome_server/installer/*`, `tests/test_{staging,promotion,installer_bundle}.py` | Compare contracts before writing Sonic's plan/apply engine. Generic extraction only after ownership/testing review; HomeNest-specific media provisioning stays there. |
| Existing uihub Sonic route | `uCore/frontend-vue/src/surfaces/sonic/SonicScrewdriverSurface.vue` | Replace its mock data through one adapter in a later integration sprint; do not build another web project in Sonic. |

Important limits: uCore's current distribution implementation includes Git/plate operations and empty-checksum metadata; this inspection does not establish a production signed/offline release bootstrap. That missing release contract belongs with uCore, not in a parallel Sonic package manager. uCode's generic page provider still contains sample registry/legacy path defaults: reuse the reader primitives with explicit inputs, not those defaults.

No functioning general hardware scanner, device-driver matching engine or safe disk/firmware plan/apply service was found in the inspected uCore/uCode application sources. Those are legitimate Sonic responsibilities. This is bounded negative evidence, not a claim that no related code exists anywhere in their histories.

## Standalone boundary

The minimal Python/Linux tool can inspect hardware, read model records, use selected offline content, create plans and execute qualified local providers. It neither needs nor starts uCore. Optional display/content/runtime packages supply capabilities on demand. An explicit bootstrap operation installs a verified uCore release and selected uCode/uKnowledge components; once present, the existing host owns services, credentials and workflows. Beacon is a deployment role using those components where they fit, with a small standalone static/offline mode for constrained devices.

## Upstream assessment

“Public domain” here means publicly available candidates; these projects generally have licenses, not public-domain status. Source licenses and each content collection's redistribution rights are recorded separately. Python is Sonic's application language; consuming a maintained C/C++ system tool does not require rewriting it in Python. No Go rewrite or mandatory Go toolchain is justified by the inspected requirements.

| Candidate | Decision and integration boundary | Intake |
| --- | --- | --- |
| [Ventoy](https://github.com/ventoy/Ventoy) | Preferred foundation for a Sonic-owned multiboot version. First prove a pinned upstream build, then maintain a narrow theme/menu/manifest patch set in Sonic-owned source. Preserve boot compatibility and upstream attribution. Inspect all bundled boot components, binaries and licenses before selecting a release. | Cloned pristine to `Vendor/01-RAW/ventoy`; GPLv3+ for Ventoy-authored components, separate bundled notices. Product fork pending concrete patch/build review. |
| [Mint themes](https://github.com/linuxmint/mint-themes) | Reversible Classic Modern overlay on upstream themes; use desktop settings and package hooks. Do not recreate a desktop environment or revive the failed shell installer. | Cloned to `Vendor/01-RAW/mint-themes`; GPLv3+ in `debian/copyright`. |
| [esptool](https://github.com/espressif/esptool) | Optional Python provider for supported Espressif devices. Use its tool/API and qualified board recipes; avoid recreating transport/flash logic. | Cloned to `Vendor/01-RAW/esptool`; GPLv2+. Hardware tests pending. |
| [Kiwix tools](https://github.com/kiwix/kiwix-tools) | Optional ZIM collection search/serving for guide capsules and Beacon. Adapt through uKnowledge; ordinary Markdown capsules need not depend on it. | Cloned to `Vendor/01-RAW/kiwix-tools`; GPLv3+. Content packs are separate. |
| [OpenWrt](https://openwrt.org/) | Qualified router firmware/profile foundation for Beacon; use upstream device support evidence. First Beacon can run on a PC plus an existing router without flashing it. | Candidate only; choose exact router before firmware/source intake. |
| [fwupd](https://github.com/fwupd/fwupd) | Prefer an adapter for supported vendor firmware updates over inventing another update ecosystem. Does not cover every driver/device. | Candidate only; platform/package qualification later. |
| [cryptsetup](https://gitlab.com/cryptsetup/cryptsetup) | Evaluate established Linux encrypted-volume support for crypt capsules. Portability/readers and recovery requirements decide the format; no custom crypto. | Candidate only; no encryption format selected or installed. |
| Existing Vendor fonts-retro and CEETEX | Fonts and teletext references already exist locally. uCode remains the rendering owner; avoid importing another terminal frontend. | No duplicate clones created. |

Official references: Ventoy's [license statement](https://www.ventoy.net/en/doc_license.html) and [installation guide](https://www.ventoy.net/en/doc_start.html); esptool's repository README describes the Python tool and bundled flasher-stub dependency; Kiwix's README documents search/manage/serve over ZIM. These capabilities are upstream claims, not Sonic integration results. Linux Mint's [project catalogue](https://projects.linuxmint.com/mint/) also identifies mintstick as a future imaging implementation reference if needed.

## Vendor process applied

Followed `Vendor/README.md`: RAW first, upstream-only `origin`, no product modifications/builds, license and intent in `VENDOR_MANIFEST.yaml`, commit pins in `00-INDEX/SONIC-INTAKE-2026-09.json`. The four checkouts remain pristine. Their shallow HEAD pins are study snapshots, not release selections.

Ventoy tracks a generated Qt build directory upstream. It is excluded from this local checkout through sparse-checkout, rather than edited or deleted from upstream history. Three bundled ZIP dependencies have separate manifest entries and remain unexecuted pending component-level review. Vendor hygiene passes after these steps.

No hosted GitHub fork was created: there is not yet a reviewed product patch. The accepted next direction is a Sonic-owned Ventoy derivative, kept outside RAW and based on the exact upstream pin. The first boot-provider spike must produce a build/component inventory, boot tests, patch budget, update procedure and precise fork ownership. Avoid a whole-codebase copy into the Python package.

Intake lifecycle: local study clones consume disk only and start no services; remove unadopted clones and corresponding manifest entries together. Integrated artifacts require explicit version/size budgets in the Sonic profile; upstream clones are not shipped to end users.
