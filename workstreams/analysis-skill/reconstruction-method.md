# Evidence-first HDP reconstruction method

Status: design and evaluation contract for `analyse-existing-harness`

## 1. Claim boundary

Reconstruct what the source artifacts support, not what a well-designed harness
would normally contain. Structural completeness never justifies a factual
invention.

Keep these four statements separate throughout the analysis:

| Claim class | What it means | Sufficient basis | Prohibited shortcut |
|---|---|---|---|
| Evidenced intended outcome | An authoritative source explicitly states the result the harness is meant to produce for a user or operator | Goal, task, charter, product requirement, or equivalent declarative text | Deriving a business or user outcome from tools, prompts, tests, or code shape |
| Operational behavior | The harness is configured or observed to behave in a particular way | Enforced configuration, executable policy, runtime trace, or repeatable inspection | Calling configured behavior the intended outcome |
| Inferred intent | A hypothesis best explaining one or more mechanics | Multiple consistent source facts plus a stated inference rule | Presenting the hypothesis as declared intent or omitting the need for confirmation |
| Absent or unknowable | The source set does not establish the value | Completed search with no sufficient source, an inaccessible source, or irreconcilable evidence | Supplying a plausible default, conventional value, or fabricated precision |

Tests and tool manifests can evidence technical acceptance behavior. They do not
evidence a business outcome unless the source itself explicitly states that
outcome and its relationship to the test or tool.

## 2. Required outputs

Produce these artifacts as one reconstruction bundle:

1. `reconstructed-hdp.yaml`: the candidate resolved HDP.
2. `reconstruction-evidence.json`: one evidence record for every populated HDP
   field and every required field that remains unknown.
3. `open-questions.md`: only questions whose answers change a normative HDP
   value or are required to make the candidate structurally valid.
4. `source-inventory.json`: included and excluded source paths, digests, access
   state, authority for each claim class, and the inspection time.
5. `validation-report.json`: parsing, structural validation, reference checks,
   contradictions, and an explicit status of `pass`, `fail`, `not-run`, or
   `inconclusive` for each validation layer attempted.

Do not call a candidate a valid HDP unless it passes the canonical structural
schema. Do not call a structurally valid candidate conformant, fit, complete, or
operationally assured without the corresponding semantic and runtime evidence.

## 3. Evidence record contract

Use one record at the smallest meaningful field granularity. For an entity array,
record both the entity identity and each consequential scalar. Use an RFC 6901
JSON Pointer in `field`; when array order is unstable, use the stable entity ID in
the evidence note and retain the resolved numeric pointer for the emitted HDP.

```json
{
  "field": "/purpose/intendedOutcomes/0/statement",
  "value": "Produce an evidence-backed incident diagnosis and remediation draft.",
  "claimClass": "evidenced-intended-outcome",
  "epistemicStatus": "declared",
  "confidence": 0.95,
  "sources": [
    {
      "path": "AGENTS.md",
      "location": "lines 8-10",
      "digest": "sha256:<64 lowercase hex characters>",
      "excerpt": "Produce an evidence-backed incident diagnosis...",
      "authority": "normative-purpose"
    }
  ],
  "contradictions": [],
  "missingEvidence": [],
  "humanConfirmation": {
    "required": false,
    "reason": ""
  }
}
```

Every record MUST contain all eight substantive elements requested by the
analysis contract:

- `field` and `value` identify the HDP value.
- `sources` contain a source path or URI, precise location, and preferably a
  digest. An empty array is valid only for `unknown`.
- `epistemicStatus` is exactly `observed`, `declared`, `inferred`, or `unknown`.
- `confidence` is a number from 0 through 1.
- `contradictions` is an array, even when empty. Each contradiction names both
  sources, the conflicting propositions, materiality, and chosen treatment.
- `missingEvidence` is an array, even when empty. State the exact evidence that
  would resolve an unknown or inference.
- `humanConfirmation.required` is a boolean and `reason` explains every `true`.

`claimClass` MUST be one of:

- `evidenced-intended-outcome`
- `operational-behavior`
- `inferred-intent`
- `administrative-metadata`
- `absent-or-unknowable`

The record value MUST equal the value at `field` in `reconstructed-hdp.yaml`.
For a missing field, use `null` and `epistemicStatus: unknown` in the ledger; do
not add `null` to the HDP when the schema prohibits it.

## 4. Epistemic rules and confidence

### Declared

Use `declared` only when a source asserts the value in the relevant semantic
role. A prompt that says “never write production” declares a constraint. It does
not declare a target business outcome. Cite the exact assertion.

Normal range: `0.80-1.00`. Reduce confidence when authority, freshness, scope, or
version is unclear. A declaration can be confidently reported while still being
contradicted by observed behavior; record the contradiction instead of lowering
it until the disagreement disappears.

### Observed

Use `observed` only for executed or directly inspected behavior. Configuration
is declared operational policy unless enforcement is demonstrated. A runtime
trace can establish that a tool call was denied on that run, not that it is
always denied.

Normal range: `0.75-1.00`. State the observation scope and repeatability limits.

### Inferred

Use `inferred` only when the inference is useful, identifies all premises, and
does not cross a protected boundary. Normal range: `0.30-0.79`. Mark human
confirmation required for any inferred normative value.

Never infer these values solely from mechanics:

- business, user, or organizational outcomes;
- success thresholds, service objectives, or risk appetite;
- permissions broader than an enforced allowlist;
- approval authority;
- hidden evaluation contents or expected answers;
- compliance applicability;
- data classification below the most restrictive supported reading; or
- production fitness.

Deterministic identifier derivation, media type from a file extension, and other
representation-preserving transforms may be inferred without human confirmation
when the transformation rule is recorded and reversible.

### Unknown

Use `unknown` when no sufficient evidence exists, the evidence is inaccessible,
or contradictions prevent a defensible selection. Use confidence `0.00` because
there is no supported field value.
Set `humanConfirmation.required: true` when the unknown blocks a required HDP
field, materially changes execution, or affects a claim of outcome or safety.

## 5. Authority is field-specific

Do not impose one global source precedence order. Assign authority by question:

| Question | Normally strongest source | What can rebut or qualify it |
|---|---|---|
| Intended outcome and target user | Task, charter, product requirement, explicit owner statement | Newer superseding intent document or owner confirmation |
| Enforced permissions | Runtime sandbox, tool allowlist, policy engine, access readback | Runtime trace showing the declared boundary is not enforced |
| Workflow | Executable orchestration or active prompt/config | Trace showing a different path; an explicit newer workflow declaration |
| Success and acceptance | Acceptance contract and evaluator definition | Executed evaluation result; not an implementation unit test alone |
| Runtime and dependency versions | Lockfile, deployed manifest, runtime readback | Immutable build/deployment evidence |
| Observed behavior | Timestamped trace tied to the subject digest | Reproduction against the same subject that demonstrates nondeterminism |

An older authoritative file can remain evidence of a declaration without being
evidence of current operation. Record both time and subject scope.

## 6. Reconstruction procedure

### Step 0: Freeze the evaluation boundary

- Define the source root and output root.
- Exclude evaluator-owned gold data, prior reconstructions, scoring results, and
  this method's conclusions from the forward agent's readable inputs.
- Hash each included source artifact before analysis.
- Record inaccessible, binary, generated, vendored, and excluded paths.
- Stop if the source boundary accidentally contains ground truth or prior answers;
  remove contamination and start a fresh run.

### Step 1: Inventory source roles

Classify each source as intent, policy, prompt, tool interface, implementation,
test, trace, deployment/runtime evidence, documentation, or unknown. Assign its
authority independently for purpose, behavior, permissions, evaluation, and
runtime claims. Do not assume a filename such as `AGENTS.md` is current or
enforced.

### Step 2: Extract atomic facts before mapping

Create a fact table with source location, exact proposition, source role,
epistemic status, subject/version, and freshness. Extract negative facts and
explicit absences as carefully as positive facts. Do not write HDP prose yet.
Split coordinated declarations into independently typed atomic facts only when
the destination schema has distinct fields for them. A field such as trace
retention receives its exact duration, while an adjacent aggregate-result
retention duration remains a separate fact. For subject-phrase destinations,
strip only an explicit subject-and-copula frame. When the destination is a
standalone statement, change only the first remaining alphabetic character to
sentence case and preserve the rest of the phrase exactly.

### Step 3: Map mechanics without promoting them to intent

Map tools, permissions, prompts, roles, stages, state, timeouts, and traces to
operational fields. Separately search intent-bearing sources for target users,
outcomes, non-goals, measures, and acceptance. If only mechanics exist, mark
purpose and outcome fields unknown rather than reverse-engineering a business
story.

### Step 4: Build the field-coverage matrix

For every top-level field family in the canonical schema, record one of:

- `evidenced`: one or more candidate facts exist;
- `contradicted`: sources disagree materially;
- `unknown`: the search completed without sufficient evidence;
- `not-inspected`: the source was not available or inspection did not occur; or
- `not-applicable`: permitted only when the schema and profile allow omission.

The matrix is complete only when every required field and every emitted optional
field has an evidence record. Arrays require coverage for membership as well as
consequential item values.

### Step 5: Reconcile contradictions explicitly

Keep both propositions. Determine whether they concern declared intent,
configured policy, or observed behavior; many apparent contradictions are
different layers. Select a value only when field-specific authority and freshness
support it. Otherwise mark the value unknown and request confirmation.

Never silently choose the more permissive permission, more favorable outcome,
newer-looking version, or most complete document.

### Step 6: Construct the candidate

- Preserve source identifiers when stable and schema-valid.
- Derive new IDs deterministically from source identity and record the rule.
- Copy exact values where the source vocabulary matches.
- Normalize only reversible representation differences such as whitespace,
  explicit booleans, or canonical path syntax.
- Use empty arrays only where the schema permits them and absence is evidenced.
- Put epistemic metadata in `reconstruction-evidence.json`; the core HDP schema
  does not provide annotations on every field.
- Use `extensions.x-reconstruction` only for a pointer and digest to the evidence
  ledger, never to weaken core semantics.

### Step 7: Refuse false structural completeness

When a required field lacks evidence, do not invent a conventional value merely
to satisfy `required`, `minItems`, enum, numeric, or reference constraints.

If the schema can represent uncertainty honestly, use that representation and
record it. If it cannot, leave the field absent from the candidate, emit the
structural diagnostic, add a ledger record with `value: null` and `unknown`, and
ask the smallest human-confirmation question. The candidate remains an
incomplete reconstruction until answered.

This rule is particularly important for required numeric limits, success
thresholds, outcome statements, evaluation expectations, and permissions. A
schema-invalid honest draft is preferable to a schema-valid false assertion.

### Step 8: Validate in layers

Run and report separately:

1. Safe parse and duplicate-key handling.
2. Canonical Draft 2020-12 structural validation.
3. Evidence-ledger completeness and HDP/ledger value consistency.
4. Stable-ID and reference resolution.
5. Cross-field semantic checks, including outcome-to-measure-to-evaluation and
   requirement-to-test-to-evidence paths.
6. Contradiction and human-confirmation gates.
7. Runtime or implementation comparison only if the relevant subject can be
   safely observed.

Do not collapse `not-run`, `inconclusive`, or `unknown` into pass.

### Step 9: State the strongest supported claim

Use exactly the strongest accurate handoff language:

- **Structurally valid reconstruction**: schema validation passed; unresolved
  semantic questions may remain.
- **Evidence-complete reconstruction**: every emitted and required field has a
  defensible evidence record or an explicit unknown.
- **Implementation-aligned reconstruction**: runtime/config comparison supports
  the operational fields for the pinned subject.
- **Intent-confirmed reconstruction**: an authorized human confirmed all inferred
  or previously unknown normative intent.

These claims are cumulative only when their named gates pass.

## 7. Forward-test protocol

Use a fresh agent context for each fixture. Give it only:

- the `analyse-existing-harness` skill;
- the raw harness source directory;
- the canonical schema;
- an empty output directory; and
- a neutral request to reconstruct the harness as an HDP with its evidence
  ledger and validation report.

Do not provide the source HDP, expected field manifest, rubric scoring details,
gold annotations, earlier output, suspected failure, or this workstream's
conclusions. Place those under an evaluator-private directory not included in the
agent's source boundary.

After the agent exits, freeze the output, run structural validation, then run
`score_fidelity.py` against the private expected manifest. Keep qualitative
review separate and label any non-deterministic judgment.

For a generated-harness round trip, compare against the source HDP that generated
the harness. Score only information that survives generation or whose absence is
itself expected. A generator that intentionally omits authoring-only metadata
must produce `correct_unknown`, not a false penalty or a reconstructed invention.

For a foreign harness, use a gold manifest built by an evaluator who read only the
raw artifacts. Include both positive facts and deliberate unknowns. At least one
fixture should contain a declaration/enforcement contradiction and no business
outcome, so the skill must demonstrate restraint rather than template completion.

## 8. Stop conditions

Stop and request human input when:

- a required business or user outcome is absent;
- sources materially conflict and field-specific authority cannot resolve them;
- satisfying the schema would require an invented threshold, budget, permission,
  evaluator expectation, or compliance claim;
- the source boundary includes evaluation gold or hidden fixtures;
- source digests change during analysis; or
- validation cannot distinguish `not-run` from pass.

Non-goals of reconstruction are redesigning the harness, recommending a better
architecture, filling expected best practices, proving production fitness, or
claiming the source author's unstated motivation.
