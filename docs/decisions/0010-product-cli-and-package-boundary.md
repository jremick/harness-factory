# ADR 0010: Expose Harness Factory as the product interface

Status: accepted for `0.2.0a1`

## Context

The verified v0.1 implementation was distributed as `hdp-reference` with an
`hdp` command. After separating the active Harness Factory and versioned HDP
Reference repositories, that name makes users treat the data contract and the
factory product as the same thing. The low-level commands also expose compiler
paths and evidence assembly before a user can complete the common workflow.

## Decision

- The active distribution is `harness-factory`.
- `harness` is the primary product command.
- `hdp` remains a compatibility command for the v0.1 low-level interface.
- Convention-driven commands discover `harness/hdp.yaml` and
  `harness/bindings/codex.yaml`.
- `build`, `install`, `audit`, `verify` and `release` orchestrate existing
  deterministic primitives. They do not change HDP/HIR semantics or bypass
  release gates.
- Generated-file installation is manifest-owned, dry-runnable and refuses to
  overwrite unowned or modified files.

## Consequences

The factory and contract may version independently. v0.1 evidence remains named
as originally produced; v0.2 package subjects identify Harness Factory. Users
need one product install, while generated manifests continue to identify the
exact HDP definition, HIR, binding and adapter used.

## Rejected alternatives

- Rename every v0.1 artifact: rejected because it would invalidate recorded
  subjects and confuse historical evidence.
- Keep only the expert `hdp` commands: rejected because repeated path flags and
  manual copying make the safe path harder than the unsafe one.
- Hide deterministic stages behind model automation: rejected because hard
  validity, permission and release decisions remain code-owned.

