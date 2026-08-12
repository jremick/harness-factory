# ADR 0009: Keep evaluator cases outside a round-trippable HDP

Status: accepted  
Date: 2026-08-12

## Context

The analyser must reconstruct a valid HDP and that HDP must recompile to the
same target harness. The generated harness must also exclude evaluator-private
cases, answers, secrets, and implementation code. A field-level redaction of
the declared HDP made the embedded definition structurally invalid and made an
exact analyse-to-compile round trip impossible.

## Decision

An HDP contains the evaluator's public contract only: opaque fixture
commitments, stable evaluator identifiers, scenario bindings, test types, and
observable expected outcomes. Actual hidden cases, answer data, evaluator
source, and credentials are never HDP inputs and stay in separately custodied
paths outside the generated harness.

The compiler embeds the exact canonical declared HDP. The analyser adds an
`x-hdp-reconstruction` evidence extension; the compiler validates that
extension and then excludes it from build semantics, so recompilation produces
the original HIR and target artifacts. The public runtime verification contract
shown to the agent remains separately filtered.

## Rejected alternatives

- Redacting required fields from the embedded HDP: rejected because the result
  is invalid and cannot meet round-trip compilation parity.
- Embedding private evaluator inputs and redacting only the agent-facing view:
  rejected because the target workspace is not an appropriate custody boundary.
- Guessing omitted fields during analysis: rejected because it would turn
  unknown facts into fabricated declarations.

## Consequences

Round-trip parity is deterministic for generated harnesses, while evaluation
secrecy depends on keeping private cases out of the HDP at authoring time. The
secret scanner and canary tests remain defence-in-depth checks, not permission
to include private evaluator material in a definition.
