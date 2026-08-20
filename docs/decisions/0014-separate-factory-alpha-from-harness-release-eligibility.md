# ADR 0014: Separate the factory alpha from harness release eligibility

Status: accepted

## Context

The software package and a generated harness have different release subjects.
The factory can be installed and evaluated while a particular generated harness
remains ineligible because one of its content-bound conformance gates failed.

On 2026-08-20, a fresh Codex CLI `0.148.0-alpha.15` probe using requested model
`gpt-5.6-sol`, reasoning effort `xhigh`, `workspace-write`, and approval policy
`never` blocked direct TCP network access and allowed workspace writes, but read
an explicit canary outside the workspace. This does not satisfy the example
HDP's workspace-only read policy. Docker was installed but its daemon was not
available, and nesting an additional macOS Seatbelt profile around Codex was
incompatible with Codex applying its own command sandbox.

## Decision

Publish `harness-factory` only as an explicitly experimental software alpha.
Do not mark the generated Codex harness release eligible and do not weaken or
rename the failed outside-read gate. Preserve the failing raw evidence and make
the limitation prominent in the verification report and release notes.

`harness release` continues to require the full subject-bound evidence bundle.
A GitHub/Python distribution release of the factory is not an attestation that
any generated harness passed those gates.

## Rejected alternatives

- Treating `workspace-write` as workspace-only read isolation was rejected
  because the live canary was readable.
- Replacing the read-denial probe with an outside-write probe was rejected
  because it would test a weaker policy than the HDP declares.
- Reusing the older passing summary was rejected because its raw evidence was
  unavailable and a current probe contradicted it.
- Tailoring a sandbox profile only to the canary path was rejected because it
  would not establish the general workspace boundary.

## Consequences

The public alpha remains useful for deterministic generation, analysis,
installation, static verification, live task experiments, and tamper detection,
but the reference generated harness is not release eligible. The next release
gate is a reproducible outer container or VM boundary that prevents agent reads
outside the mounted workspace while still permitting the controller's model
transport, followed by a fresh four-task run and bound evidence bundle.
