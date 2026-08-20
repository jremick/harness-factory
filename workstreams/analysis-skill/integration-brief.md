# Existing-harness analysis integration brief

Status: method, deterministic evaluator, frozen forward tests, retained
public-alpha blind failures, and evaluation-informed regression complete

## Outcome

This workstream supplies an evidence-first reconstruction method, a complete
field-family fidelity rubric, an executable scorer, evaluator-private gold
manifests, and a structurally different Agent Spec/AGENTS/prompt/tool fixture.

The central rule is that schema completeness never authorizes factual invention.
Mechanics may establish operational behavior or support an explicitly labeled
inference, but they do not establish a business outcome. When the source cannot
support a required value, the reconstruction must expose the unknown and its
structural consequence rather than manufacture a passing HDP.

ADR 0012 makes that rule executable for the foreign fixture: raw schema validity
is not required when the gold contract itself identifies absent required values.
Those values must instead appear as explicit unknown evidence records, while all
content, coverage, confidence and zero-false-assertion gates remain unchanged.

## Deliverables

| Artifact | Purpose |
|---|---|
| `reconstruction-method.md` | Field-level evidence contract, epistemic rules, contradiction handling, unknown policy, validation layers, forward-test boundary, and stop conditions |
| `fidelity-rubric.json` | Machine-readable categories, weights, confidence bands, all 23 required HDP field families, and hard gates |
| `score_fidelity.py` | Deterministic fact, evidence-contract, confidence, schema, and optional whole-document scoring |
| `second-harness/` | Foreign Agent Spec plus scoped AGENTS, prompt, tools, evaluation, change policy, and observed trace |
| `tests/evaluator-private/` | Gold facts and input-boundary declarations withheld from forward agents |
| `tests/test_score_fidelity.py` | Scorer unit and CLI tests |
| `tests/results/` | Machine-readable self-test and fidelity reports |

## Fidelity categories

Each expected fact receives exactly one content category:

- `exact_match`
- `normalized_match`
- `acceptable_inferred_difference`
- `false_assertion`
- `correct_unknown`
- `missing_field`

Confidence calibration and evidence-contract completeness are separate scores so
an exact value with fabricated provenance cannot receive full credit. Any false
assertion fails the current rubric; critical outcome, permission, safety,
evaluation, runtime, traceability, or risk assertions are counted separately.

The scorer accepts either a standalone `records` ledger or the skill's current
`fieldAssessments` shape. It verifies HDP/ledger value consistency, source path and
location, epistemic status, contradiction and missing-evidence arrays, human
confirmation, and confidence band. Optional whole-document comparison uses
canonical JSON after only evaluator-declared ignore pointers are removed.

## Test evidence

### Scorer and fixture validation

Verified on 2026-08-12:

- Eight scorer unit/CLI tests pass.
- Rubric, both gold manifests, and JSON fixture files parse.
- The generated round-trip gold has 26 facts across all 23 field families.
- The foreign-harness gold has 27 facts across all 23 field families.
- `git diff --check -- hdp-reference/workstreams/analysis-skill` passes.

See `tests/results/scorer-selftest.json` for the command ledger.

### Generated-harness round trip

The frozen-skill reconstruction at
`hdp-reference/evidence/skill-forward-generated-frozen/hdp.reconstructed.yaml`
was compared with the public source snapshot embedded in the generated harness at
`hdp-reference/build/generated-harness/.hdp/source-definition.public.json`.

- Ignore set: only `/extensions/x-hdp-reconstruction`, which is reconstruction
  evidence intentionally absent from the source HDP.
- Whole-document comparison: exact.
- Source and comparable reconstruction canonical SHA-256:
  `95f189ceae3ae88c280971358f25897d39f8cad967bf0b03f1d55f2c6e7f0867`.
- Structural validation: pass.
- Sampled field result: 26 exact, 0 normalized, 0 inferred differences,
  0 false assertions, 0 missing fields.
- Content, evidence contract, coverage, and confidence calibration: `1.0`.
- Overall score: `1.0`; all configured gates pass.

The frozen skill added explicit claim classes, eliminating the earlier assessment
contract deduction. See `tests/results/generated-roundtrip-frozen.json`.

Exact source recovery did not hide implementation drift. The forward agent also
reported eight artifact-level contradictions: parent-directory write wording,
unenforced tool allowlisting, unrecorded denial events, unapplied timeout and hard
budgets, missing trace redaction/correlation, ungated completion summaries, and
dropped public-test statements. These are declared/code-inspection findings, not
runtime observations, and demonstrate why lossless round trip and implementation
alignment are separate gates.

The current authoring example at `examples/software-development/hdp.yaml` has
since evolved to the broader `ai-sdlc` definition and no longer equals the
generated harness's embedded source snapshot. It is source/generation drift, not
a reconstruction error; using that newer file as ground truth correctly fails
whole-document fidelity.

### Invalidated runs

Two exploratory agent runs were interrupted and excluded because the skill
changed during execution. The foreign run also saw a release-notes-specific
scaffold that was unrelated to its subject. Their payloads were moved
recoverably to a local, untracked archive; the
invalidation notice remains under `tests/invalidated-runs/`. They are not inputs,
gold, baselines, or reported results.

### Foreign-harness forward test

The foreign Agent Spec run is structurally and evidentially substantial but fails
the precommitted deterministic fidelity rubric.

- Structural schema validation: pass.
- Internal stable-ID and reference check: pass (122 IDs, 66 checked references).
- Field assessments: 667 total; 347 declared, 304 inferred, 16 unknown.
- Claim classes: 590 operational behavior, 43 administrative metadata,
  13 inferred intent, 5 evidenced intended outcome, 16 absent/unknowable.
- Contradictions: 4; omissions: 10, of which 7 block generation.
- `generationReady`: correctly false.
- Deterministic facts: 20 exact, 1 correct-unknown guard, 5 false-assertion
  categories, 1 missing field.
- Scores: content `0.797753`, evidence contract `0.936474`, confidence
  calibration `0.943820`, coverage `0.943820`, overall `0.694036`.
- Result: fail. False-assertion, critical-false-assertion, content, coverage, and
  overall gates failed. No gate was weakened; schema validity itself passed.

The confirmed reconstruction defect is an empty `safety.privacyControls` array
despite an explicit source privacy rule. It also overuses `inferred` for values
that appear directly in source files (`metadata.name` and the `logs.search` tool
name), unnecessarily requiring confirmation, and classifies a directly declared
mission summary as `inferred-intent` instead of
`evidenced-intended-outcome`.

The five deterministic false-assertion categories are conservative string-match
failures, not five material fabrications: each output is a supported paraphrase,
representation-preserving split, or supported superset. The business-outcome
guard passed; the agent did not invent a KPI. This post-score adjudication does
not modify or override the failing rubric result. See
`tests/results/foreign-agent-spec-frozen.json` and
`tests/results/foreign-agent-spec-adjudication.json`.

The agent verified the task-start `SKILL.md` digest
`6044f8deb9c9d69a60e58b1b3598f6dd4055a50abe0262f733de495f0925860b`
before reading the harness. A later final read found concurrent skill drift to
`972a792db45ee78f29fc76d22bd5ed3a35e21f4f535a60fbe721b5d58b843961`.
All seven harness inputs, the schema, and the evidence contract remained stable.
The run is scored against the task-start skill read but is not a fully immutable
execution; a copied read-only skill snapshot would provide stronger proof.

### 2026-08-20 public-alpha blind sequence

Four immutable-input foreign-harness attempts were completed by fresh
`gpt-5.6-sol` agents at `xhigh`; a schema-mismatched third attempt was stopped
and invalidated before reconstruction. Every completed score remains retained,
including failures:

| Run | Overall | Exact | Correct unknown | False assertions | Critical | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 0.750303 | 22 | 1 | 3 | 2 | fail |
| 2 | 0.734883 | 17 | 5 | 4 | 1 | fail |
| 4 | 0.914799 | 24 | 5 | 2 | 1 | fail |
| 5 | 0.947037 | 22 | 5 | 1 | 1 | fail |

Run 5 passed the content, coverage, evidence-contract, confidence and overall
score thresholds. It still failed the zero-false-assertion hard gate because a
standalone target-user statement began with lower-case `a` rather than the
precommitted sentence-case `A`. The run correctly retained 11 unsupported
required fields as zero-confidence unknowns, kept `generationReady: false`, and
preserved four contradictions. Its 316 declared-string checks and two
representable trace-edge checks passed.

The skill was subsequently clarified to sentence-case only the first remaining
alphabetic character after removing an explicit subject-and-copula frame. Any
follow-up on this same fixture is evaluation-informed regression, not a new
blind result. A genuinely fresh blind claim requires a new separately controlled
fixture and commitment.

Machine-readable scores are retained in
`tests/results/public-alpha-blind-run-{1,2,4,5}.json`. The progression is useful
engineering evidence, but none of these four results satisfies the precommitted
zero-false-assertion gate.

The evaluation-informed run 6 reached overall `0.964835`, with 25 exact facts,
5 correct unknowns, no critical false assertion, and one noncritical false-
assertion category. It selected a different directly supported “no business
KPI” limitation than the precommitted statement, so the zero-false-assertion
gate still failed. The machine result is
`tests/results/public-alpha-evaluation-informed-run-6.json`. No further tuning
on this fixture is counted as independent evidence.

## Findings

### 1. Epistemic data must be first-class

Every emitted leaf and every required-but-unknown field needs value, precise
source/location, `observed|declared|inferred|unknown`, confidence,
contradictions, missing evidence, and human-confirmation state. A separate ledger
or reconstruction extension is necessary because the core schema does not carry
these annotations at each field.

### 2. Intent and behavior require different authority

Task or charter text can declare intended outcomes. Tool policy can declare an
operational boundary. A runtime trace can observe behavior for a pinned run.
None substitutes for the others. The foreign fixture deliberately includes a
stale prompt sentence allowing a restart while the tool policy denies restart and
an observed trace records the denial; a correct reconstruction must preserve all
three layers.

### 3. Honest incompleteness can be the only correct result

Some schema-required fields, especially numeric limits, thresholds, and linked
evaluation entities, cannot carry `unknown`. If no source supports them, a
schema-valid value would be a false assertion. The process therefore returns an
incomplete candidate plus diagnostics and a narrow confirmation question. A
validity claim waits for that answer.

### 4. Exact recovery is a distinct fast path

When a generated harness carries a validated public source snapshot, exact
recovery is preferable to re-inference. The whole-document comparison proves
losslessness while the reconstruction extension records provenance. Observable
artifacts still need a separate drift/contradiction comparison before making an
implementation-alignment claim.

### 5. Scaffolds are an evaluation and correctness hazard

A domain-specific “minimal” template can seed unrelated outcomes, permissions,
tools, runtime facts, and risks into a foreign reconstruction. Starting artifacts
must be neutral, visibly non-assertive, and outside gold provenance. A scaffold
must never be mistaken for subject evidence.

### 6. Epistemic status should describe the value, not the mapping work

The foreign run marked direct source values such as `incident-scribe` and
`logs.search` as inferred because their placement in the HDP required schema
mapping. This conflates two questions. The value remains declared; the mapping or
normalization can be separately recorded as an inferred transformation. Otherwise
confidence and human-confirmation requirements become systematically overstated.

### 7. Literal deterministic scoring needs atomic gold facts

Whitespace normalization is deterministic, but semantic paraphrase is not. The
foreign run shows that field-level prose comparisons can conservatively report a
false assertion for a faithful paraphrase or a value split across adjacent
fields. Gold should prefer stable IDs, booleans, enums, numbers, paths, and atomic
phrases. Longer prose needs predeclared alternatives or a blinded adjudication
layer that never alters the deterministic score.

## Integration risks

| Risk | Effect | Treatment |
|---|---|---|
| Skill changes during a forward run | Result no longer identifies one tested subject | Hash all skill, schema, and fixture inputs before and after; invalidate on drift |
| Gold and agent share a readable filesystem | Prompt-only separation can fail without leaving obvious evidence | Prefer an OS-enforced clean copy; otherwise inspect the agent read/inventory trace and state that isolation was logical, not proven |
| Domain-specific reconstruction scaffold | False assertions and answer leakage | Use a neutral skeleton or construct from schema; never ship example values as placeholders |
| Claim-class drift across tools | The four-way intent/behavior distinction can disappear from downstream evidence | Keep `claimClass` required in the reconstruction contract, annotation script, validator, and scorer |
| Mapping work is labeled as inferred value | Direct declarations receive low confidence and unnecessary confirmation | Add a separate transformation/mapping assessment; keep epistemic status tied to source support for the value |
| Explicit controls disappear into empty schema arrays | A structurally valid HDP silently loses privacy or safety requirements | Add field-family extraction coverage checks and negative fixtures for each declared control family |
| Array-index gold paths | Correct reorderings can look wrong | Preserve source order where normative; otherwise add stable-ID selector support or score whole collections semantically |
| Schema-valid unknown placeholders | Consumers may mistake placeholders for facts | Prefer blocked invalid draft when the schema cannot represent uncertainty; require `generationReady: false` and explicit diagnostics |
| Large embedded field ledger | Output can exceed 300 KB for a 600-line HDP | Keep canonical evidence in a sidecar and embed only a digest/reference if the schema profile permits it |
| Pattern-based no-business-claim check | Detects fabrication classes, not every possible invented outcome | Retain deterministic patterns as a guard; use a separate blinded human semantic review for residual cases |

## Recommended integration action

1. Copy the skill, schema, scripts, and contract into a read-only run directory;
   record before/after digests instead of relying on a live path staying frozen.
2. Keep the explicit field-level claim class and add a separate mapping or
   transformation assessment so direct values remain `declared`.
3. Add a coverage regression requiring every explicit privacy, security, safety,
   and permission statement to reach the appropriate HDP collection or an
   explicit contradiction/unknown record.
4. Ensure the reconstruction starting point contains no domain values and cannot
   be cited as subject evidence.
5. Prefer atomic deterministic gold facts and stable-ID collection selectors;
   retain blinded semantic adjudication only as a separate report.
6. Regenerate the example harness when the authoring source changes, or explicitly
   label the embedded public snapshot as the historical round-trip ground truth.
7. Treat any structural failure, false assertion, gold leakage, or input drift as
   failed or invalid rather than averaging it into a passing score.

## Scope boundary

This workstream designs and evaluates reconstruction. It does not edit or install
the skill, modify the canonical schema, change dependencies, or write to
`~/.codex`. It does not claim that a structurally valid reconstruction proves
implementation conformance, outcome fitness, or operational assurance.
