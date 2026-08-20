# ADR 0013: Align canonical semantics with HDP Draft 0.1

Status: accepted for `0.2.0a1`
Date: 2026-08-20

## Context

The Factory and the separate HDP Reference repository both identified their
definitions as HDP `0.1`, but the Factory retained older target-shaped enums for
tool interfaces and runtime profile types. The current Draft 0.1 schema uses
provider-neutral tool kinds and an extensible profile slug. This drift caused
valid reference examples to fail Factory validation and placed target details in
canonical semantics.

## Decision

- The Factory's canonical schema and the analyser skill's schema copy are byte
  identical to `urn:hdp:schema:0.1.0`, SHA-256
  `4cb4a85dcdfe6b176be5760a1f109c720a66ea80a6179f94928e3683f1566e96`.
- Canonical tool kinds remain the Draft 0.1 generic vocabulary. Codex executable
  mappings are selected only by `commandBindings` in the target binding.
- Runtime profile type is an extensible slug. The Codex vertical slice accepts
  the target-neutral `software-development` profile and rejects unsupported
  profiles during adapter generation, not structural HDP validation.
- A trace component may reference an output contract or retained contract
  artifact, matching the current Draft 0.1 examples. Evidence nodes remain
  restricted to retained evidence artifacts.
- Tests pin the Draft 0.1 schema digest, schema-copy equality, target binding
  completeness and typed trace references.

## Consequences

The Factory validates all current HDP Reference Draft 0.1 examples. A structurally
valid general HDP still does not imply that the Codex adapter can compile it; the
adapter must bind every allowed capability and support the selected profile.
Future HDP schema revisions require an explicit compatibility decision and test
fixture update.

## Rejected alternatives

- Document the schema drift as a limitation: rejected because two public repos
  cannot honestly use the same `0.1` contract name for incompatible schemas.
- Add Codex-specific values to the reference schema: rejected because target
  bindings own provider and runtime details.
- Treat any stable ID as any trace kind: rejected because the specification
  requires kind-compatible references.
