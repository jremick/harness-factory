# Stable release checkpoint

## Current position

Harness Factory is currently **Stage 2 — Public Alpha** at `v0.2.0a1`. The
factory can be installed, can build and install a Codex harness, and has passing
tests on Ubuntu and macOS. Alpha means people can inspect and try it, but should
expect some commands, file formats and compatibility promises to change.

The target is **Stage 4 — Stable OSS** with a `1.0.0` release. Stable will mean
that users can depend on the documented command-line workflow and file formats
through the `1.x` release line, understand upgrade risk, verify official release
artifacts, and use a documented support and security process.

Stable will **not** mean that every AI-generated change is correct, that every
possible harness can be reconstructed, or that this project is a formal
standard or security certification.

## Current blockers

The following gaps prevent a stable release today:

1. The example generated harness is not release-eligible because the current
   Codex sandbox probe could read a file outside its workspace.
2. Analysis of harnesses created by other tools has not yet passed a fresh
   held-out test with zero false assertions.
3. Behavioural evidence covers only a small reference task set and one complete
   target adapter.
4. The public compatibility surface is not frozen, and there is no tested
   migration path from the alpha formats to `1.0`.
5. Release files have checksums, but authenticated build provenance, an SBOM and
   trusted package-registry publishing are not yet in place.
6. Upgrade, rollback and troubleshooting guidance is not complete enough for a
   stable support promise.

## Required gates

Every gate below is mandatory unless a later ADR narrows the stable product
scope and records why.

| Gate | Exit condition | Required evidence |
| --- | --- | --- |
| Supported product contract | Declare the supported `harness` commands, HDP/HIR versions, Codex binding, generated-file ownership rules and release formats for `1.x`. | Versioning and compatibility docs, frozen schemas, golden tests and an ADR defining the stable surface. |
| Upgrade safety | Existing alpha projects either migrate deterministically or fail with a clear, actionable message. | Migration tool or documented manual path, old-to-new fixtures, digest-preserving source maps and rollback tests. |
| Runtime isolation | A supported outer runtime passes filesystem, network, process, environment, time, output and resource-limit probes for the stable reference harness. | Exact-subject sandbox evidence with every mandatory security gate passing and `releaseEligible: true`. |
| Managed installer safety | Install, update, interruption recovery, tamper detection, concurrent execution and hostile path cases remain fail-closed on supported platforms. | Green security regression suite on Ubuntu and macOS plus an independent adversarial review with no unresolved critical/high finding. |
| Managed round-trip parity | A harness built by this factory can be analysed, rebuilt and compared without losing declared behaviour. | Exact analyse → build → diff tests for every supported stable contract version. |
| Foreign-harness honesty | The analyser never invents required facts and passes a fresh held-out foreign harness with zero critical or noncritical false assertions. | Precommitted evaluator, immutable fixture, provenance/uncertainty report and independently recomputed score. |
| Real-world usefulness | The supported workflow succeeds beyond the bundled toy repository and its limits are measured rather than implied. | At least two additional independently maintained repositories, repeated feature/fix/refactor/policy tasks, evaluator results and a published comparison with the no-harness baseline. |
| Reproducible releases | Official source and wheel artifacts are built from a protected tag, content-addressed and independently installable. | Clean-build reproduction, checksums, SBOM, signed or platform-attested provenance, tamper test and install-from-release test. |
| Package delivery | Users have one maintained installation path with upgrade and uninstall instructions. | Trusted PyPI publishing through OIDC, public installation test, dependency audit and release runbook. |
| Operations and support | Users know what is supported, how upgrades work, where bugs go and how security reports are handled. | Installation, upgrade, rollback and troubleshooting docs; maintained issue/security routes; changelog; triage of all known critical/high issues. |

## Delivery sequence

### 1. Close alpha safety and fidelity gaps

- Add or adopt a portable outer sandbox and make all mandatory probes pass.
- Run a new, untouched foreign-harness evaluation after the analyser is frozen.
- Keep the current Codex-only scope; do not add another adapter to create the
  appearance of maturity.

Exit: the reference harness can become release-eligible and the analyser's
held-out zero-false-assertion gate passes.

### 2. Publish a public beta

- Freeze the candidate `harness` command and file-format surface.
- Add migration fixtures and broaden behavioural tests to real repositories.
- Publish compatibility, upgrade, rollback, troubleshooting and support
  expectations.
- Ship a beta through the same protected CI and release-asset verification path
  used for the alpha.

Exit: a new user can install, run, upgrade and diagnose the supported workflow
without maintainer-only knowledge.

### 3. Cut a release candidate

- Accept only blocker, compatibility, documentation and security fixes.
- Run the complete test, behavioural, sandbox, analyser, migration, packaging,
  provenance and clean-install suite from a protected tag.
- Commission a final independent architecture and security review.
- Triage every known critical/high issue and record any accepted lower-severity
  risk.

Exit: the release candidate satisfies every required gate with no material
claim based only on self-authored evidence.

### 4. Publish `1.0.0`

- Publish signed or platform-attested source and wheel artifacts with checksums
  and an SBOM.
- Publish through the trusted package-registry path and repeat the five-minute
  start from the public artifact.
- Read back the tag, release assets, package metadata, default-branch CI,
  security settings and required branch checks.
- Start the documented maintenance, deprecation and vulnerability-response
  cadence.

Exit: Harness Factory meets the Stage 4 stable criteria and users can evaluate
both how to adopt it and the risks of depending on it.

## Explicit non-goals for `1.0`

- A web interface, Kubernetes deployment or general workflow platform.
- A second complete target adapter unless it is needed by real beta users and
  passes the same gates as Codex.
- A guarantee that an AI agent will produce correct software.
- Formal certification, a claimed SLSA level without matching evidence, or
  support for every model provider and harness format.
