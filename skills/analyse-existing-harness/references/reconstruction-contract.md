# Reconstruction output contract

Version: 0.1.0

Each leaf field in `hdp.reconstructed.yaml`, excluding the reconstruction
extension itself, has one assessment in the adjacent `evidence-map.json` named
by `extensions.x-hdp-reconstruction.evidenceMap`.

```yaml
- field: /governance/permissions/network/allowed
  value: false
  claimClass: operational-behavior
  epistemicStatus: declared
  confidence: 0.95
  sources:
    - path: config/runtime-policy.json
      location: /network/allowed
      digest: sha256:64-lowercase-hex
      authority: inspected-runtime-object
  contradictions: []
  missingEvidence:
    - No OS-level sandbox readback was available.
  humanConfirmation:
    required: true
    reason: No OS-level sandbox readback was available.
```

## Status decision

`claimClass` is exactly one of `evidenced-intended-outcome`,
`operational-behavior`, `inferred-intent`, `administrative-metadata`, or
`absent-or-unknowable`.

- Use `observed` only for executed/read-back behavior with a preserved trace.
- Use `declared` for explicit prompt/config/code/document statements.
- Use `inferred` when multiple facts support an interpretation but no artifact
  states it. Record plausible alternatives in `contradictions` or `missingEvidence`.
- Use `unknown` when a value cannot be established. Do not fill the gap with a
  common pattern, implementation convention, or desired answer.

Confidence is a number from 0 to 1. `unknown` MUST use 0. `inferred` MUST be below
0.8. `observed` and `declared` still require evidence and MAY be below 1 when
artifacts are stale, partial, or contradictory.

## Outcome rule

Prompts, roles, tools, tests, and workflow stages show operational mechanics.
They establish an intended business outcome only when an authorized source says
what effect is desired for which user or environment. Otherwise use an explicit
unknown outcome and set `generationReady: false`.

## Contradictions and omission

Preserve both sides with separate locations. Prefer the active runtime readback
for observed behavior while retaining the stale declaration as a contradiction.
Do not silently resolve conflicts by source order. List inaccessible, absent, or
unverifiable artifact classes in `omissions`.
